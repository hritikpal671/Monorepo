# FP&A Studio — Synthetic Data Generator

A full-stack application that generates correlated, industry-specific synthetic FP&A datasets with a complete P&L model. Built with **FastAPI** (Python) for the backend and **React + Vite** for the frontend, backed by **PostgreSQL** or **SQLite**.

---

## Table of Contents

- [What This App Does](#what-this-app-does)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup — macOS](#setup--macos)
- [Setup — Windows](#setup--windows)
- [Setup — Linux (Ubuntu / Debian)](#setup--linux-ubuntu--debian)
- [Environment Variables](#environment-variables)
- [Database Options](#database-options)
- [Running the App](#running-the-app)
- [Loading Demo Data](#loading-demo-data)
- [Generated Output Files](#generated-output-files)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)

---

## What This App Does

FP&A Studio lets you:

1. **Create industry workspaces** — CPG, SaaS, Retail (and custom industries via Templates)
2. **Configure datasets** — choose dimensions (product, region, channel), scenarios (Base, Optimistic, Pessimistic), seasonality profiles, FX volatility, inflation presets, and marketing intensity
3. **Generate synthetic financial data** — each run produces a full correlated P&L model: `fact_sales.csv`, `pnl_consolidated.csv`, and dimension tables
4. **Explore & download** — interactive analytics dashboard, custom charts, column slicer, and bulk CSV export
5. **Stress-test scenarios** — compare Base vs Pessimistic vs Holiday Upside side-by-side

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite 8, Recharts, Lucide Icons, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy, Pydantic, NumPy, Pandas |
| Database | SQLite (default, zero-config) or PostgreSQL |
| Python | 3.9+ |
| Node.js | 18+ |

---

## Project Structure

```
Divyansh Panwar/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI routes and app entry point
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── database.py          # DB engine and session setup
│   │   ├── fpna_generator.py    # Core data generation logic
│   │   └── config/
│   │       └── templates/       # Industry JSON templates (cpg, saas, retail)
│   ├── seed_demo_data.py        # CLI script to populate demo projects
│   ├── requirements.txt
│   └── .env                     # Your environment variables (not committed)
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── config.js            # API base URL config
│   │   ├── hooks/api.js         # All API calls centralised here
│   │   ├── components/
│   │   │   └── Layout.jsx
│   │   └── pages/
│   │       ├── DashboardPage.jsx
│   │       ├── ProjectsPage.jsx
│   │       ├── ProjectDetailPage.jsx
│   │       ├── NewProjectPage.jsx
│   │       ├── NewDatasetPage.jsx
│   │       ├── DatasetDashboard.jsx
│   │       ├── AnalyticsPage.jsx
│   │       └── TemplatesPage.jsx
│   ├── package.json
│   └── vite.config.js
└── README.md
```

---

## Prerequisites

You need the following installed before starting:

| Tool | Minimum Version | Check command |
|---|---|---|
| Python | 3.9 | `python --version` or `python3 --version` |
| pip | Latest | `pip --version` |
| Node.js | 18.0 | `node --version` |
| npm | 9.0 | `npm --version` |
| Git | Any | `git --version` |

PostgreSQL is **optional** — the app works out of the box with SQLite.

---

## Setup — macOS

### 1. Install system dependencies

If you don't have Homebrew, install it first:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then install Python and Node:
```bash
brew install python@3.11 node
```

Verify:
```bash
python3 --version   # Should print 3.9 or higher
node --version      # Should print 18 or higher
```

### 2. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

### 3. Set up the backend

```bash
cd backend

# Create a virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
# Create your .env file inside backend/
touch .env
```

Open `backend/.env` and add:
```env
# Leave these two lines out to use SQLite (recommended for local dev)
# POSTGRES=postgresql://user:password@localhost:5432/fpna_db
# USE_POSTGRES=true
```

### 5. Set up the frontend

Open a **new terminal tab**, then:
```bash
cd frontend
npm install
```

---

## Setup — Windows

### 1. Install system dependencies

**Python:** Download from [python.org](https://www.python.org/downloads/). During installation, check **"Add Python to PATH"**.

**Node.js:** Download from [nodejs.org](https://nodejs.org/) (LTS version).

Verify in Command Prompt or PowerShell:
```powershell
python --version    # Should print 3.9 or higher
node --version      # Should print 18 or higher
```

### 2. Clone the repository

```powershell
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

### 3. Set up the backend

```powershell
cd backend

# Create a virtual environment
python -m venv .venv

# Activate it (PowerShell)
.venv\Scripts\Activate.ps1

# If you get an execution policy error, run this first:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Activate it (Command Prompt)
.venv\Scripts\activate.bat

# Install Python dependencies
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a file named `.env` inside the `backend/` folder with this content:
```env
# Leave these two lines commented out to use SQLite (zero config)
# POSTGRES=postgresql://user:password@localhost:5432/fpna_db
# USE_POSTGRES=true
```

### 5. Set up the frontend

Open a **new PowerShell / Command Prompt window**, then:
```powershell
cd frontend
npm install
```

---


### 1. Install system dependencies

```bash
# Update package list
sudo apt update

# Install Python 3, pip, and venv
sudo apt install -y python3 python3-pip python3-venv

# Install Node.js 18+ via NodeSource
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Verify
python3 --version
node --version
```

### 2. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

### 3. Set up the backend

```bash
cd backend

# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
touch backend/.env
```

Add to `backend/.env`:
```env
# Leave these commented for SQLite (default)
# POSTGRES=postgresql://user:password@localhost:5432/fpna_db
# USE_POSTGRES=true
```

### 5. Set up the frontend

Open a **new terminal**, then:
```bash
cd frontend
npm install
```

---

## Environment Variables

All variables go in `backend/.env`. None are required for basic local use — the app defaults to SQLite automatically.

| Variable | Required | Description | Example |
|---|---|---|---|
| `USE_POSTGRES` | No | Set to `true` to use PostgreSQL instead of SQLite | `true` |
| `POSTGRES` | Only if `USE_POSTGRES=true` | Full PostgreSQL connection string | `postgresql://postgres:pass@localhost:5432/fpna_db` |
| `DATABASE_URL` | No | Alternative to `POSTGRES` for PostgreSQL URL | Same format as above |

**SQLite** (default, zero setup):
```env
# Leave .env empty or don't create it — SQLite file is auto-created at backend/fpna_studio.db
```

**PostgreSQL** (optional):
```env
USE_POSTGRES=true
POSTGRES=postgresql://postgres:yourpassword@localhost:5432/fpna_studio
```

---

## Database Options

### Option A — SQLite (Default, Recommended for local dev)

No setup needed. The database file `fpna_studio.db` is automatically created inside `backend/` the first time you start the server.

### Option B — PostgreSQL

1. Install PostgreSQL from [postgresql.org](https://www.postgresql.org/download/)
2. Create a database:
   ```sql
   CREATE DATABASE fpna_studio;
   ```
3. Set `USE_POSTGRES=true` and `POSTGRES=postgresql://...` in `backend/.env`
4. Tables are auto-created by SQLAlchemy on first run — no migrations needed

---

## Running the App

You need **two terminals running simultaneously** — one for the backend and one for the frontend.

### Terminal 1 — Start the backend

**macOS / Linux:**
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Windows (PowerShell):**
```powershell
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

Backend is live at → **http://localhost:8000**  
Interactive API docs → **http://localhost:8000/docs**

---

### Terminal 2 — Start the frontend

```bash
cd frontend
npm run dev
```

You should see:
```
  VITE v8.x.x  ready in xxx ms

  ➜  Local:   http://localhost:3000/
```

App is live at → **http://localhost:3000**

---

## Loading Demo Data

Once both servers are running, you have two ways to populate demo data:

### Option A — From the UI (Recommended)

1. Open **http://localhost:3000**
2. Go to the **Dashboard** page
3. Click the **🚀 Load Demo Projects** button
4. Wait ~30 seconds while 3 projects are generated:
   - **NutriCo Foods** (CPG) — multi-region snack & beverage brand, 2 datasets
   - **CloudMetrics** (SaaS) — 3-year enterprise subscription model, 3 scenarios
   - **StyleHouse** (Retail) — omnichannel fashion retailer with holiday seasonality

### Option B — From the command line

```bash
cd backend
source .venv/bin/activate      # Windows: .venv\Scripts\activate
python seed_demo_data.py
```

---

## Generated Output Files

Every dataset generates these CSV files, saved under `backend/data/{project_id}/{dataset_id}/`:

| File | Description |
|---|---|
| `fact_sales.csv` | Full fact table — all financial and driver columns at the lowest grain (product × region × channel × scenario × month) |
| `pnl_consolidated.csv` | Monthly P&L rolled up by scenario, with margin % columns |
| `dim_product.csv` | Product dimension table |
| `dim_region.csv` | Region dimension with FX base rates |
| `dim_time.csv` | Calendar dimension with year / quarter / month labels |

### Columns in `fact_sales.csv`

**Dimension columns:** `date`, `year`, `month`, `product`, `region`, `channel`, `scenario`

**Driver accounts:** `seasonality_index`, `sentiment_index`, `fx_rate`, `inflation_index`, `promo_depth`, `capacity_utilization`, `stockout_flag`

**Financial accounts:** `units`, `price`, `revenue`, `cogs`, `gross_profit`, `marketing_expense`, `other_opex`, `ebitda`, `depreciation`, `ebit`, `interest`, `taxes`, `net_income`

---

## API Reference

All endpoints are prefixed with `/api`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/templates` | List all industry templates |
| `GET` | `/api/templates/{industry}` | Get a single template |
| `POST` | `/api/templates` | Create a custom template |
| `PUT` | `/api/templates/{industry}` | Update a template |
| `DELETE` | `/api/templates/{industry}` | Delete a template |
| `GET` | `/api/projects` | List all projects |
| `POST` | `/api/projects` | Create a project |
| `GET` | `/api/projects/{id}` | Get project details |
| `DELETE` | `/api/projects/{id}` | Delete project and all its data |
| `GET` | `/api/projects/{id}/datasets` | List datasets for a project |
| `POST` | `/api/projects/{id}/datasets` | Generate a new dataset |
| `DELETE` | `/api/projects/{id}/datasets/{dsId}` | Delete a dataset |
| `GET` | `/api/projects/{id}/datasets/{dsId}/dashboard-stats` | Analytics summary stats |
| `POST` | `/api/projects/{id}/datasets/{dsId}/custom-chart` | Custom chart data slice |
| `GET` | `/api/projects/{id}/datasets/{dsId}/download?file=X` | Download a single CSV |
| `GET` | `/api/projects/{id}/datasets/{dsId}/download-all` | Download all CSVs as ZIP |
| `POST` | `/api/seed-demo` | Seed 3 demo projects (safe to call multiple times) |

Full interactive documentation is available at **http://localhost:8000/docs** once the backend is running.

---

## Troubleshooting

**`ModuleNotFoundError` when starting the backend**
Make sure you activated your virtual environment before running `uvicorn`:
```bash
source .venv/bin/activate    # macOS / Linux
.venv\Scripts\activate.bat   # Windows CMD
```

**`npm install` fails with EACCES permission error (macOS/Linux)**
Fix npm permissions instead of using `sudo`:
```bash
mkdir -p ~/.npm-global
npm config set prefix ~/.npm-global
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

**Frontend shows "Failed to fetch" or network errors**
- Confirm the backend is running on port 8000
- Check `frontend/src/config.js` — the `API_BASE` should be `http://localhost:8000/api`
- Open http://localhost:8000/api/health in your browser — you should see `{"status":"ok"}`

**Port 8000 or 3000 already in use**
```bash
# Use a different backend port
uvicorn app.main:app --reload --port 8001

# Then update frontend/src/config.js:
# const API_BASE = "http://localhost:8001/api"
```

**PostgreSQL connection refused**
- Ensure the PostgreSQL service is running: `sudo systemctl start postgresql` (Linux) or check Services on Windows
- Verify your credentials in `.env` match your PostgreSQL user
- Test the connection: `psql -U postgres -d fpna_studio`

**On Windows: `.venv\Scripts\Activate.ps1 cannot be loaded` error**
Run this once in PowerShell as Administrator:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Demo seed takes too long or fails**
Each dataset generates thousands of rows of correlated financial data. For machines with less RAM, reduce the dataset size when seeding: use `num_years=1` and fewer products/regions.
