import json
import logging
import random
import mysql.connector
import telegram.ext
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARN

)
logger = logging.getLogger(__name__)
token = "5927240736:AAEXVEGcGVas4cNdGtOWZb3Pq2RZSEPkwmM"

datos_globales = {
    'r_insulina': [],
    'r_r_insulina': [],
    'menu': [],
    'borrarnino': []
}


class Enfermero:
    def __init__(self, uid: int, nombre: str, username: str, colegio: str):
        self.uid = uid
        self.nombre = nombre
        self.username = username
        self.colegio = colegio


class Ninio:
    def __init__(self, nombre: str, ratio: float, enfermero: int):
        self.nombre = nombre
        self.ratio = ratio
        self.enfermero = enfermero


class Menu:
    def __init__(self):
        self.primero = ""
        self.cantidad_primero = 0
        self.segundo = ""
        self.cantidad_segundo = 0
        self.extra = ""
        self.cantidad_extra = 0
        self.postre = ""
        self.cantidad_postre = 0
        self.pan = False
        self.cantidad_pan = 0

    async def menu_to_dict(self):
        menu_analizar = {
            "Primero": self.primero,
            "Cantidad de primero": self.cantidad_primero,
            "Segundo": self.segundo,
            "Cantidad de segundo": self.cantidad_primero,
            "Extra": self.extra,
            "Cantidad de extra": self.cantidad_extra,
            "Postre": self.postre,
            "Cantidad de postre": self.cantidad_postre,
            "Pan": self.pan,
            "Cantidad de pan": self.cantidad_pan
        }
        return menu_analizar

    async def getraciones(self):
        raciones = 0
        if await getgramos(self.primero) != 0:
            raciones += self.cantidad_primero / await getgramos(self.primero)
        if await getgramos(self.segundo) != 0:
            raciones += self.cantidad_segundo / await getgramos(self.segundo)
        if self.extra != "Nada" and await getgramos(self.extra) != 0:
            raciones += self.cantidad_extra / await getgramos(self.extra)
        if await getgramos(self.postre) != 0:
            raciones += self.cantidad_postre / await getgramos(self.postre)
        if self.pan:
            raciones += self.cantidad_pan / 20
        return raciones


async def helpp(update, context):
    ayuda = "/help: Muestra esta ayuda.\n\n/ejemplomenu: Muestra un ejemplo de menú.\n\n/alimentos: Da informacion " \
            "sobre el alimento que se especifique, si no se especifica ninguno de mostrará una lista " \
            "completa.\n\n/insertaralimento: Inserta un nuevo alimento para usar en menus se deberá especificar un " \
            "nombre y la cantidad que da lugar a una racion.\n\n/registro: Comando para que un enfermero se " \
            "registre, deberá indicar el nombre, el apellido y el colegio.\n\n/registronino Comando para registrar " \
            "un niño a nombre de quien ejecute el comando, este debe estar registrado con el comando /registro. Se " \
            "deberá especificar un nombre y un ratio.\n\n/insulina: Calcula la insulina que se debe pinchar al niño." \
            "\n\n/menu: Tras especificar un menú indicará cuantas raciones genera ese menu.\n\n/borrarnino: Elimina " \
            "a un niño de la lista de ese enfermero.\n\n/baja: Darse de baja.\n\n/cancelar: Cancelar toda pregunta " \
            "que haya quedado pendiente con el bot.\n\n/ban: Expulsar a un usuario.\n\n/unban: Retirar la expulsion " \
            "a un usuario, deberá volver a entrar al grupo."
    await context.bot.send_message(chat_id=update.message.chat.id, text=ayuda)


async def beautify(elements: list):
    pair = False
    res = ""
    for e in elements:
        keys = e.keys()
        for key in keys:
            if e[key] != "":
                t = str(e[key]).lower()
                if t != "libre":
                    res = res + f"{key}: {e[key]}\n"
                    if pair:
                        res = res[:len(res) - 1] + " gramos/centilitros\n\n"
                elif t == "false":
                    res = res + f"{key}: No\n"
                elif t == "true":
                    res = res + f"{key}: Si\n"
                else:
                    res = res + f"{key}: {e[key]}\n\n"
                pair = not pair
        res = res + "\n"
    return res


