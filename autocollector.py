import asyncio
import aiohttp
import logging
from web3 import Web3
from dotenv import load_dotenv
import os
from telegram import Bot
import requests

# Load .env variables
load_dotenv()

COLLECTION_LIMIT = int(os.getenv("COLLECTION_LIMIT", 20))
TOKENS_LIMIT = int(os.getenv("TOKENS_LIMIT", 5))


# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Blockchain setup
BASE_RPC_URL = "https://mainnet.base.org"
w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))

# Wallet
SMART_WALLET_ADDRESS = Web3.to_checksum_address(os.getenv("SMART_WALLET_ADDRESS"))
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

# Filters from .env
MAX_PRICE_ETH = float(os.getenv("MAX_PRICE_ETH", "0.01"))
MIN_OWNERS = int(os.getenv("MIN_OWNERS", "10"))
MIN_RARITY_SCORE = float(os.getenv("MIN_RARITY_SCORE", "0"))  # Optional, default to 0

# Keywords
KEYWORDS = ["art", "avatar", "mint", "drop", "punk", "rare", "pixel", "ai"]
EXCLUDE_WORDS = ["test", "fake", "scam", "copy"]

# API Keys
RESERVOIR_API_KEY = os.getenv("RESERVOIR_API_KEY")
MORALIS_API_KEY = os.getenv("MORALIS_API_KEY")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
telegram_bot = Bot(token=TELEGRAM_BOT_TOKEN)


SIMULATION_MODE = os.getenv("SIMULATION_MODE", "true").lower() == "true"

# === Data Fetching ===
async def fetch_collections(session, limit=20):
    headers = {"accept": "application/json", "x-api-key": RESERVOIR_API_KEY}
    url = f"https://api.reservoir.tools/collections/v5?chain=base&limit={limit}&sortBy=allTimeVolume"
    async with session.get(url, headers=headers) as resp:
        return await resp.json()

async def fetch_tokens(session, contract_address, limit=5):
    headers = {"accept": "application/json", "x-api-key": RESERVOIR_API_KEY}
    url = f"https://api.reservoir.tools/tokens/v6?chain=base&contract={contract_address}&limit={limit}"
    async with session.get(url, headers=headers) as resp:
        return await resp.json()

# === Minting ===
def try_mint(nft_contract_address):
    logging.info(f"🚀 Minting from contract: {nft_contract_address}")

    if SIMULATION_MODE:
        logging.info(f"🧪 SIMULATION MODE: Mint not executed for contract: {nft_contract_address}")
        return True

    abi_variants = [
        {"name": "mint", "inputs": [], "stateMutability": "payable", "type": "function"},
        {"name": "mint", "inputs": [{"internalType": "uint256", "name": "quantity", "type": "uint256"}], "stateMutability": "payable", "type": "function"},
        {"name": "claim", "inputs": [], "stateMutability": "payable", "type": "function"},
    ]

    for abi in abi_variants:
        try:
            contract = w3.eth.contract(address=nft_contract_address, abi=[abi])
            nonce = w3.eth.get_transaction_count(SMART_WALLET_ADDRESS)
            func = contract.get_function_by_name(abi["name"])
            tx = func(1).build_transaction({
                "from": SMART_WALLET_ADDRESS,
                "nonce": nonce,
                "gas": 200000,
                "gasPrice": w3.to_wei("0.0000005", "ether"),
                "value": w3.to_wei(MAX_PRICE_ETH, "ether")
            }) if abi["inputs"] else func().build_transaction({
                "from": SMART_WALLET_ADDRESS,
                "nonce": nonce,
                "gas": 200000,
                "gasPrice": w3.to_wei("0.0000005", "ether"),
                "value": w3.to_wei(MAX_PRICE_ETH, "ether")
            })

            signed_txn = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            logging.info(f"✅ Minted! TX Hash: {w3.to_hex(tx_hash)}")
            return True

        except Exception as e:
            continue

    logging.warning(f"⚠️ Mint failed for contract: {nft_contract_address}")
    return False



# === Rarity Score ===
def get_rarity_score(contract_address, token_id):
    try:
        headers = {"X-API-Key": MORALIS_API_KEY, "accept": "application/json"}
        url = f"https://deep-index.moralis.io/api/v2/nft/{contract_address}/{token_id}?chain=base&format=decimal"
        response = requests.get(url, headers=headers)
        data = response.json()
        for attr in data.get("attributes", []):
            if attr.get("trait_type", "").lower() == "rarity":
                return float(attr.get("value", 0))
        return 0.0
    except Exception as e:
        logging.warning(f"⚠️ Rarity fetch error for {contract_address}/{token_id}: {e}")
        return 0.0

# === Telegram Alert ===
async def notify_telegram(nft):
    msg = (
        f"🎯 Matching NFT Found!\n\n"
        f"Name: {nft['name']}\n"
        f"Price: {nft['price']:.4f} ETH\n"
        f"Owners: {nft['owners']}\n"
        f"Rarity Score: {nft['rarity']:.2f}\n"
        f"Contract: {nft['address']}"
    )
    await telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)

# === NFT Filtering ===
async def fetch_and_filter_nfts():
    async with aiohttp.ClientSession() as session:
        collections = (await fetch_collections(session, limit=COLLECTION_LIMIT)).get("collections", [])
        logging.info(f"🔵 {len(collections)} collections fetched.")

        for collection in collections:
            address = collection.get("primaryContract")
            if not address:
                continue

            try:
                tokens = (await fetch_tokens(session, address, limit=TOKENS_LIMIT)).get("tokens", [])
                for token in tokens:
                    token_info = token.get("token", {})
                    name = (token_info.get("name") or "unknown").lower()
                    price = float(token.get("market", {}).get("floorAsk", {}).get("price", {}).get("amount", {}).get("decimal") or 0.0)
                    owners = int(token_info.get("ownerCount") or 0)
                    token_id = token_info.get("tokenId")
                    addr = Web3.to_checksum_address(token_info["contract"])
                    rarity = get_rarity_score(addr, token_id)

                    # Rejection logic with reason
                    if any(ex in name for ex in EXCLUDE_WORDS):
                        reason = "❌ Excluded keyword"
                    elif price > MAX_PRICE_ETH:
                        reason = f"❌ Price {price:.4f} > max {MAX_PRICE_ETH:.4f}"
                    elif owners < MIN_OWNERS:
                        reason = f"❌ Owners {owners} < min {MIN_OWNERS}"
                    elif not any(kw in name for kw in KEYWORDS):
                        reason = "❌ No keyword match"
                    elif rarity < MIN_RARITY_SCORE:
                        reason = f"❌ Rarity {rarity:.2f} < min {MIN_RARITY_SCORE:.2f}"
                    else:
                        nft = {
                            "name": name,
                            "price": price,
                            "owners": owners,
                            "address": addr,
                            "rarity": rarity
                        }
                        logging.info(f"🎯 MATCH FOUND: {nft}")
                        await notify_telegram(nft)
                        try_mint(addr)
                        continue

                    logging.info(
                        f"🧾 {name} | Price: {price:.4f} ETH | Owners: {owners} | Rarity: {rarity:.2f} → ⛔ Rejected: {reason}"
                    )
            except Exception as e:
                logging.warning(f"⚠️ Token fetch error for {address}: {e}")

# === Main Loop ===
async def main_loop():
    while True:
        await fetch_and_filter_nfts()
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main_loop())
