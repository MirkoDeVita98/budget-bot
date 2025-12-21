![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)

# 💸 Telegram Budget Bot

A personal Telegram bot to track expenses and budgets directly from Telegram.  
Designed to be simple, transparent, and fully under your control.

Key highlights:

- 📊 Monthly overall budget tracking
- 🗂️ Category-based expenses (Food, Transport, Subscriptions, etc.)
- ⏱️ Daily, Monthly, and Yearly budget rules
- 💱 Multi-currency expenses with automatic conversion to CHF
- 🔁 Undo last expense, monthly reset, full reset
- 🧱 Local SQLite storage (no cloud, no third parties)

All amounts are **computed and reported in your BASE_CURRENCY**, even when entered in foreign currencies.

---

## Features

### Budgets
- Set an overall monthly budget that represents your maximum allowed spending
- Instantly see how much money you still have available
- Inspect past months to review historical spending

### Budget Rules
Budget rules define your *planned* spending and are automatically aggregated per month.

- **Daily rules**  
  Example: `Food 15 CHF/day` → converted automatically based on number of days in the month

- **Monthly rules**  
  Example: `Subscriptions 35 CHF/month`

- **Yearly rules**  
  Example: `Car insurance 600 CHF/year` → automatically divided by 12

- **Named rules**  
  Useful for individual subscriptions (e.g. Netflix, PSN, Spotify)

Rules are always stored internally in **BASE_CURRENCY** to ensure consistent reporting. You can set it in the `.env`, e.g **BASE_CURRENCY=CHF**.

### Expenses
- Add expenses at any time via Telegram commands
- Support for **foreign currencies** (EUR, USD, etc.)
- Automatic FX conversion to CHF at entry time
- Store both original amount and converted CHF amount
- Undo the last expense of the current month
- Reset all expenses for the current month

### FX Conversion
- Uses ECB reference rates via the **Frankfurter API**
- FX rates are fetched online and cached daily
- Each expense stores:
  - Original currency
  - Original amount
  - FX rate
  - Converted CHF amount

---

## Project Structure

```text
budget-bot/
├── .env                  # secrets (NOT committed)
├── .env.example          # environment variable template
├── .gitignore
├── requirements.txt
├── main.py               # application entry point
├── budget.db             # SQLite database (created at runtime)
└── src/
    ├── __init__.py
    ├── config.py         # configuration & environment variables
    ├── db.py             # database schema & migrations
    ├── fx.py             # FX API integration & caching
    ├── services.py       # business logic (budgets, rules, expenses)
    └── handlers.py       # Telegram command handlers
```

## Requirements

- Python **3.10+** (recommended: 3.11)
- A Telegram account
- A Telegram bot token (see below)

---

## Creating the Telegram Bot

1. Open Telegram
2. Search for **@BotFather**
3. Start a chat and send:
   ```text
   /newbot
   ```
4. Choose:
   - A display name (any text)
   - A username ending in `bot` (e.g. `my_budget_bot`)

5. Copy the token provided by BotFather

```text
123456789:AAHkxxxxxxxxxxxxxxxxxxxx
```
- If the token leaks:

```text
@BotFather
/mybots
(select your bot)
Revoke token
```

## Installation

### Clone the repository
```bash
git clone https://github.com/MirkoDeVita98/budget-bot.git
cd budget-bot
```

### Create and activate a virtual environment
```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### Install the Dependencies
```bash
pip install -r requirements.txt
```

## Environment Variables
`.env.example` (committed to git)
```bash
BOT_TOKEN=
BASE_CURRENCY=CHF
DB_PATH=budget.db
```
`.env` (local only, NOT committed)
```bash
BOT_TOKEN=PASTE_YOUR_TELEGRAM_BOT_TOKEN_HERE
BASE_CURRENCY=CHF
DB_PATH=budget.db
```

## Running the Bot
```bash
python main.py
```
On Telegram:
```bash
/start
```

## Usage Guide

### Set Monthly Budget
```bash
/setbudget 3000
```

### Define Budget Rules
- Daily rule
```bash
/setdaily Food 15
```
- Monthly rule
```bash
/setmonthly Rent 700
```
- Monthly rule with name and currency
```bash
/setmonthly PSN 16.99 EUR Subscription
```
- Yearly rule
```bash
/setyearly CarInsurance 600 Transport
```
- View and manage rules
```bash
/rules
/delrule <id>
```
### Add Expenses
- CHF expense
```bash
/add Food Groceries 62.40
```
- Foreign currency expense
```bash
/add Travel Taxi 20 EUR
```
### List and Delete Expenses
- List expenses for the current month (default limit = 50):
```bash
/expenses
```
- List expenses for a specific month:
```bash
/expenses 2025-12
```
- List expenses with a custom limit:
```bash
/expenses 2025-12 100
```
The limit parameter controls how many of the most recent expenses are shown, to avoid very long Telegram messages.
- Delete a specific expense by ID:
```bash
/delexpense <id>
```
### Reports
```bash
/status
/status Food
/month 2025-02
```
### Undo & Reset
- Undo last expense:
```bash
/undo
```
- Reset current month expenses:
```bash
/resetmonth
```
- Reset everything:
```bash
/resetall yes
```
⚠️ `/resetall yes` permanently deletes all stored data.
## Data Storage
- Uses a local SQLite database.
`budget.db`
- The schema is created automatically at startup.
## Security Notes
- Never commit `.env`
- Never share your Telegram bot token
- If exposed:
```bash
@BotFather
/mybots
Revoke token
```
## TODO / Future Improvements
The following features are planned or under consideration:
- 📄 Automatic expense extraction using a self-hosted LLM
  - Parse bank statements (PDFs)
  - Extract merchant, amount, date, and currency
  - Automatically classify transactions into categories
- 🧠 LLM-powered categorization
  - Use a locally hosted small language model
  - Zero cloud dependency
  - Privacy-preserving processing
- 📊 Advanced analytics
  - Category trends over time
  - Monthly comparisons
  - Forecasting based on past spending
- 🔄 Improved automation
  - Smarter rules
  - Optional confirmations for imported expenses
  - Confidence scores for LLM-parsed transactions
## License
This project is licensed under the MIT License.
You are free to:
- Use
- Modify
- Distribute
- Self-host

See the LICENSE file for full details.