async def ejemplos(update, context):
    await context.bot.send_message(chat_id=update.message.chat_id, text="Este es un menú que se puede preparar:")
    with open("Menus.json", "r") as file:
        data = json.load(file)
    pos = random.randint(0, len(data) - 1)
    await context.bot.send_message(chat_id=update.message.chat_id, text=await beautify([data[pos]]))


async def alimentos(update, context):
    try:
        datos = context.args[0]
    except IndexError:
        datos = None
    if datos:
        elems = []
        with open("Alimentos.json") as file:
            data = json.load(file)
        datas = str(data).replace("\'", "\"")
        dataj = json.loads(datas)
        for elem in dataj:
            if str(datos).lower() in str(elem['Alimento']).lower():
                elems.append(elem)
        if elems:
            msj = await beautify(elems)
            await context.bot.send_message(chat_id=update.message.chat_id, text=f"Algunos alimentos que contienen "
                                                                                f"la palabra {datos} son:")
            await context.bot.send_message(chat_id=update.message.chat_id, text=msj)
        else:
            await context.bot.send_message(chat_id=update.message.chat_id,
                                           text=f"No hay elementos con el nombre {datos}")
    else:
        file = open("Alimentos.pdf", "rb")
        await context.bot.send_document(chat_id=update.message.chat_id, document=file)


async def new_alimento(data, alim):
    for elem in data:
        if elem['Alimento'] == alim:
            return False
    return True


async def insertar_alimento(update, context):
    try:
        i = 0
        alimento = ""
        while i < len(context.args) - 1:
            alimento = alimento + " " + context.args[i]
            i = i + 1
        cr = context.args[len(context.args) - 1]
    except IndexError:
        alimento = None
        cr = None
    if alimento:
        with open("Alimentos.json", "r") as file:
            data = json.load(file)
        if await new_alimento(data, alimento):
            elem = {
                "Alimento": alimento,
                "Cantidad": cr
            }
            data.append(elem)
            with open("Alimentos.json", "w") as file:
                json.dump(data, file)
            await context.bot.send_message(chat_id=update.message.chat_id, text=f"Alimento {alimento} "
                                                                                f"añadido correctamente")
        else:
            await context.bot.send_message(chat_id=update.message.chat_id, text="El alimento ya existe en "
                                                                                "los datos")

    else:
        await context.bot.send_message(chat_id=update.message.chat_id,
                                       text="No se ha especificado correctamente el alimento y su cantidad por "
                                            "racion, para añadir un alimento usa el siguiente comando con el "
                                            "formato /insertaralimento <i>comida cantidad</i>",
                                       parse_mode=telegram.constants.ParseMode.HTML)


def database():
    conn = mysql.connector.connect(
        user='conection',
        password='passwd',
        host='localhost',
        database='pfg')
    cursor = conn.cursor()
    return conn, cursor


def dboff(conn, cursor):
    cursor.close()
    conn.close()


async def registro(update, context):
    try:
        colegio = context.args[2]
        if len(context.args) > 3:
            i = 3
            while i < len(context.args):
                colegio = colegio + " " + context.args[i]
                i = i + 1
        uname = update.message.from_user.username
        if not uname:
            uname = "-"
        else:
            uname = "@" + uname
        enfermero = Enfermero(update.message.from_user.id, context.args[0] + context.args[1], uname, colegio)
    except IndexError:
        enfermero = None

    if enfermero:
        conn, cursor = database()
        try:
            sql = f"INSERT INTO enfermeros VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (enfermero.uid, enfermero.nombre, enfermero.username, enfermero.colegio,))
            conn.commit()
            await context.bot.send_message(chat_id=update.message.chat_id,
                                           text=f"Enfermero/a {enfermero.nombre} registrado/a")
        except mysql.connector.errors.IntegrityError:
            await context.bot.send_message(chat_id=update.message.chat_id,
                                           text=f"Enfermero/a {enfermero.nombre} ya registrado/a previamente")

        dboff(conn, cursor)
    else:
        await context.bot.send_message(chat_id=update.message.chat_id,
                                       text="No se han especificado correctamente los datos, el uso de este comando "
                                            "es: /registro <i>nombre apellido colegio</i> (Colegio pueden ser varias "
                                            "palabras)",
                                       parse_mode=telegram.constants.ParseMode.HTML)


