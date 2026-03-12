# Blanks ERP — Inventory Management System

A complete, scalable ERP system for a blanks clothing store. Built with Python Flask, designed to manage 10,000+ product variants, record sales, track profits, monitor expenses, and analyze fast-moving products.

---

## Features

- **Dashboard** — KPIs: inventory worth, potential profit, today's revenue, low-stock alerts
- **Product Catalog** — manage product types, brands, colors, and sizes
- **Variants** — create single or bulk SKUs by combining attributes
- **Inventory** — table view + interactive grid view with inline editing
- **Sales** — multi-item sale recording with automatic stock deduction
- **Reports** — daily, monthly, product profit, fast movers, restock recommendations
- **Expenses** — track operating costs, included in monthly net profit report
- **Authentication** — secure admin login with hashed passwords

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python Flask |
| ORM | SQLAlchemy |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Frontend | HTML + Bootstrap 5 + Vanilla JS |
| Auth | Flask-Login + Werkzeug |
| Server | Gunicorn |

---

## Local Development

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/blanks-erp.git
cd blanks-erp
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
python app.py
```

Visit `http://localhost:5000`

**Default login:** `admin` / `admin123`

---

## Deployment on Render (Free Tier)

### Step 1 — Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/blanks-erp.git
git push -u origin main
```

### Step 2 — Create Render Web Service

1. Go to [render.com](https://render.com) and sign up
2. Click **New → Web Service**
3. Connect your GitHub repository
4. Configure:

| Setting | Value |
|---|---|
| **Environment** | Python |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app` |
| **Plan** | Free |

### Step 3 — Set Environment Variables

In Render dashboard → **Environment**:

| Key | Value |
|---|---|
| `FLASK_ENV` | `production` |
| `SECRET_KEY` | (generate a random 32-char string) |
| `DATABASE_URL` | (auto-set if you add a Render PostgreSQL) |

### Step 4 — Add PostgreSQL (optional, recommended)

1. In Render: **New → PostgreSQL**
2. Create a free database
3. Copy the **Internal Database URL**
4. Set it as `DATABASE_URL` in your web service's environment variables

### Step 5 — Deploy

Click **Deploy**. Render will build and start your ERP. You'll receive a public URL like `https://blanks-erp.onrender.com`.

---

## Project Structure

```
blanks_erp/
├── app.py              # Application factory & entry point
├── config.py           # Dev/Prod configuration
├── models.py           # SQLAlchemy database models
├── routes/
│   ├── auth.py         # Login / logout
│   ├── dashboard.py    # KPI dashboard
│   ├── products.py     # Products, brands, colors, sizes, variants
│   ├── inventory.py    # Stock management + grid view
│   ├── sales.py        # Sales recording
│   ├── reports.py      # All reports & analytics
│   └── expenses.py     # Expense tracking
├── templates/          # Jinja2 HTML templates
├── static/
│   ├── css/main.css    # Custom stylesheet
│   └── js/main.js      # Grid AJAX & sale form JS
├── requirements.txt
├── Procfile
└── README.md
```

---

## Default Credentials

| Username | Password |
|---|---|
| admin | admin123 |

**Change the password after first login** by modifying the seed in `app.py`.

---

## Performance Notes

- All variant lookups use database indexes on `variant_id`, `sku`, `brand_id`, `color_id`, `size_id`
- Inventory KPIs use aggregate SQL queries (no Python loops)
- Pagination on all large tables (50 rows per page)
- Grid view loads only filtered variants (by product + brand)
- SQLAlchemy `lazy='dynamic'` on large relationships prevents N+1 queries
