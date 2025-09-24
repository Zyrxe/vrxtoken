import json
import hashlib
import time
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string
from uuid import uuid4

# --- Konfigurasi Koin ---
COIN_NAME = "VRX"
COIN_SYMBOL = "VRX"
GENESIS_REWARD = 1000000.0
BLOCK_REWARD = 50.0
BLOCK_TIME_SECONDS = 600 # 10 menit
DIFFICULTY_ADJUSTMENT_BLOCKS = 2016
TARGET_DIFFICULTY_PREFIX = "0000"

# --- Basis Data Sederhana (File JSON) ---
blockchain_file = "blockchain_data.json"
wallet_file = "wallet_data.json"

def save_data(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def load_data(filename, default_data):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default_data

# --- Kelas dan Fungsi Blockchain ---
class Blockchain:
    def __init__(self):
        self.chain = load_data(blockchain_file, [])
        self.current_transactions = []
        if not self.chain:
            self.create_genesis_block()

    def create_genesis_block(self):
        # Transaksi Genesis: 1 juta VRX ke address founder
        genesis_tx = {
            'sender': 'genesis_block',
            'recipient': str(uuid4()).replace('-', ''),
            'amount': GENESIS_REWARD,
            'timestamp': time.time(),
            'signature': 'genesis_signature'
        }
        self.current_transactions.append(genesis_tx)
        self.new_block(proof=100, previous_hash='1', transactions=[genesis_tx])
        self.current_transactions = []
        save_data(self.chain, blockchain_file)

    def new_block(self, proof, previous_hash=None, transactions=None):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time.time(),
            'transactions': transactions or self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }
        self.current_transactions = []
        self.chain.append(block)
        save_data(self.chain, blockchain_file)
        return block

    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_proof):
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        return proof

    def valid_proof(self, last_proof, proof):
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:len(TARGET_DIFFICULTY_PREFIX)] == TARGET_DIFFICULTY_PREFIX

    def new_transaction(self, sender, recipient, amount):
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'timestamp': time.time()
        })
        return self.last_block['index'] + 1

    def get_difficulty(self):
        if len(self.chain) % DIFFICULTY_ADJUSTMENT_BLOCKS == 0 and len(self.chain) > 0:
            # Sederhana: jika jumlah blok melebihi 2016, tingkatkan kesulitan
            return TARGET_DIFFICULTY_PREFIX + "0"
        return TARGET_DIFFICULTY_PREFIX

    def get_balance(self, address):
        balance = 0
        for block in self.chain:
            for transaction in block['transactions']:
                if transaction['recipient'] == address:
                    balance += transaction['amount']
                if transaction['sender'] == address:
                    balance -= transaction['amount']
        return balance

# --- Kelas dan Fungsi Wallet (Sangat Sederhana) ---
class Wallet:
    def __init__(self):
        self.wallets = load_data(wallet_file, {})

    def create_address(self):
        address = str(uuid4()).replace('-', '')
        self.wallets[address] = {'private_key': str(uuid4()).replace('-', '')}
        save_data(self.wallets, wallet_file)
        return address

    def get_all_wallets(self):
        return self.wallets

# --- Aplikasi Web Flask ---
app = Flask(__name__)
blockchain = Blockchain()
wallet = Wallet()

# --- Halaman Utama Explorer ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VRX Coin Explorer</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
    </style>