async def check_registro(uid):
    conn, cursor = database()
    sql = f"SELECT * FROM enfermeros WHERE uid = {uid}"
    cursor.execute(sql)
    data = cursor.fetchall()
    dboff(conn, cursor)
    if data:
        return True
    else:
        return False


async def registro_nino(update, context):
    if await check_registro(update.message.from_user.id):
        try:
            i = 0
            nombre = ""
            while i < len(context.args) - 1:
                nombre = nombre + context.args[i]
                i = i + 1
            try:
                v = context.args[len(context.args) - 1].replace(",", ".")
                nino = Ninio(nombre, float(v), update.message.from_user.id)
            except ValueError:
                nino = None
        except IndexError:
            nino = None

        if nino:
            conn, cursor = database()
            try:
                sql = "INSERT INTO ninios VALUES (%s, %s, %s)"
                cursor.execute(sql, (nino.nombre, nino.ratio, nino.enfermero,))
                conn.commit()
                await context.bot.send_message(chat_id=update.message.chat_id, text="Niño añadido.")
            except mysql.connector.errors.IntegrityError:
                await context.bot.send_message(chat_id=update.message.chat_id, text="Niño ya añadido")
            dboff(conn, cursor)
        else:
            await context.bot.send_message(chat_id=update.message.chat_id,
                                           text="No se han especificado correctamente los datos, el uso de este "
                                                "comando es: /registronino <i>nombre ratio</i> (nombre pueden ser "
                                                "varias palabras)",
                                           parse_mode=telegram.constants.ParseMode.HTML)
    else:
        await context.bot.send_message(chat_id=update.message.chat_id, text="Enfermero no registrado, para poder "
                                                                            "incluir niños se ha de registrar primero "
                                                                            "el enfermero que los va a supervisar "
                                                                            "mediante el comando /registro")


async def mensajes(update, context):
    if update.message.chat.type == "private":
        """insulina"""
        chatid = update.message.chat_id
        if datos_globales['r_insulina']:
            i = 0
            found = False
            while i < len(datos_globales['r_insulina']) and not found:
                if datos_globales['r_insulina'][i] == chatid:
                    await respuesta_insulina(update, context)
                    found = True
                i += 1
        elif datos_globales['r_r_insulina']:
            i = 0
            found = False
            while i < len(datos_globales['r_r_insulina']) and not found:
                if datos_globales['r_r_insulina'][i].enfermero == chatid:
                    await r_respuesta_insulina(update, context, datos_globales['r_r_insulina'][i])
                    found = True
                i += 1
        elif datos_globales['menu']:
            i = 0
            found = False
            while i < len(datos_globales['menu']) and not found:
                if datos_globales['menu'][i][0] == chatid:
                    await menu(update, context)
                    found = True
                i += 1
        elif datos_globales['borrarnino']:
            i = 0
            found = False
            while i < len(datos_globales['borrarnino']) and not found:
                if datos_globales['borrarnino'][i] == update.message.from_user.id:
                    await r_borrarninio(update)
                    await context.bot.send_message(chat_id=chatid, text="Niño eliminado de la base de datos.")
                    found = True
                i = i + 1


async def creabotones(lista):
    lon = len(lista)
    par = False
    listatemp = []
    botones = []
    if lon % 2 == 0:
        for item in lista:
            texto = item
            if not par:
                listatemp = [texto]
                par = True
            else:
                listatemp.append(texto)
                par = False
                botones.append(listatemp)
    else:
        num = 0
        for item in lista:
            texto = item
            if num + 1 == lon:
                botones.append([texto])
            if not par:
                listatemp = [texto]
                par = True
                num = num + 1
            else:
                listatemp.append(texto)
                par = False
                botones.append(listatemp)
                num = num + 1
    return botones


async def respuesta_insulina(update, context):
    global datos_globales
    i = 0
    found = False
    nino = Ninio(update.message.text, 0.0, update.message.from_user.id)
    while i < len(datos_globales['r_insulina']) and not found:
        if datos_globales['r_insulina'][i] == nino.enfermero:
            datos_globales['r_insulina'].pop(i)
            found = True
        i += 1
    conn, cursor = database()
    sql = "SELECT ratio FROM ninios WHERE nombre = %s AND enfermero = %s"
    cursor.execute(sql, (nino.nombre, nino.enfermero,))
    data = cursor.fetchall()
    if data:
        nino.ratio = data[0][0]
        datos_globales['r_r_insulina'].append(nino)
        await context.bot.send_message(chat_id=update.message.chat_id,
                                       text=f"Indica cuantas raciones ha consumido {nino.nombre}")
    else:
        await context.bot.send_message(chat_id=update.message.chat_id, text=f"No se ha encontrado a ese niño")
    dboff(conn, cursor)


