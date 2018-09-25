from flask import Flask,jsonify,request, send_from_directory
from wallet import Wallet
from flask_cors import CORS
from blockchain import Blockchain
app = Flask(__name__)

CORS(app)


@app.route('/',methods=['GET'])
def get_node_ui():
    return send_from_directory('ui','node.html')

@app.route('/network',methods=['GET'])
def get_network_ui():
    return send_from_directory('ui','network.html')


@app.route('/balance',methods=['GET'])
def get_balance():
    balance = blockchain.get_balance()
    if balance != None:
        response = {
            'message':'Fetched balance sucesesfully',
            'funds': balance
            }      
        return jsonify(response),201
    else:
        response = {
            'message': 'Loading balance failed',
            'wallet_set_up':wallet.public_key != None
            }
        return jsonify(response),500



@app.route('/wallet',methods=['POST'])
def create_keys():
    wallet.create_keys()
    if wallet.save_keys():       
        global blockchain
        blockchain = Blockchain(wallet.public_key,port)
        response = {
            'public_key': wallet.public_key,
            'private_key':wallet.private_key,
            'funds':blockchain.get_balance()
            }
        return jsonify(response),201
    else:
        response = {
            'message': 'Saving the keys failed'
            }
        return jsonify(response),500


@app.route('/wallet',methods=['GET'])
def load_keys():
    if wallet.load_keys():
        
        global blockchain
        blockchain = Blockchain(wallet.public_key,port)
        response = {
            'public_key': wallet.public_key,
            'private_key':wallet.private_key,
            'funds':blockchain.get_balance()
            }
        return jsonify(response),201
    else:
        response = {
            'message': 'Load the keys failed'
            }
        return jsonify(response),500


@app.route('/broadcast-transaction',methods=["POST"])
def broadcast_transaction():
    values = request.get_json()
    if not values:
        response = {'message':'No data found.'}
        return jsonify(response),400
    required = ['sender','recipient','amount','signature']
    if not all(key in values for key in required):
        response = {'message':'No data is missing.'}
        return jsonify(response),400
    success = blockchain.add_transaction(values['recipient'],
                               values['sender'],
                               values['signature'],
                               values['amount'],
                               is_receiving=True)
    if success:
        response = {
            'message':'Sucessfully added transaction',
            'transaction':{
                'sender':values['sender'],
                'recipient':values['recipient'],
                'amount': values['amount'],
                'signature':values['signature']
                }
        }
        return jsonify(response),201
    else:
        response = {
            'message': 'Creating a transaction field'
            }
        return jsonify(response),500


@app.route('/broadcast-block',methods=['POST'])
def broadcast_block():
    values = request.get_json()
    if not values:
        response = {'message':'No data found.'}
        return jsonify(response),400
    if 'block' not in values:
        response = {'message':'Some data is missing'}
        return jsonify(response),400
    block = values['block']
    if block['index'] == blockchain.chain[-1].index + 1:
        if blockchain.add_block(block):
            response = {'message':'Block added'}
            return jsonify(response),201
        else:
            response = {'message':'Block seem invalid'}
            return jsonify(response),409
    elif block['index'] > blockchain.chain[-1].index:
        response = {'message':'Block chain seem different from local blockchain'}
        blockchain.resolve_conflicts = True
        return jsonify(response),200
    else:
        response = {'message':'Block chain seem to be shorter, block not added'}
        return jsonify(response),409



@app.route('/transaction',methods=['POST'])
def add_transaction():
    if wallet.public_key == None:
        response = {
            'message':'now allet setup'
            }
        return jsonify(response),400
    values = request.get_json()
    if not values:
        response = {
            'message': 'No data found.'
            }
        return jsonify(response),400
    required_fields = ['recipient','amount']
    if not all(field in values for field in required_fields):
        response = {
            'message':'Required data is missing.'
            }
        return jsonify(response),400
    recipient = values['recipient']
    amount = values['amount']
    signature = wallet.sign_transaction(wallet.public_key,recipient,amount)
    success = blockchain.add_transaction(recipient,wallet.public_key,signature,amount)
    if success:
        response = {
            'message':'Sucessfully added transaction',
            'transaction':{
                'sender':wallet.public_key,
                'recipient':recipient,
                'amount': amount,
                'signature':signature
                },
            'funds':blockchain.get_balance()
        }
        return jsonify(response),201
    else:
        response = {
            'message': 'Creating a transaction field'
            }
        return jsonify(response),500

@app.route('/mine',methods=['POST'])
def mine():
    if blockchain.resolve_conflicts == True:
        response = {'message':'resove confilct first,block not added'}
        return jsonify(response),409
    block = blockchain.mine_block()
    if block != None:
        dict_block = block.__dict__.copy()
        dict_block['transactions'] = [tx.__dict__ for tx in dict_block['transactions']] 
        response = {
            'message':'Block added successfully',
            'block':dict_block,
             'funds':blockchain.get_balance()
            }
        return jsonify(response),201
    else:
        response = {
            'message':'Adding a block failed',
            'wallet_set_up':wallet.public_key != None
           
            }
        return jsonify(response),500


@app.route('/resolve-conflicts',methods=['POST'])
def resolve_conflicts():
    replaced = blockchain.resolve()
    if replaced:
        response = {'message':'Chain was replaced!'}
    else:
        response = {'message':'Local chain kept'}
    return jsonify(response),200


@app.route('/transactions',methods=['GET'])
def get_open_transaction():
    transaction = blockchain.get_open_transactions()
    dict_transactions = [tx.__dict__ for tx in transaction]
    return jsonify(dict_transactions),200
    #response={
    #    'message':'Fetched transaction sucessfully',
    #    'transactions':dict_transaction
    #    }
@app.route('/chain',methods=['GET'])
def get_chain():
    chain_snapshot = blockchain.chain
    dict_chain = [block.__dict__.copy() for block in chain_snapshot]
    for dict_block in dict_chain:
        dict_block['transactions'] = [tx.__dict__ for tx in dict_block['transactions']]
    return jsonify(dict_chain), 200


@app.route('/node',methods=['POST'])
def add_node():
    values = request.get_json()
    if not values:
        response = {
            'message':'No data attached.'
            }
        return jsonify(response),400
    if 'node' not in values:
        response = {
            'message':'No data found.'
            }
        return jsonify(response),400
    node = values['node']

    blockchain.add_pear_node(node)
    response = {
            'message':'Node added sucessfully.',
            'all_nodes':blockchain.get_peer_nodes()
            }
    return jsonify(response),201

@app.route('/node/<node_url>',methods=['DELETE'])
def remove_node(node_url):
    if node_url == '' or node_url == None:
        response = {
            'message':'No node found'
            }
        return jsonify(response),400
    blockchain.remove_peer_node(node_url)
    response = {
            'message':'node removed',
            'all_nodes':blockchain.get_peer_nodes()
            }
    return jsonify(response),200



@app.route('/nodes',methods=['GET'])
def get_nodes():
    nodes = blockchain.get_peer_nodes()
    response = {
            'all_nodes':nodes
            }
    return jsonify(response),200



if __name__ == '__main__':
    from argparse import ArgumentParser
    parger = ArgumentParser()
    parger.add_argument('-p','--port',type=int,default=5001)
    args = parger.parse_args()
    port = args.port
    wallet = Wallet(port)
    blockchain = Blockchain(wallet.public_key,port)
    app.run(host='0.0.0.0',port=port)