</head>
<body class="bg-gray-100 text-gray-800 p-4">
    <div class="container mx-auto max-w-7xl">
        <div class="bg-white rounded-xl shadow-lg p-6 md:p-8 mb-8">
            <h1 class="text-3xl md:text-4xl font-bold text-center text-blue-600 mb-6">VRX Coin Explorer</h1>
            <p class="text-center text-gray-600 mb-4">Node dan explorer dalam satu file. Mining, kirim transaksi, dan cek saldo langsung di sini!</p>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <!-- Mining Section -->
                <div class="bg-green-50 border border-green-200 rounded-lg p-6 flex flex-col items-center">
                    <h2 class="text-2xl font-semibold text-green-800 mb-4">Mining</h2>
                    <p class="text-center text-gray-600 mb-4">
                        Menambang blok baru dan mendapatkan {{ BLOCK_REWARD }} {{ COIN_SYMBOL }}.
                    </p>
                    <button id="mineButton" class="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-6 rounded-full transition-colors shadow-md">
                        Mulai Mining
                    </button>
                    <p id="mineStatus" class="mt-4 text-center text-sm font-medium"></p>
                </div>
                
                <!-- Wallet Section -->
                <div class="bg-purple-50 border border-purple-200 rounded-lg p-6 flex flex-col items-center">
                    <h2 class="text-2xl font-semibold text-purple-800 mb-4">Wallet & Transaksi</h2>
                    <p class="text-center text-gray-600 mb-4">
                        Buat address, cek saldo, atau kirim koin.
                    </p>
                    <div class="w-full space-y-4">
                        <div>
                            <button id="createWalletButton" class="w-full bg-purple-500 hover:bg-purple-600 text-white font-bold py-2 px-6 rounded-full transition-colors shadow-md">
                                Buat Address Baru
                            </button>
                            <p id="newAddress" class="mt-2 text-center text-sm break-all font-mono text-gray-700"></p>
                        </div>
                        <div class="space-y-2">
                            <input type="text" id="addressInput" placeholder="Masukkan Address" class="w-full p-2 border border-gray-300 rounded-md">
                            <button id="checkBalanceButton" class="w-full bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-6 rounded-full transition-colors shadow-md">
                                Cek Saldo
                            </button>
                            <p id="balanceStatus" class="mt-2 text-center text-sm font-medium"></p>
                        </div>
                    </div>
                </div>
            </div>
            
            <h2 class="text-2xl md:text-3xl font-bold text-center text-blue-600 mt-10 mb-6">Blok</h2>
            <div id="blocksContainer" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <!-- Blocks will be injected here by JavaScript -->
            </div>
        </div>
    </div>

    <script>
        const API_URL = window.location.origin;

        function fetchBlocks() {
            fetch(`${API_URL}/blocks`)
                .then(response => response.json())
                .then(data => {
                    const container = document.getElementById('blocksContainer');
                    container.innerHTML = '';
                    data.forEach(block => {
                        const blockDiv = document.createElement('div');
                        blockDiv.className = 'bg-blue-50 border border-blue-200 rounded-lg p-4 transition-transform transform hover:scale-105';
                        
                        let transactionsHtml = '';
                        block.transactions.forEach(tx => {
                            const date = new Date(tx.timestamp * 1000).toLocaleString();
                            transactionsHtml += `
                                <div class="bg-gray-100 p-2 rounded-md my-2 text-xs">
                                    <p><span class="font-medium">Dari:</span> <span class="break-all">{{ COIN_SYMBOL }}</span> ${tx.sender}</p>
                                    <p><span class="font-medium">Ke:</span> <span class="break-all">{{ COIN_SYMBOL }}</span> ${tx.recipient}</p>
                                    <p><span class="font-medium">Jumlah:</span> ${tx.amount} {{ COIN_SYMBOL }}</p>
                                    <p><span class="font-medium">Waktu:</span> ${date}</p>
                                </div>
                            `;
                        });
                        
                        blockDiv.innerHTML = `
                            <h2 class="text-xl font-semibold text-blue-800 mb-2">Block #${block.index}</h2>
                            <p class="truncate text-gray-600 mb-1">
                                <span class="font-medium">Hash:</span> ${block.proof}
                            </p>
                            <p class="truncate text-gray-600">
                                <span class="font-medium">Hash Sebelumnya:</span> ${block.previous_hash.substring(0, 15)}...
                            </p>
                            <p class="text-sm text-gray-500 mt-2">
                                Transaksi: ${block.transactions.length}
                            </p>
                            <div class="mt-4">
                                <h3 class="text-sm font-semibold text-gray-700">Detail Transaksi:</h3>
                                ${transactionsHtml}
                            </div>
                        `;
                        container.appendChild(blockDiv);
                    });
                })
                .catch(error => console.error('Error fetching blocks:', error));
        }

        document.getElementById('mineButton').addEventListener('click', () => {
            const status = document.getElementById('mineStatus');
            status.textContent = 'Menambang... Mohon tunggu.';
            status.className = 'mt-4 text-center text-sm font-medium text-yellow-600';
            fetch(`${API_URL}/mine`)
                .then(response => response.json())
                .then(data => {
                    status.textContent = `Blok #${data.index} berhasil ditambang! Proof: ${data.proof}`;
                    status.className = 'mt-4 text-center text-sm font-medium text-green-600';
                    fetchBlocks();
                })
                .catch(error => {
                    console.error('Error mining:', error);
                    status.textContent = 'Gagal menambang. Cek konsol untuk detail.';
                    status.className = 'mt-4 text-center text-sm font-medium text-red-600';
                });
        });

        document.getElementById('createWalletButton').addEventListener('click', () => {
            const newAddressP = document.getElementById('newAddress');
            fetch(`${API_URL}/wallet/create`)
                .then(response => response.json())
                .then(data => {
                    newAddressP.textContent = `Address Baru: ${data.address}`;
                    newAddressP.style.display = 'block';
                })
                .catch(error => console.error('Error creating wallet:', error));
        });

        document.getElementById('checkBalanceButton').addEventListener('click', () => {
            const address = document.getElementById('addressInput').value;
            const status = document.getElementById('balanceStatus');
            if (!address) {
                status.textContent = 'Silakan masukkan address.';
                status.className = 'mt-2 text-center text-sm font-medium text-red-600';
                return;
            }
            fetch(`${API_URL}/wallet/balance?address=${address}`)
                .then(response => response.json())
                .then(data => {
                    status.textContent = `Saldo: ${data.balance} {{ COIN_SYMBOL }}`;
                    status.className = 'mt-2 text-center text-sm font-medium text-green-600';
                })
                .catch(error => {
                    console.error('Error checking balance:', error);
                    status.textContent = 'Gagal mengecek saldo. Address mungkin tidak valid.';
                    status.className = 'mt-2 text-center text-sm font-medium text-red-600';
                });
        });

        // Fetch blocks on initial load
        fetchBlocks();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, BLOCK_REWARD=BLOCK_REWARD, COIN_SYMBOL=COIN_SYMBOL)