async def r_respuesta_insulina(update, context, nino):
    global datos_globales
    raciones = update.message.text
    i = 0
    found = False
    while i < len(datos_globales['r_r_insulina']) and not found:
        if datos_globales['r_r_insulina'][i].enfermero == update.message.chat_id:
            datos_globales['r_r_insulina'].pop(i)
            found = True
        i += 1
    try:
        raciones = float(raciones.replace(",", "."))
    except ValueError:
        raciones = None
    if raciones:
        await context.bot.send_message(chat_id=update.message.chat_id, text=f"La cantidad de insulina que necesita "
                                                                            f"{nino.nombre} es "
                                                                            f"{float(raciones) * nino.ratio}")
    else:
        await context.bot.send_message(chat_id=update.message.chat_id, text=f"No se ha indicado un numero de "
                                                                            f"raciones correcto")


async def insulina(update, context):
    global datos_globales
    conn, cursor = database()
    sql = f"SELECT nombre FROM ninios where enfermero ={update.message.from_user.id}"
    cursor.execute(sql)
    ninos = cursor.fetchall()
    datos = []
    if ninos:
        for n in ninos:
            datos.append(n[0])
        ninios = await creabotones(datos)
        aux = telegram.ReplyKeyboardMarkup(ninios, resize_keyboard=True, one_time_keyboard=True)
        await context.bot.send_message(chat_id=update.message.chat_id,
                                       text="Indica con respecto a que niño hacer el calculo",
                                       reply_markup=aux)
        datos_globales['r_insulina'].append(update.message.from_user.id)
    else:
        await context.bot.send_message(chat_id=update.message.chat_id,
                                       text="No hay ningun niño/a registrado con este enfermero")
    dboff(conn, cursor)


async def getgramos(alimento):
    with open("Alimentos.json", "r") as file:
        val = file.readlines()[0].lower()
    alimento = alimento.lower()
    pos = val.find(f"\"{alimento}\"")
    valor = val[pos:]
    pos = valor.find("cantidad\": \"")
    valor = valor[pos + 12:]
    pos = valor.find("\"")
    valor = valor[:pos]
    if valor == "libre":
        return 0
    return int(valor)


