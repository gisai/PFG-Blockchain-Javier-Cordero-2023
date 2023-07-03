import datetime

import hashlib

import json

from flask import Flask, jsonify, request

import requests

from uuid import uuid4

from urllib.parse import urlparse


class Blockchain:

    def __init__(self):
        self.chain = []
        self.transactions = []
        self.tickets = []
        self.create_block(proof=1, previous_hash='0')
        self.nodes = set()

    def add_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def replace_chain(self):
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)
        for node in network:
            response = requests.get(f'http://{node}/get_chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                if length > max_length and self.is_chain_valid(chain):
                    max_length = length
                    longest_chain = chain
        if longest_chain:
            self.chain = longest_chain
            return True
        return False

    def create_block(self, proof, previous_hash):
        block = {'index': len(self.chain) + 1,
                 'timestamp': str(datetime.datetime.now()),
                 'proof': proof,
                 'previous_hash': previous_hash,
                 'transactions': self.transactions,
                 'tickets': self.tickets}
        self.transactions = []
        self.tickets = []
        self.chain.append(block)
        return block

    def add_transacction(self, sender, reciever, amount, ticket):
        self.transactions.append({'sender': sender,
                                  'reciever': reciever,
                                  'amount': amount,
                                  'ticket': ticket})
        previous_block = self.get_prev_block()
        return previous_block['index'] + 1

    def add_ticket(self, ticket):
        ticket = ticket.ticket_to_dict()
        self.tickets.append(ticket)
        previous_block = self.get_prev_block()
        return previous_block['index'] + 1

    def get_prev_block(self):
        return self.chain[-1]

    @staticmethod
    def proof_of_work(prev_proof):
        new_proof = 1
        check_proof = False

        while not check_proof:
            hash_operation = hashlib.sha256(str(new_proof ** 2 - prev_proof ** 2).encode()).hexdigest()

            if hash_operation[:4] == '0000':
                check_proof = True
            else:
                new_proof += 1
        return new_proof

    @staticmethod
    def hash(block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def is_chain_valid(self, chain):
        previous_block = chain[0]
        block_index = 1

        while block_index < len(chain):
            block = chain[block_index]
            if block['previous_hash'] != self.hash(previous_block):
                return False
            previous_proof = previous_block['proof']
            proof = block['proof']
            hash_operation = hashlib.sha256(str(proof ** 2 - previous_proof ** 2).encode()).hexdigest()
            if hash_operation[:4] != '0000':
                return False
            previous_block = block
            block_index += 1
        return True


class Ticket:

    def __init__(self, tracker: str, company: str, origin: str,
                 destination: str, date_time: datetime, seat, owner: str = "Company"):
        self.tracker = tracker
        self.company = company
        self.origin = origin
        self.destination = destination
        self.date_time = date_time
        self.seat = seat
        self.owner = owner

    def ticket_to_dict(self):
        response = {
            "Tracker": self.tracker,
            "Company": self.company,
            "Origin": self.origin,
            "Destination": self.destination,
            "Date&hour": str(self.date_time),
            "Owner": self.owner,
            "Seat": self.seat
        }
        return response

    @staticmethod
    def dict_to_ticket(ticket_dict):
        return Ticket(
            ticket_dict['Tracker'],
            ticket_dict['Company'],
            ticket_dict['Origin'],
            ticket_dict['Destination'],
            datetime.datetime.strptime(str(ticket_dict['Date&hour']), "%Y-%m-%d %H:%M:%S"),
            ticket_dict['Seat']
        )


if __name__ == '__main__':
    app = Flask(__name__)

    node_address = str(uuid4()).replace('-', '')

    blockchain = Blockchain()


    @app.route('/mine_block', methods=['GET'])
    def mine_block():
        previous_block = blockchain.get_prev_block()
        previous_proof = previous_block['proof']
        proof = blockchain.proof_of_work(previous_proof)
        previous_hash = blockchain.hash(previous_block)
        blockchain.add_transacction("Blockchain", node_address, 1, "-")
        block = blockchain.create_block(proof, previous_hash)
        response = {'message': 'Bloque minado con exito',
                    'index': block['index'],
                    'timestamp': block['timestamp'],
                    'proof': block['proof'],
                    'previous_hash': block['previous_hash'],
                    'transactions': block['transactions'],
                    'tickets': block['tickets']}
        return jsonify(response), 200


    @app.route('/get_chain', methods=['GET'])
    def get_chain():
        response = {'chain': blockchain.chain,
                    'length': len(blockchain.chain)}
        return jsonify(response), 200


    @app.route('/is_valid', methods=['GET'])
    def is_valid():
        is_blockchain_valid = blockchain.is_chain_valid(blockchain.chain)
        if is_blockchain_valid:
            response = {
                'message': 'The Blockchain is valid'
            }
        else:
            response = {
                'message': 'The Blockchain is not valid'
            }
        return jsonify(response), 200


    @app.route("/buy_ticket", methods=['POST'])
    def buy_ticket():
        json_got = request.get_json()
        transaction_keys = ['sender', 'reciever', 'amount', 'ticket']
        if not all(key in json_got for key in transaction_keys):
            return 'There is an element of the transaction missing', 400
        t = find_ticket(json_got['ticket'])
        if t is not None:
            if t.owner == json_got['reciever']:
                index = blockchain.add_transacction(json_got['sender'], json_got['reciever'],
                                                    json_got['amount'], json_got['ticket'])
                t.owner = json_got['sender']
                blockchain.add_ticket(t)
                response = {
                    'message': f"The transacction will be added to the block {index}"
                }
                return jsonify(response), 200
            else:
                return "Propietario incorrecto", 400
        else:
            return "Billete no localizado", 400

    def find_ticket(track):
        lchain = len(blockchain.chain)-1
        while lchain >= 0:
            block = blockchain.chain[lchain]
            tickets = block['tickets']
            for ticket in tickets:
                if ticket['Tracker'] == track:
                    return Ticket.dict_to_ticket(ticket)
            lchain -= 1
        return None

    @app.route("/generate_ticket", methods=['POST'])
    def add_ticket():
        json_got = request.get_json()
        ticket_keys = ["Tracker", "Company", "Origin", "Destination", "Date&hour", "Seat"]
        if not all(key in json_got for key in ticket_keys):
            return 'There is an element of the ticket missing', 400
        ticket = Ticket.dict_to_ticket(json_got)
        index = blockchain.add_ticket(ticket)
        response = {
            'message': f"The ticket will be added to the block {index}"
        }
        return jsonify(response), 200


    @app.route("/connect_node", methods=['POST'])
    def connect_node():
        json_got = request.get_json()
        nodes = json_got.get('nodes')
        if nodes is None:
            return "No nodes", 400
        for node in nodes:
            blockchain.add_node(node)
        response = {'message': "All nodes connected. Policoin Blockchain contains the following nodes:",
                    'total_nodes': list(blockchain.nodes)}
        return jsonify(response), 200


    @app.route("/replace_chain", methods=['GET'])
    def replace_chain():
        is_chain_replaced = blockchain.replace_chain()
        if is_chain_replaced:
            response = {
                'message': 'The nodes had diferent chains so the chain has been replaced by the longest chain',
                'new_chain': blockchain.chain
            }
        else:
            response = {
                'message': 'Chain not changed',
                'actual_chain': blockchain.chain
            }
        return jsonify(response), 200

    @app.route("/get_tickets", methods=['GET'])
    def get_tickets():
        tickets = []
        tickets_owner = []
        owner = request.args.get("owner")
        chain = blockchain.chain
        i = len(chain)-1
        while i >= 0:
            block = chain[i]
            for ticket in block['tickets']:
                if ticket['Tracker'] not in tickets:
                    if owner == ticket['Owner']:
                        tickets_owner.append(ticket)
                    tickets.append(ticket['Tracker'])
            i -= 1
        if tickets_owner:
            response = {
                "Message": f"The tickets owned by {owner} are the list shown",
                "Tickets": tickets_owner
            }
        else:
            response = {
                "Message": f"There are no tickets owned by {owner}"
            }
        return jsonify(response), 200


    app.run(host='0.0.0.0', port=5002)
