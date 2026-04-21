# Test Stand Web Interface

Hydraulic pump test stand monitoring and data export system. Built with FastAPI (backend) and React + TypeScript (frontend), connected to a Raspberry Pi via WebSocket for live CAN bus data.

---

## Architecture Overview

```
[Raspberry Pi]               [Backend — FastAPI]            [Frontend — React/TS]
  pi/can_publisher.py  →    backend/main.py (port 8000)  →  localhost:5173
  pi/can_decoder.py         ├─ /ws/pi       ← Pi data
  pi/sim_mode.py            ├─ /ws/frontend → browser
  (mock mode in dev)        ├─ REST API
                            └─ SQLite (dev) / PostgreSQL (prod)
```

In local development, **MOCK_MODE** replaces the Raspberry Pi with a software simulator — no hardware required.

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | bundled with Node |
| pip | latest | `pip --version` |

---

## Local Setup

### 1. Clone the repo

```bash
git clone <repo-url>
cd TestStandWebInterface
```

### 2. Configure environment variables

Copy the example env file to `.env` in the project root:

```bash
cp frontend/teststandfrontend/.env.example .env
```

The defaults work for local development as-is:

```env
DATABASE_URL=sqlite:///./dev.db
MOCK_MODE=true
SIM_INTERVAL=0.5
FLASK_PORT=8000
EXPORT_DIR=./exports
```

> **MOCK_MODE=true** activates the built-in simulator. The backend generates synthetic pump data so you can develop and test without a Raspberry Pi or CAN bus connection.

### 3. Install backend dependencies

Run this from the **project root** (not inside `backend/`):

```bash
pip install -r backend/requirements.txt
```

### 4. Install frontend dependencies

```bash
cd frontend/teststandfrontend
npm install
cd ../..
```

---

## Running Locally

You need **two terminals** running simultaneously.

### Terminal 1 — Backend

Run from the **project root**:

```powershell
# PowerShell
$env:MOCK_MODE="true"; python -m uvicorn backend.main:app --reload --port 8000
```

```bash
# bash / Git Bash
MOCK_MODE=true python -m uvicorn backend.main:app --reload --port 8000
```

The backend starts at **http://localhost:8000**.  
On first run it creates `dev.db` (SQLite) and seeds default settings automatically.

### Terminal 2 — Frontend

```bash
cd frontend/teststandfrontend
npm run dev
```

The frontend starts at **http://localhost:5173**.

Vite proxies all API calls and WebSocket connections to port 8000, so no extra configuration is needed. Open your browser to **http://localhost:5173** and the app will be live.

---

## Verifying It Works

1. Open **http://localhost:5173** — you should see the test stand dashboard.
2. Live signal values (S1, TP, F1, pressures, etc.) should be updating if `MOCK_MODE=true`.
3. The **Pi Connected** indicator in the UI turns green when the simulator is running.
4. Navigate to the **Settings** tab and confirm the Input Factor and other defaults loaded correctly.

---

## Running an Export

1. Let the simulator run for a few seconds so data gets logged (trending must be active).
2. Click **Export Data** in the UI.
3. An `.xlsx` file is saved to the `exports/` folder in the project root and downloaded by the browser.

To test with the debug logger (logs every 0.5 s regardless of trending):

```powershell
# PowerShell — enable debug mode via the UI toggle, or call the API directly:
Invoke-RestMethod -Method Post -Uri http://localhost:8000/set_debug_mode `
  -ContentType "application/json" -Body '{"enabled": true}'
```

---

## Project Structure

```
TestStandWebInterface/
├── backend/
│   ├── main.py               # FastAPI app, WebSocket endpoints, startup
│   ├── exportXLSX.py         # Excel export logic
│   ├── assets/               # Drop logo.png here for branded exports
│   ├── db/
│   │   ├── database.py       # SQLAlchemy engine, init_db(), migrations
│   │   └── models.py         # TestLog, AppSettings, ExportedFile models
│   ├── routes/
│   │   └── export.py         # /export_data and debug-mode endpoints
│   └── services/
│       ├── data_store.py     # In-memory signal store, WS broadcast
│       └── csv_logger.py     # Background task: logs to DB every 5 s
├── frontend/teststandfrontend/
│   ├── src/                  # React + TypeScript source
│   └── vite.config.ts        # Dev proxy config (API + WS → port 8000)
├── pi/
│   ├── can_publisher.py      # Runs on Pi: reads can0, sends to backend
│   ├── can_decoder.py        # All 17 CAN message decoders
│   └── sim_mode.py           # Dev simulator (replays CSV or synthetic data)
├── exports/                  # Generated .xlsx files land here
├── .env                      # Local environment variables (not committed)
└── requirements.txt          # Python dependencies (root alias)
```

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./dev.db` | SQLite for dev, PostgreSQL URL for prod |
| `MOCK_MODE` | `true` | `true` = run simulator; `false` = wait for real Pi |
| `SIM_INTERVAL` | `0.5` | Simulator tick rate in seconds |
| `EXPORT_DIR` | `./exports` | Directory where `.xlsx` files are saved |
| `ALLOWED_ORIGINS` | _(unset)_ | CORS whitelist, e.g. `http://localhost:5173` |
| `AZURE_TENANT_ID` | _(unset)_ | SharePoint upload — leave blank to disable |
| `AZURE_CLIENT_ID` | _(unset)_ | SharePoint upload — leave blank to disable |
| `AZURE_CLIENT_SECRET` | _(unset)_ | SharePoint upload — leave blank to disable |

---

## Common Issues

**`ModuleNotFoundError: No module named 'backend'`**  
Run uvicorn from the **project root**, not from inside the `backend/` folder:
```bash
# Correct
python -m uvicorn backend.main:app --reload --port 8000

# Wrong — do not do this
cd backend && uvicorn main:app ...
```

**Port 8000 already in use**  
Kill the existing process or change the port:
```powershell
# Find and kill (PowerShell)
Get-Process -Name python | Stop-Process
```

**`dev.db` schema out of date after pulling changes**  
Delete `dev.db` and restart the backend — `init_db()` recreates it and runs any pending column migrations automatically:
```bash
rm dev.db
```

**Frontend shows "disconnected" / no live data**  
Make sure the backend is running on port 8000 before starting the frontend. The WebSocket proxy in Vite only works when the backend is already up.

---

## Production Deployment

| Service | Purpose | Key env vars |
|---------|---------|-------------|
| Railway | FastAPI backend | `DATABASE_URL`, `MOCK_MODE=false`, `ALLOWED_ORIGINS`, `EXPORT_DIR` |
| Supabase | PostgreSQL database | Provides `DATABASE_URL` |
| Vercel | React frontend | `VITE_WS_URL=wss://...railway.app/ws/frontend` |
| Raspberry Pi | CAN bus publisher | `BACKEND_WS_URL=wss://...railway.app/ws/pi` |

See `pi/teststand-publisher.service` for the systemd unit that auto-starts the Pi publisher on boot.