async def menu(update, context):
    global datos_globales
    chatid = update.message.chat_id
    if "private" not in update.message.chat.type:
        await context.bot.send_message(chat_id=update.message.chat_id,
                                       text=" Este comando ha de ejecutarse en un chat privado.")
    else:
        i = 0
        found = False
        datos = []
        while i < len(datos_globales['menu']) and not found:
            if datos_globales['menu'][i][0] == chatid:
                found = True
                datos = datos_globales['menu'][i].copy()
            else:
                i = i + 1
        if not found:
            """Primera ejecución"""
            await context.bot.send_message(chat_id=update.message.chat_id,
                                           text="Dime el primer plato, recuerda que todos los alimentos que incluyas "
                                                "deben estar en la lista obtenible con el comando /alimentos.")
            menu_analizar = Menu()
            datos_globales['menu'].append([update.message.chat_id, 1, menu_analizar])
        else:
            msj = update.message.text.lower()
            msj = msj.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
            paso = datos[1]
            with open("Alimentos.json", "r") as file:
                comidas = file.readlines()[0].lower()
            if paso == 1:
                msj = "\"" + msj + "\""
                if comidas.find(msj) != -1:
                    datos[2].primero = msj[1:len(msj) - 1]
                    datos[1] = paso + 1
                    await context.bot.send_message(chat_id=update.message.chat_id,
                                                   text="Indica la cantidad en gramos del primer plato")
                    datos_globales['menu'][i] = datos
                else:
                    await context.bot.send_message(chat_id=update.message.chat_id,
                                                   text="Alimento no encontrado, prueba de nuevo. Si quieres cancelar "
                                                        "usa /cancelar en cualquier momento.")
            elif paso == 2:
                """Cantidad de primero"""
                try:
                    cant = int(msj)
                except ValueError:
                    cant = None
                if cant:
                    datos[1] += 1
                    datos[2].cantidad_primero = cant
                    await context.bot.send_message(chat_id=update.message.chat_id,
                                                   text="Indica el segundo plato.")
                    datos_globales['menu'][i] = datos
                else:
                    await context.bot.send_message(chat_id=update.message.chat_id,
                                                   text="Cantidad no válida, intentalo de nuevo. Si quieres cancelar "
                                                        "usa /cancelar en cualquier momento.")
            elif paso == 3:
                msj = "\"" + msj + "\""
                if comidas.find(msj) != -1:
                    datos[2].segundo = msj[1:len(msj) - 1]
                    datos[1] = paso + 1
                    await context.bot.send_message(chat_id=update.message.chat_id,
                                                   text="Indica la cantidad en gramos del segundo plato")
                    datos_globales['menu'][i] = datos
                else:
                    await context.bot.send_message(chat_id=update.message.chat_id,
                                                   text="Alimento no encontrado, prueba de nuevo. Si quieres cancelar "
                                                        "usa /cancelar en cualquier momento.")
            elif paso == 4:
                """Cantidad de primero"""
                try:
                    cant = int(msj)
                except ValueError:
                    cant = None
                if cant:
                    datos[1] += 1
                    datos[2].cantidad_segundo = cant
                    await context.bot.send_message(chat_id=update.message.chat_id,
                                                   text="Indica un extra, si no hubiese pon nada.")
                    datos_globales['menu'][i] = datos
                else:
                    await context.bot.send_message(chat_id=update.message.chat_id,
                                                   text="Cantidad no válida, intentalo de nuevo. Si quieres cancelar "
                                                        "usa /cancelar en cualquier momento.")
            elif paso == 5:
                msj = "\"" + msj + "\""
                if "\"nada\"" == msj or "\"Nada\"" == msj:
                    datos[1] = paso + 2
                    datos[2].extra = "Nada"
                    datos[2].cantidad_extra = 0
                    datos_globales['menu'][i] = datos
                    await context.bot.send_message(chat_id=update.message.chat_id,
                                                   text="Indica un postre.")
                else:
                    if comidas.find(msj) != -1:
                        datos[2].extra = msj[1:len(msj) - 1]
                        datos[1] = paso + 1
                        await context.bot.send_message(chat_id=update.message.chat_id,
                                                       text="Indica la cantidad en gramos del extra")
                        datos_globales['menu'][i] = datos
                    else:
                        await context.bot.send_message(chat_id=update.message.chat_id,
                                                       text="Alimento no encontrado, prueba de nuevo. Si quieres "
                                                            "cancelar usa /cancelar en cualquier momento.")
            elif paso == 6:
                """Cantidad de extra"""
                try:
                    cant = int(msj)
                except ValueError:
                    cant = None
                if cant:
                    datos[1] += 1
                    datos[2].cantidad_extra = cant
                    await context.bot.send_message(chat_id=update.message.chat_id,
                                                   text="Indica un postre.")
                    datos_globales['menu'][i] = datos
                else:
                    await context.bot.send_message(chat_id=update.message.chat_id,
                                                   text="Cantidad no válida, intentalo de nuevo. Si quieres cancelar "
                                                        "usa /cancelar en cualquier momento.")

            elif paso == 7:
                msj = "\"" + msj + "\""
                if comidas.find(msj) != -1:
                    datos[2].postre = msj[1:len(msj) - 1]
                    datos[1] = paso + 1
                    await context.bot.send_message(chat_id=update.message.chat_id,
                                                   text="Indica la cantidad en gramos del postre")
                    datos_globales['menu'][i] = datos
                else:
                    await context.bot.send_message(chat_id=update.message.chat_id,
                                                   text="Alimento no encontrado, prueba de nuevo. Si quieres cancelar "
                                                        "usa /cancelar en cualquier momento.")
            elif paso == 8:
                """Cantidad de postre"""
                try:
                    cant = int(msj)
                except ValueError:
                    cant = None
                if cant:
                    datos[1] += 1
                    datos[2].cantidad_postre = cant
                    aux = telegram.ReplyKeyboardMarkup([['Si', 'No']], resize_keyboard=True,
                                                       one_time_keyboard=True)
                    await context.bot.send_message(chat_id=update.message.chat_id,
                                                   text="¿Tomará pan?",
                                                   reply_markup=aux)
                    datos_globales['menu'][i] = datos
                else:
                    await context.bot.send_message(chat_id=update.message.chat_id,
                                                   text="Cantidad no válida, intentalo de nuevo. Si quieres cancelar "
                                                        "usa /cancelar en cualquier momento.")
            elif paso == 9:
                if msj == "si":
                    datos[1] = paso + 1
                    datos[2].pan = True
                    await context.bot.send_message(chat_id=update.message.chat_id,
                                                   text="Indica la cantidad en gramos de pan")
                    datos_globales['menu'][i] = datos
                else:
                    datos[2].pan = False
                    datos[2].cantidad_pan = 0
                    datos_globales['menu'][i] = datos
                    raciones = await datos[2].getraciones()
                    await context.bot.send_message(chat_id=chatid, text=f"El menú es:")
                    res = await beautify([await datos_globales['menu'][i][2].menu_to_dict()])
                    await context.bot.send_message(chat_id=chatid, text=res)
                    await context.bot.send_message(chat_id=chatid, text=f"Las raciones que genera este menú dados los "
                                                                        f"pesos son {raciones} raciones")
                    datos_globales['menu'].pop(i)
            elif paso == 10:
                """Cantidad de pan"""
                try:
                    cant = int(msj)
                except ValueError:
                    cant = None
                if cant:
                    datos[2].cantidad_pan = cant
                    datos_globales['menu'][i] = datos
                    raciones = await datos[2].getraciones()
                    await context.bot.send_message(chat_id=chatid, text=f"El menú es:")
                    res = await beautify([await datos_globales['menu'][i][2].menu_to_dict()])
                    await context.bot.send_message(chat_id=chatid, text=res)
                    await context.bot.send_message(chat_id=chatid, text=f"Las raciones que genera este menú dados los "
                                                                        f"pesos son {raciones} raciones")
                    datos_globales['menu'].pop(i)
                else:
                    await context.bot.send_message(chat_id=update.message.chat_id,
                                                   text="Cantidad no válida, intentalo de nuevo. Si quieres cancelar "
                                                        "usa /cancelar en cualquier momento.")


