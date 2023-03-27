from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import discord
import requests
from dotenv import load_dotenv
import os
import json
from web3 import Web3


app = Flask(__name__)


load_dotenv()

app = Flask(__name__)

intents = discord.Intents.all()
intents.members = True  # subscribe to the on_member_join and on_member_remove events

client = discord.Client(intents=intents)


ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')

# Instantiate Web3 with Infura API endpoint
web3 = Web3(Web3.HTTPProvider(
    f"https://mainnet.infura.io/v3/{os.getenv('INFURA_API_KEY')}"))


def get_contract_address(collection_name_or_id):

    if web3.isAddress(collection_name_or_id):
        contract_address = collection_name_or_id
        return contract_address

    # Use OpenSea API to search for the contract address of the NFT collection
    response = requests.get(
        f'https://api.opensea.io/api/v1/collection/{collection_name_or_id}/')
    if response.ok:
        data = response.json()
        collection = data.get('collection')
        if collection and collection.get('primary_asset_contracts'):
            contract_address = collection.get('primary_asset_contracts')[
                0].get('address')
            return contract_address
    return None


def calculate_profit(wallet_address, contract_address):
    # API endpoint to retrieve transaction data for a given wallet address and contract address
    api_url = f"https://api.etherscan.io/api?module=account&action=txlist&address={wallet_address}&startblock=0&endblock=99999999&sort=asc&apikey={ETHERSCAN_API_KEY}"

    # Send an HTTP GET request to the API endpoint
    response = requests.get(api_url)

    # Parse the response JSON
    data = json.loads(response.text)

    # Calculate the total cost and current value of the NFT collection
    total_cost = 0
    current_value = 0
    for transaction in data["result"]:
        # Check if the transaction is a transfer to the NFT collection contract
        if transaction["to"] == contract_address:
            total_cost += float(transaction["value"]) / 1e18

        # Check if the transaction is a transfer from the NFT collection contract
        if transaction["from"] == contract_address:
            current_value += float(transaction["value"]) / 1e18

    # Calculate the profit made on the NFT collection
    profit = current_value - total_cost

    # Return the profit value
    return profit


@app.route('/')
def index():
    return 'Hello World!'


@app.route('/profit', methods=['POST'])
def calculate_profits():
    data = request.json
    wallet_address = data.get('wallet_address')
    collection_name_or_id = data.get('collection_name_or_id')

    contract_address = get_contract_address(collection_name_or_id)

    if contract_address is None:
        return {'error': f"Could not find contract address for {collection_name_or_id}"}

    profit = calculate_profit(wallet_address, contract_address)
    return {'profit': profit}


@client.event
async def on_ready():
    print(f'Logged in as {client.user}')


@client.event
async def on_message(message):
    print(
        f'Message from {message.author}: {message.content}, and the client user is {client.user}, {message}')

    if not message.content:
        await message.channel.send('No message content')
        print('No message content')

    elif message.author == client.user:
        return

    if message.content.startswith('/profit'):
        await message.channel.send("Please enter your wallet address:")
        wallet_address = await client.wait_for('message', check=lambda m: m.author == message.author)
        wallet_address = wallet_address.content.strip()

        await message.channel.send("Please enter the contract address or collection name:")
        collection_name_or_id = await client.wait_for('message', check=lambda m: m.author == message.author)
        collection_name_or_id = collection_name_or_id.content.strip()

        data = {'wallet_address': wallet_address,
                'collection_name_or_id': collection_name_or_id}
        response = request.post(
            'diamond-bot.azurewebsites.net/profit', json=data)

    if response.ok:
        result = response.json()
        if 'profit' in result:
            await message.channel.send(f"Profit for {wallet_address} in {collection_name_or_id}: {result['profit']:.2f} ETH")
        elif 'error' in result:
            await message.channel.send(result['error'])
    else:
        await message.channel.send('Error calculating profit')


client.run(os.getenv('DISCORD_TOKEN'))


if __name__ == '__main__':
    app.run()
