# NL to SQL Data Assistant

Query your database in plain English — no SQL required. Ask a question, see the generated SQL, the results, and a plain-English explanation.

The project ships two independent ways to run it:

| | Web App (`app.py`) | Desktop GUI (`local-desktop-gui/`) |
|---|---|---|
| **Interface** | Flask web app | Tkinter desktop app |
| **LLM backend** | Local, via `llama-cpp-python` (no Ollama, no API keys) | Ollama (`llama3.2`) |
| **Database** | Any SQLAlchemy-supported DB (ships with demo SQLite) | SQL Server (via `pymssql`) |
| **Setup** | Docker, one command | Local Python install |
| **Extras** | Token-usage metrics, live log stream | Conversation history, auto-retry on failed SQL |

---

## Quick Start — Web App (Docker)

**1. Configure `.env`**
```
DB_URL=sqlite:////app/database/dev.db
FLASK_SECRET_KEY=<random-string>
```
`DB_URL` accepts any SQLAlchemy-supported database (SQLite, MSSQL via `pymssql`, etc.). The default SQLite path is seeded automatically with sample `Customers`/`Orders` tables on first run.

**2. Run**
```
docker compose up --build
```
The first build compiles `llama-cpp-python` and downloads the ~350MB Qwen2.5-0.5B GGUF model — this is slow the first time only. The app serves on **port 7860**.

**3. Use it**

| Route | Description |
|---|---|
| `/` | Ask questions; see generated SQL, results table, plain-English explanation, and per-query token-usage metrics |
| `/stream-logs` | Live server-sent-events log tail |
| `/health` | Health check; reports the connected `DATABASE_URL` |

### Running without Docker (e.g. WSL)

The web app doesn't require Docker.

1. Install system build dependencies: `gcc g++ make cmake wget sqlite3`
2. Install Python dependencies:
   ```
   pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
   pip install -r requirements.txt
   ```
3. Download the model:
   ```
   wget -O models/qwen.gguf https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf
   ```
4. Update `model_path` in `nl_to_sql.py` to `models/qwen.gguf` (it's hardcoded to `/app/models/qwen.gguf` for the container).
5. Point `DB_URL` in `.env` at a local path, e.g. `sqlite:///./database/dev.db`.
6. Seed the database: `python init_db.py`
7. Start the app:
   ```
   python app.py
   # or, for production:
   gunicorn -w 1 -k sync --timeout 300 -b 0.0.0.0:7860 app:app
   ```

---

## Quick Start — Desktop GUI (Ollama)

**1. Install dependencies**
```
cd local-desktop-gui
pip install sqlalchemy pymssql ollama python-dotenv
ollama pull llama3.2
```

**2. Configure `.env`**
```
DB_URL=mssql+pymssql://your_user:your_password@your_host:your_port/your_database
```

**3. Run**
```
python gui.py     # Tkinter GUI with chat history
python main.py     # CLI loop instead, if preferred
```

Requires Ollama running (`ollama serve`) and a SQL Server login with `db_datareader` access (see below).

### SQL Server read-only login
```sql
CREATE LOGIN datauser WITH PASSWORD = 'your_password',
    CHECK_POLICY = OFF,
    CHECK_EXPIRATION = OFF;

USE your_database;
CREATE USER datauser FOR LOGIN datauser;
ALTER ROLE db_datareader ADD MEMBER datauser;
```

---

## How It Works

1. **Schema Extractor** (`schemaconnector.py`) — connects to the database, discovers tables, columns, types, and row counts, and formats it into prompt context.
2. **NL-to-SQL Engine** (`nl_to_sql.py`) — sends the question plus schema context to the LLM and gets SQL back. Auto-fixes common syntax issues (`LIMIT` → `TOP`, stray aliases, `GROUP BY` gaps, nested aggregates). The desktop GUI additionally retries once, feeding the failed SQL and the database error back to the model.
3. **Result Explainer** — passes query results back to the LLM for a 2–3 sentence plain-English summary.

---

## Project Structure

```
data-assistant/
├── app.py                       # Flask web app (llama-cpp backend)
├── nl_to_sql.py                 # NL → SQL for the web app
├── schemaconnector.py           # Schema extraction (web app)
├── init_db.py                   # Seeds the demo SQLite database
├── templates/index.html         # Web UI
├── static/style.css             # Web UI styles
├── Dockerfile / docker-compose.yml
├── requirements.txt
├── local-desktop-gui/
│   ├── gui.py                   # Tkinter desktop app (Ollama backend)
│   ├── main.py                  # CLI entry point (Ollama backend)
│   ├── nl_to_sql.py             # NL → SQL for the desktop app
│   └── schemaconnector.py       # Schema extraction (desktop app)
├── .env                         # Your credentials (not committed to Git)
└── .gitignore
```

---

## Notes & Safety

- This tool generates and executes SQL automatically. **Always review generated SQL before pointing it at a production database, and use a read-only login.**
- Connecting from WSL to SQL Server on Windows: enable TCP/IP in SQL Server Configuration Manager and open port 1433 (or your dynamic port) in Windows Firewall.
- The web app's Docker image runs the LLM in-process via `llama-cpp-python` — no separate Ollama server needed for that path.

---

## Roadmap

- [ ] Support for PostgreSQL, DuckDB, and CSV files — broaden format support and fine-tune the model on the resulting syntax differences
- [ ] Query history logging — build a question bank from past queries to improve accuracy on more complex questions
