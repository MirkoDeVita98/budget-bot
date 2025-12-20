# 💸 Telegram Budget Bot

A personal Telegram bot to track expenses and budgets with:

- 📊 Monthly overall budget
- 🗂️ Categories (Food, Transport, Subscriptions, etc.)
- ⏱️ Daily / Monthly / Yearly budget rules
- 💱 Multi-currency expenses (auto-converted to CHF)
- 🔁 Undo, monthly reset, full reset
- 🧱 SQLite storage (local, simple, fast)

All amounts are **computed and reported in CHF**, even when entered in foreign currencies.

---

## Features

### Budgets
- Set an overall monthly budget
- See remaining budget at any time
- View past months

### Budget rules
- **Daily** budgets (e.g. Food 15 CHF/day)
- **Monthly** budgets (e.g. Subscriptions)
- **Yearly** budgets split across 12 months
- Rules can be named (e.g. individual subscriptions)

### Expenses
- Add expenses anytime
- Optional currency (EUR, USD, etc.)
- Automatic FX conversion to CHF
- Undo last expense
- Reset current month

### FX Conversion
- Uses ECB reference rates via **Frankfurter API**
- Rates cached daily
- Original amount + CHF stored

---

## Project structure

```text
budget-bot/
├── .env                  # secrets (NOT committed)
├── .env.example          # example env file
├── .gitignore
├── requirements.txt
├── main.py               # entry point
├── budget.db             # SQLite DB (runtime)
└── src/
    ├── __init__.py
    ├── config.py         # env + constants
    ├── db.py             # schema & migrations
    ├── fx.py             # FX API + caching
    ├── services.py       # business logic
    └── handlers.py       # Telegram commands
