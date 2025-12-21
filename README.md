![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)

<p align="center">
  <img src="assets/expense_bot_icon.png" alt="Budget Bot logo" width="120">
</p>

# 💸 Telegram Budget Bot

A personal Telegram bot to track expenses and budgets directly from Telegram.  
Designed to be simple, transparent, and fully under your control.

Key highlights:

- 📊 Monthly overall budget tracking (auto-carried month to month)
- 🗂️ Category-based expenses (Food, Transport, Subscriptions, etc.)
- ⏱️ Daily, Monthly, and Yearly budget rules
- 🧠 Automatic rule snapshots for historical months
- 💱 Multi-currency expenses with automatic conversion to your **BASE_CURRENCY**
- 🧾 List expenses with IDs (filter by month / category / limit)
- 🗑️ Delete specific expenses or rules by ID
- 🔔 Budget & category alerts
- 🔁 Undo last expense, monthly reset, full reset
- 🧱 Local SQLite storage (no cloud, no third parties)

All amounts are **computed and reported in your BASE_CURRENCY**, even when entered in foreign currencies.

---

## Features

### Budgets
- Set an overall monthly budget (`/setbudget`)
- Budget automatically carries forward if not explicitly set
- Remaining budget is computed *after* planned rules and overspending
- Reset a specific month’s budget with `/resetmonth [YYYY-MM]`

### Budget Rules
Budget rules define your *planned* spending and are automatically aggregated per month.

- **Daily rules**  
  Example: `Food 15 CHF/day` → multiplied by days in the month

- **Monthly rules**  
  Example: `Subscriptions 35 CHF/month`

- **Yearly rules**  
  Example: `Car insurance 600 CHF/year` → divided by 12

- **Named rules**  
  Useful for subscriptions (Netflix, PSN, Spotify, etc.)

Rules are stored internally in **BASE_CURRENCY** for consistency.

#### 📌 Historical accuracy
- When a new month starts, the bot **automatically snapshots the previous month’s rules**
- Past months (`/month YYYY-MM`) always show the rules that were active at that time
- No manual snapshot command needed

### Expenses
- Add expenses at any time
- Supports **foreign currencies** (EUR, USD, etc.)
- Automatic FX conversion to **BASE_CURRENCY**
- Stores:
  - Original amount
  - Original currency
  - FX rate & date
  - Converted amount
- Undo the last expense (`/undo`)
- Delete specific expenses by ID (`/delexpense <id>`)

### FX Conversion
- Uses ECB reference rates via the **Frankfurter API**
- Rates are cached daily
- Ensures deterministic historical conversions

### Notifications (Alerts)
The bot automatically notifies you when:

- ⚠️ A **category budget** is exceeded
- 🚨 The **overall monthly budget** is exceeded
- 🔔 Remaining budget drops below a safe threshold
- ℹ️ A **new unplanned category** is detected

Alerts are triggered immediately after adding an expense.

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
├── assets/
│   └── expense_bot_icon.png
└── src/
    ├── __init__.py
    ├── config.py         # configuration & environment variables
    ├── db.py             # database schema & migrations
    ├── fx.py             # FX API integration & caching
    ├── services.py       # business logic (budgets, rules, expenses)
    ├── alerts.py         # alert detection logic
    ├── export_csv.py     # CSV exports
    ├── textparse.py      # robust quoted argument parsing
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
Once the bot is running:
- Open Telegram
- Search for your bot by its username
- Open the chat
- Send the command:
```bash
/start
```
The `/start` command initializes the bot and displays the full list of available commands.
You can also use:
```bash
/help
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
- **BASE_CURRENCY** expense
```bash
/add Food Groceries 62.40
```
- Foreign currency expense
```bash
/add Travel Taxi 20 EUR
```
Tip: Use quotes for multi-word names or categories:
```bash
/add "Food & Drinks" "Migros groceries" 62.40
/setmonthly "PSN Plus Extra" 16.99 EUR "Subscriptions & Gaming"
/status "Food & Drinks"
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
- You can fully reset a month (expenses + budget) with:
```bash
/resetmonth YYYY-MM
```
- Reset everything:
```bash
/resetall yes
```
⚠️ `/resetall yes` permanently deletes all stored data.

## Month Rollovers & Historical Consistency

This bot is designed to keep your **financial history accurate and predictable**, even as your rules and budgets evolve over time.

### How rollovers work

#### 📅 Budgets
- When a **new month starts**, if you haven’t explicitly set a budget yet:
  - The bot **automatically carries forward** the last known budget.
  - This happens only for the **current month**.
- When viewing past months with `/month YYYY-MM`:
  - Budgets are **read-only**
  - No automatic carry or creation happens
  - You only see what was actually set for that month

### Rules (the important part)
Rules are global by default, but to preserve history:
- On the first interaction in a new month, the bot automatically:
  - Creates a snapshot of the previous month’s rules
  - Stores them internally as a frozen historical state
- This happens automatically, without any manual command
- As a result:
  - Past months always reflect the rules that were active at that time
  - Future changes to rules do not affect historical months
This ensures:
- `/status` → always reflects current planning
- `/month YYYY-MM` → always reflects historical planning
No cron jobs, no schedulers — snapshots are created lazily and safely on first use.

## Notifications (Alerts)

The bot can automatically notify you when:

- ⚠️ You exceed a **category planned budget** (e.g. Food goes below 0)
- 🚨 You exceed the **overall monthly budget**
- 🔔 You are running low on remaining budget (default: < 10%)
- ℹ️ A new unplanned category is detected

Alerts are triggered immediately after you add an expense:

```bash
/add Food Groceries 120
```
Example alert (category exceeded):
```text
⚠️ Category exceeded: Food
Planned: 450.00 CHF
Spent: 520.00 CHF
Over: 70.00 CHF
```
Example alert (overall exceeded):
```text
🚨 Overall budget exceeded!
Remaining overall is now: -25.40 CHF
```
Example alert (unplanned category):
```text
ℹ️ New unplanned category detected: Gaming (no rule set). It will count as unplanned spend until you add a rule.
```
## Export / Backup (CSV + SQLite)

### Export to CSV

Export the current month expenses (default):
```bash
/export
```
Export expenses for a specific month:
```bash
/export expenses 2025-12
```
Export your rules:
```bash
/export rules
```
Export your monthly budgets:
```bash
/export budgets
```
The bot will send you a downloadable `.csv` file.
### Backup the SQLite database
This sends the raw `budget.db` file containing all your data:
```bash
/backupdb
```
## Data Storage & Privacy
- Local SQLite database only (budget.db)
- No cloud services
- No third-party data sharing
- You fully own your data
  
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
- 🔄 Smarter rollovers
  - Compare rule snapshots vs current rules
  - Highlight what changed month-over-month:
    - New rules added
    - Rules removed
    - Amount changes
  - Optional command like:
    ```bash
    /rules diff 2025-11 2025-12
    ```
  - Or automatic summary:
    ```text
    “Rules changed since last month: +Subscriptions, −Transport, Food +50 CHF”
    ```
    
## License
This project is licensed under the MIT License.
You are free to:
- Use
- Modify
- Distribute
- Self-host

See the LICENSE file for full details.
