# 🔥 Base NFT Sniper Bot (AutoCollector)

An automated NFT sniper bot built for the [Base Network](https://base.org), designed to **monitor NFT collections in real-time**, **filter based on rarity**, and **simulate minting smart contracts**. Fully integrated with **Telegram alerts**, powered by **Reservoir API** and **Moralis**, and crafted for the Devfolio hackathon.

---

## 🚀 Features

- ✅ Real-time scanning of top NFT collections on Base.
- 🎯 Filters by:
  - Max price in ETH
  - Min number of owners
  - Keyword inclusion/exclusion
  - Rarity score from Moralis
- 🤖 Simulated smart contract minting (with support for `mint()`, `mint(quantity)`, and `claim()`).
- 📬 Telegram bot alerts for matching NFTs.
- 🧪 Simulation Mode for safe testing without spending ETH.

---

## 📸 Demo

https://vimeo.com/1081686737

---

## 📦 Technologies Used

- Python 3
- Web3.py
- Reservoir API
- Moralis API
- Telegram Bot API
- AsyncIO + AioHTTP

---

## ⚙️ .env Configuration

Create a `.env` file based on the `.env.example` provided:

```env
SMART_WALLET_ADDRESS=0xYourWalletAddress
PRIVATE_KEY=your_private_key
RESERVOIR_API_KEY=your_reservoir_api_key
MORALIS_API_KEY=your_moralis_api_key
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
MAX_PRICE_ETH=0.01
MIN_OWNERS=10
MIN_RARITY_SCORE=50
SIMULATION_MODE=true
COLLECTION_LIMIT=20
TOKENS_LIMIT=5