@app.route('/mine', methods=['GET'])
def mine():
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # Tambahkan transaksi 'coinbase' untuk reward miner
    blockchain.new_transaction(
        sender="0",
        recipient=str(uuid4()).replace('-', ''), # address acak untuk demo
        amount=BLOCK_REWARD
    )

    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "Blok baru berhasil ditambang",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])
    response = {'message': f'Transaksi akan ditambahkan ke Blok {index}'}
    return jsonify(response), 201

@app.route('/blocks', methods=['GET'])
def get_blocks():
    return jsonify(blockchain.chain), 200

@app.route('/wallet/create', methods=['GET'])
def create_wallet_route():
    address = wallet.create_address()
    return jsonify({"address": address}), 200

@app.route('/wallet/balance', methods=['GET'])
def get_balance():
    address = request.args.get('address')
    if not address:
        return 'Missing address parameter', 400
    balance = blockchain.get_balance(address)
    return jsonify({"address": address, "balance": balance}), 200

if __name__ == '__main__':
    # Hapus file database jika ada untuk memulai ulang
    if os.path.exists(blockchain_file):
        os.remove(blockchain_file)
    if os.path.exists(wallet_file):
        os.remove(wallet_file)
    
    # Jalankan server Flask
    app.run(host='0.0.0.0', port=5000)
