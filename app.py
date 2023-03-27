import discord
import requests
from dotenv import load_dotenv
import os
import json
from web3 import Web3


load_dotenv()

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

        contract_address = get_contract_address(collection_name_or_id)

    if contract_address is None:
        await message.channel.send(f"Could not find contract address for {collection_name_or_id}")
        return

    profit = calculate_profit(wallet_address, contract_address)
    await message.channel.send(f"Profit for {wallet_address} in {collection_name_or_id}: {profit:.2f} ETH")

# Start Discord client
client.run(os.getenv('DISCORD_TOKEN'))