async def r_borrarninio(update):
    global datos_globales
    i = 0
    found = False
    name = update.message.text
    while i < len(datos_globales['borrarnino']) and not found:
        if datos_globales['borrarnino'][i] == update.message.from_user.id:
            datos_globales['borrarnino'].pop(i)
            found = True
        i += 1
    await borrarninio(update.message.from_user.id, name)


async def borrarninio(enfermero, name):
    conn, cursor = database()
    sql = "DELETE FROM ninios WHERE enfermero = %s and nombre = %s"
    cursor.execute(sql, (enfermero, name,))
    conn.commit()
    dboff(conn, cursor)


async def borrarnino(update, context):
    if update.message.chat.type == "private":
        if await check_registro(update.message.from_user.id):
            global datos_globales
            conn, cursor = database()
            sql = f"SELECT nombre FROM ninios where enfermero ={update.message.from_user.id}"
            cursor.execute(sql)
            ninos = cursor.fetchall()
            datos = []
            for n in ninos:
                datos.append(n[0])
            ninios = await creabotones(datos)
            aux = telegram.ReplyKeyboardMarkup(ninios, resize_keyboard=True, one_time_keyboard=True)
            await context.bot.send_message(chat_id=update.message.chat_id,
                                           text="Indica que niño quieres borrar",
                                           reply_markup=aux)
            datos_globales['borrarnino'].append(update.message.from_user.id)
            dboff(conn, cursor)
        else:
            await context.bot.send_message(chat_id=update.message.chat.id, text="Enfermero no encontrado")
    else:
        await context.bot.send_message(chat_id=update.message.chat.id, text="Utiliza este comando en un chat privado "
                                                                            "conmigo --> @Diabetes_PFG_bot")


