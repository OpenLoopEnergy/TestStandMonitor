# Test Stand Web Interface

Hydraulic pump test stand web interface. Rebuilt from Flask/SQLite/Jinja2 into FastAPI + React/TypeScript + Supabase PostgreSQL, cloud-hosted.

## Architecture
```
[Raspberry Pi]              [Railway — Backend]           [Vercel — Frontend]
  pi/can_publisher.py  →   FastAPI (backend/main.py)  →  React + TypeScript
  pi/can_decoder.py        ├─ /ws/pi  (from Pi)           frontend/teststandfrontend/
  pi/sim_mode.py (dev)     ├─ /ws/frontend (to browsers)
                           ├─ REST API
                           └─ SQLAlchemy (SQLite dev / PostgreSQL prod)
```

## Dev Setup (PowerShell)
```powershell
# Terminal 1 — Backend (run from project root, NOT from inside backend/)
pip install -r backend/requirements.txt
$env:MOCK_MODE="true"; python -m uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend/teststandfrontend
npm install
npm run dev
# Opens at http://localhost:5173, proxies API/WS to port 8000
```

## Key Files
| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app, WebSocket endpoints, startup |
| `backend/db/database.py` | SQLAlchemy engine, `init_db()` seeds defaults (inputFactor=11) |
| `backend/services/data_store.py` | In-memory signal store, broadcasts to all frontend WS clients |
| `backend/services/csv_logger.py` | Background task: writes to DB every 5s when trending==1 |
| `backend/exportXLSX.py` | Excel export — preserved from original, do not change structure |
| `pi/can_decoder.py` | All 17 CAN message decoders (preserved from original) |
| `pi/can_publisher.py` | Runs on Pi: reads can0, sends frames to backend WS |
| `pi/sim_mode.py` | Dev sim: replays log_data.csv or generates synthetic data |
| `pi/teststand-publisher.service` | systemd unit for auto-start on Pi boot |
| `Procfile` | Railway deployment command |
| `.env.example` | All environment variables |

## Signal Scaling (frontend)
- `F1 × 0.01` = GPM (raw centi-units in DB, scaled once in routes/export.py for CSV)
- `T1 / 10`, `T3 / 10` = °F
- `TP / 10.23` = %
- `TheoFlow = (S1 × inputFactor) / 231` (cu/in) — default inputFactor=11
- `Efficiency = (F1_scaled / TheoFlow) × 100` — expect ~95-100% at full load

## Deployment
| Service | What | Key env vars |
|---------|------|-------------|
| Railway | FastAPI backend | `DATABASE_URL`, `MOCK_MODE=false`, `ALLOWED_ORIGINS`, `EXPORT_DIR` |
| Supabase | PostgreSQL DB | Provides `DATABASE_URL` |
| Vercel | React frontend | `VITE_WS_URL=wss://...railway.app/ws/frontend` |
| Pi | CAN publisher | `BACKEND_WS_URL=wss://...railway.app/ws/pi` |

## Important Rules
- `sendCommands.py` is not functional — do not implement or reference it
- Do not modify `backend/exportXLSX.py` structure — Excel output format is preserved exactly
- Do not scale F1 in exportXLSX.py — it is already scaled in routes/export.py before the CSV is built
- Run uvicorn from the **project root**, not from inside `backend/`
