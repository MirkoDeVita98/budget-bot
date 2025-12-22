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

## ⚡ Quick Start

1. **Get your bot token** from [@BotFather](https://t.me/botfather) on Telegram
2. **Clone and setup**:
   ```bash
   git clone https://github.com/MirkoDeVita98/budget-bot.git
   cd budget-bot
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Configure** your `.env`:
   ```bash
   cp .env.example .env
   # Edit .env and paste your BOT_TOKEN
   ```
4. **Run the bot**:
   ```bash
   python main.py
   ```
5. **Start using** it: Open Telegram, find your bot, and send `/start`

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
├── .env                  # secrets (NOT committed to git)
├── .env.example          # environment variable template
├── .gitignore            # git ignore rules
├── LICENSE               # MIT License
├── README.md             # this file
├── requirements.txt      # Python dependencies
├── main.py               # application entry point
├── budget.db             # SQLite database (created at runtime)
├── assets/
│   └── expense_bot_icon.png  # bot icon
└── src/
    ├── __init__.py
    ├── config.py         # configuration & environment variables
    ├── db.py             # database schema & migrations
    ├── fx.py             # FX API integration & currency conversion
    ├── services.py       # business logic (budgets, rules, expenses)
    ├── alerts.py         # alert system for budget notifications
    ├── textparse.py      # text parsing utilities
    ├── export_csv.py     # CSV export functionality
    └── handlers/         # Telegram command handlers
        ├── __init__.py
        ├── base.py       # base handler class & utilities
        ├── setup.py      # /start and /help commands
        ├── budget.py     # /setbudget, /status, /month commands
        ├── rules.py      # budget rules management (/setdaily, /setmonthly, etc.)
        ├── expenses.py   # expense management (/add, /undo, /expenses, etc.)
        ├── export.py     # /export and /backupdb commands
        ├── reset.py      # /resetmonth and /resetall commands
        └── messages/     # YAML message templates
            ├── base.yaml
            ├── setup.yaml
            ├── budget.yaml
            ├── rules.yaml
            ├── expenses.yaml
            ├── export.yaml
            └── reset.yaml
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
`.env` (local only, NOT committed to git)
```bash
BOT_TOKEN=PASTE_YOUR_TELEGRAM_BOT_TOKEN_HERE
BASE_CURRENCY=CHF
DB_PATH=budget.db
```

### Customization
- **BASE_CURRENCY**: The currency all amounts are converted to (default: CHF). Examples: USD, EUR, GBP, etc.
- **DB_PATH**: Where to store the SQLite database file (default: budget.db in the current directory)

## Running the Bot

```bash
cd src
python main.py
```

The bot will start polling for messages. Once running:
1. Open Telegram
2. Search for your bot by its username
3. Send `/start` to initialize and see all available commands
4. (Optional) Send `/help` to see the help message

**Note:** The bot will continue running until you stop it (Ctrl+C). For persistent hosting, consider using a service like Heroku, AWS, or a VPS.

## Usage Guide

### Command Shortcuts
Most commands have shorthand aliases to make them easier to use:

| Command | Shorthand | Description |
|---------|-----------|-------------|
| `/help` | `/h` | Show help message |
| `/setbudget` | `/sb` | Set monthly budget |
| `/setdaily` | `/sd` | Add a daily budget rule |
| `/setmonthly` | `/sm` | Add a monthly budget rule |
| `/setyearly` | `/sy` | Add a yearly budget rule |
| `/rules` | `/r` | View all budget rules |
| `/delrule` | `/dr` | Delete a budget rule |
| `/add` | `/a` | Add an expense |
| `/undo` | `/u` | Undo last expense |
| `/expenses` | `/e` | List expenses |
| `/delexpense` | `/d` | Delete an expense |
| `/status` | `/s` | Show budget status |
| `/categories` | `/c` | List all categories |
| `/month` | `/m` | Show expenses for a specific month |
| `/resetmonth` | `/rm` | Reset current month expenses |

### Set Monthly Budget

Set your overall monthly spending limit:
```bash
/setbudget 3000
```

This is your maximum allowed spending for the month. Use `/status` to see:
- How much you've spent so far
- How much budget remains
- Breakdown by category

**Tip:** You can set different budgets for different months, and the bot remembers your historical budgets.

### Define Budget Rules
Budget rules define your planned spending for each category. The bot will alert you when you exceed a rule.

- **Daily rule** (automatically scaled to the month)
```bash
/setdaily Food 15
```
This means you plan to spend 15 CHF on Food per day. The bot automatically scales this to the number of days in the month.

- **Monthly rule**
```bash
/setmonthly Rent 700
```

- **Yearly rule** (automatically divided by 12)
```bash
/setyearly CarInsurance 600 Transport
```

- **Named rule** (useful for subscriptions)
```bash
/setmonthly PSN 16.99 EUR Subscription
```
You can specify currency for any rule; it will be converted to BASE_CURRENCY.

- **View all rules**
```bash
/rules
```

- **Delete a rule by ID**
```bash
/delrule <id>
```
### Add Expenses

Add a new expense (amount is required, currency defaults to BASE_CURRENCY):

- **In your base currency**
```bash
/add Food Groceries 62.40
```

- **In a foreign currency** (automatically converted)
```bash
/add Travel Taxi 20 EUR
```

- **Multi-word names or categories** (use quotes)
```bash
/add "Food & Drinks" "Migros groceries" 62.40
/add "Entertainment & Gaming" "PS Store subscription" 16.99 EUR
```

**Pro tip:** Use `/a` as shorthand (e.g., `/a Food Coffee 5`)

### List and Delete Expenses

View your expenses with flexible filtering options:

- **Current month expenses** (default: last 50 items)
```bash
/expenses
```

- **Expenses from a specific month**
```bash
/expenses 2025-12
```

- **Customize the number shown** (prevents very long messages)
```bash
/expenses 2025-12 100
```

- **Filter by category**
```bash
/expenses "Food & Drinks"
```

- **Combine month, category, and limit**
```bash
/expenses 2025-12 "Food & Drinks" 100
```

Each expense is shown with a unique ID, making it easy to identify and delete specific items.

- **Delete a specific expense by ID**
```bash
/delexpense 123
```

Use `/expenses` to see the IDs, then use `/delexpense <id>` to remove unwanted items.
### Reports

Check your spending and budget status:

- **Current month overview**
```bash
/status
```

- **Specific category status**
```bash
/status Food
```
Shows planned budget, actual spending, and remaining amount for that category.

- **Past month summary**
```bash
/month 2025-02
```

- **All categories you've used**
```bash
/categories
```
### Undo & Reset

Manage your expenses with these safety features:

- **Undo the last expense**
```bash
/undo
```
Only undoes the most recent expense in the current month.

- **Reset current month's expenses**
```bash
/resetmonth YYYY-MM
```
Deletes all expenses for the current month, but keeps your rules and budget.

- **Complete reset** (⚠️ use with caution)
```bash
/resetall yes
```
Permanently deletes **all data**: expenses, rules, and budgets. This cannot be undone!

## Data Storage & Security

### Local Storage
- Uses a local SQLite database (`budget.db`) to store all your data
- The database schema is created automatically on first run
- **No data is sent to any cloud service** - everything stays on your machine
- You can back up your database using `/backupdb` command

### Security Best Practices
- ⚠️ **Never commit** your `.env` file to git (it contains your bot token)
- ⚠️ **Never share** your Telegram bot token publicly
- If your token is exposed, immediately revoke it:
  ```text
  Telegram → @BotFather → /mybots → (select your bot) → Revoke current token
  ```
- Store your `.env` file in a safe location with restricted file permissions
- When hosting on a server, use environment variable management tools instead of .env files
## Notifications & Alerts

The bot automatically monitors your spending and sends alerts when certain thresholds are exceeded. Alerts are triggered immediately after you add an expense.

### Alert Types

- **⚠️ Category exceeded**: You've spent more than planned for a category
```text
⚠️ Category exceeded: Food
Planned: 450.00 CHF
Spent: 520.00 CHF
Over: 70.00 CHF
```

- **🚨 Overall budget exceeded**: Your total spending exceeded the monthly budget
```text
🚨 Overall budget exceeded!
Remaining overall is now: -25.40 CHF
```

- **🔔 Budget running low**: You're approaching your limit (default: < 10% remaining)
- **ℹ️ New unplanned category**: You added an expense to a category without a budget rule
```text
ℹ️ New unplanned category detected: Gaming (no rule set). 
It will count as unplanned spend until you add a rule.
```

### How to Use Alerts
1. Set up budget rules with `/setdaily`, `/setmonthly`, `/setyearly`
2. Set an overall monthly budget with `/setbudget`
3. Add expenses as usual - the bot will automatically notify you if you exceed any limits
4. Use alerts to stay aware of your spending patterns
## Export & Backup

### Export to CSV

Export your data in CSV format (useful for spreadsheets, analysis, or backups):

- **Current month expenses** (default)
```bash
/export
```

- **Expenses for a specific month**
```bash
/export expenses 2025-12
```

- **All your budget rules**
```bash
/export rules
```

- **Monthly budgets history**
```bash
/export budgets
```

The bot sends you a downloadable `.csv` file that you can open in Excel, Google Sheets, or any spreadsheet application.

### Backup the SQLite Database

Export the complete raw database file:
```bash
/backupdb
```

This sends the entire `budget.db` file containing all your data. You can:
- Download and save it as a complete backup
- Copy it to another machine and replace the `budget.db` file to restore your data
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

## Troubleshooting

### Bot doesn't respond to commands
- **Check:** Is the bot running? (`python main.py` in the src directory)
- **Check:** Did you set `BOT_TOKEN` in `.env`?
- **Check:** Are you messaging the correct bot? Use `/start` to initialize it

### "No module named 'telegram'" error
```bash
pip install -r requirements.txt
```

### Currency conversion fails
- The bot uses the **Frankfurter API** which requires an internet connection
- Some currencies may not be supported (common ones like EUR, USD, GBP are supported)
- Check the [Frankfurter API documentation](https://www.frankfurter.app/) for supported currencies

### Database errors
- If you see database errors, delete `budget.db` and restart the bot (it will recreate the schema)
- **Warning:** This will delete all your stored data!

### Virtual environment issues
- Ensure you're using Python 3.10+:
  ```bash
  python3 --version
  ```
- Reactivate the virtual environment:
  ```bash
  source .venv/bin/activate
  ```

## License
This project is licensed under the MIT License.
You are free to:
- Use
- Modify
- Distribute
- Self-host

See the LICENSE file for full details.
