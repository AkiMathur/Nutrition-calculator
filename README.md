# 🥗 NutriCalc — Nutrition Calculator

A mobile-first nutrition tracking app built with **FastAPI** + **PostgreSQL** + **Gemini AI**.

Log meals, track daily macros, manage favorites, and get AI-powered nutritional estimates — all from a clean mobile-friendly interface.

---

## ✨ Features

- 📊 **Today** — Calorie ring and macro summary for the current day
- 📋 **Log** — Browse meals by date with day totals
- ➕ **Add Meal** — Two-phase flow: enter meal → AI analyses nutrition → log it
- ⭐ **Favorites** — Save, manage, and directly log favorite meals
- 🤖 **Gemini AI** — Estimates calories and macros from a natural language meal description

---

## 🛠 Tech Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI, SQLAlchemy, Alembic |
| Database | PostgreSQL |
| AI | Google Gemini API |
| Frontend | Vanilla HTML/CSS/JS (mobile-first SPA) |

---

## 🚀 Setup

### 1. Clone the repo
```bash
git clone https://github.com/your-username/nutrition-calculator.git
cd nutrition-calculator
```

### 2. Create a virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
cp .env.example .env
```
Edit `.env` with your actual credentials:
```
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/nutri_calc
GEMINI_API_KEY=your_gemini_api_key_here
```
Get a free Gemini API key at: https://aistudio.google.com/apikey

### 5. Set up the database
Create a PostgreSQL database named `nutri_calc`, then run migrations:
```bash
alembic upgrade head
```

### 6. Run the server
```bash
uvicorn main:app --reload
```

Open the app at: **http://localhost:8000/app**

---

## 📁 Project Structure

```
nutrition-calculator/
├── main.py           # FastAPI routes and Gemini integration
├── models.py         # SQLAlchemy DB models
├── database.py       # DB connection
├── gentest.py        # Gemini API test script
├── requirements.txt
├── .env.example      # Environment variable template
├── alembic/          # DB migrations (not included in repo)
└── static/
    └── index.html    # Full frontend SPA
```

---

## 🔑 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/meals/` | Log a meal |
| `GET` | `/meals/{date}/` | Get meals for a date |
| `PUT` | `/meals/{id}/` | Update a meal |
| `DELETE` | `/meals/{id}/` | Delete a meal |
| `GET` | `/meals/summary/{date}/` | Day totals (calories + macros) |
| `POST` | `/meals/analyse/` | AI nutrition estimate |
| `GET` | `/meals/fav` | List favorites |
| `POST` | `/meals/fav/` | Save a meal as favorite |
| `POST` | `/meals/single_fav/` | Add a new favorite directly |
| `DELETE` | `/meals/fav/{id}/` | Remove a favorite |