async def baja(update, context):
    if update.message.chat.type == "private":
        if await check_registro(update.message.from_user.id):
            conn, cursor = database()
            sql = f"SELECT nombre FROM ninios where enfermero ={update.message.from_user.id}"
            cursor.execute(sql)
            ninos = cursor.fetchall()
            for n in ninos:
                await borrarninio(update.message.from_user.id, n[0])
            sql = "DELETE FROM enfermeros WHERE uid = %s"
            cursor.execute(sql, (update.message.from_user.id,))
            conn.commit()
            await context.bot.send_message(chat_id=update.message.chat.id, text="Enfermero dado de baja")
            dboff(conn, cursor)
        else:
            await context.bot.send_message(chat_id=update.message.chat.id, text="Enfermero no encontrado")
    else:
        await context.bot.send_message(chat_id=update.message.chat.id, text="Utiliza este comando en un chat privado "
                                                                            "conmigo --> @Diabetes_PFG_bot")


async def cancelar(update, context):
    global datos_globales
    user = update.message.from_user.id
    if user in datos_globales['r_insulina']:
        i = 0
        found = False
        while i < len(datos_globales['r_insulina']) and not found:
            if user == datos_globales['r_insulina'][i]:
                datos_globales['r_insulina'].pop(i)
                found = True
            i = i + 1
        await context.bot.send_message(chat_id=user, text="Comando insulina cancelado.")

    if (user in elem[0] for elem in datos_globales['r_r_insulina']) and len(datos_globales['r_r_insulina']) > 0:
        i = 0
        found = False
        while i < len(datos_globales['r_r_insulina']) and not found:
            if user == datos_globales['r_r_insulina'][i][0]:
                datos_globales['r_r_insulina'].pop(i)
                found = True
            i = i + 1
        await context.bot.send_message(chat_id=user, text="Comando insulina cancelado.")

    if (user in elem[0] for elem in datos_globales['menu']) and len(datos_globales['menu']) > 0:
        i = 0
        found = False
        while i < len(datos_globales['menu']) and not found:
            if user == datos_globales['menu'][i][0]:
                datos_globales['menu'].pop(i)
                found = True
            i = i + 1
        await context.bot.send_message(chat_id=user, text="Comando menu cancelado.")

    if user in datos_globales['borrarnino']:
        i = 0
        found = False
        while i < len(datos_globales['borrarnino']) and not found:
            if user == datos_globales['borrarnino'][i]:
                datos_globales['borrarnino'].pop(i)
                found = True
            i = i + 1
        await context.bot.send_message(chat_id=user, text="Comando borrarnino cancelado.")


async def checkadmin(update, context):
    user = update.message.from_user.id
    admins = await context.bot.get_chat_administrators(update.message.chat.id)
    for a in admins:
        if a.user.id == user:
            return True
    return False


async def ban(update, context):
    if "group" in update.message.chat.type:
        if not await checkadmin(update, context):
            await context.bot.delete_message(update.message.chat.id, update.message.message_id)
        else:
            if update.message.reply_to_message is not None:
                try:
                    await context.bot.ban_chat_member(update.message.chat.id,
                                                      update.message.reply_to_message.from_user.id)
                    await context.bot.send_message(chat_id=update.message.chat.id,
                                                   text="Usuario expulsado")
                except Exception:
                    await context.bot.send_message(chat_id=update.message.chat.id,
                                                   text="Error al expulsar al usuario")
            else:
                await context.bot.send_message(chat_id=update.message.chat.id,
                                               text="No se ha respondido a ningun mensaje del "
                                                    "usuario que se quiere banear. Un correcto "
                                                    "funcionamiento seria usar /ban "
                                                    "respondiendo al usuario")
    else:
        await context.bot.send_message(chat_id=update.message.chat.id,
                                       text="El comando debe ser ejecutado en un grupo")


if __name__ == '__main__':
    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler('help', helpp))
    application.add_handler(CommandHandler("ejemplomenu", ejemplos))
    application.add_handler(CommandHandler('alimentos', alimentos))
    application.add_handler(CommandHandler("insertaralimento", insertar_alimento))
    application.add_handler(CommandHandler("registro", registro))
    application.add_handler(CommandHandler("registronino", registro_nino))
    application.add_handler(CommandHandler("insulina", insulina))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("borrarnino", borrarnino))
    application.add_handler(CommandHandler("baja", baja))
    application.add_handler(CommandHandler("cancelar", cancelar))
    application.add_handler(CommandHandler("ban", ban))

    application.add_handler(MessageHandler(filters.TEXT, mensajes))

    print("Bot working")
    application.run_polling()
