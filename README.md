 NL to SQL Data Assistant

Query your database in plain English. Two ways to run it:

- **Web app** (`app.py`) — self-contained Flask app, local LLM via `llama-cpp-python` (no Ollama, no API keys), ships in Docker with a bundled Qwen2.5-0.5B model. Works against a demo SQLite database out of the box.
- **Desktop GUI** (`local-desktop-gui/`) — Tkinter app that talks to SQL Server through Ollama (`llama3.2`), with conversation history and auto-retry on failed SQL.

---

 Web App (Docker)

### 1. Configure `.env`

```
DB_URL=sqlite:////app/database/dev.db
FLASK_SECRET_KEY=<random-string>
```

`DB_URL` can point at any SQLAlchemy-supported database (SQLite, MSSQL via `pymssql`, etc). The default SQLite path is seeded with sample `Customers`/`Orders` tables by `init_db.py` on first run.

### 2. Run

```bash
docker compose up --build
```

First build compiles `llama-cpp-python` and downloads the ~350MB Qwen GGUF model — slow the first time. App serves on **port 7860**.

### 3. Use it

- `/` — ask questions, see generated SQL, results table, and a plain-English explanation, plus token-usage metrics per query.
- `/stream-logs` — live server-sent-events log tail.
- `/health` — health check, reports the connected `DATABASE_URL`.

  <img width="1460" height="855" alt="image" src="https://github.com/user-attachments/assets/1d4619a5-82a9-4c7e-a655-589fc15cfb22" />
  <img width="1515" height="687" alt="image" src="https://github.com/user-attachments/assets/16948c31-a00e-42cd-92f0-f7bac5407198" />



---

 Desktop GUI (Ollama)

### 1. Install dependencies

```bash
cd local-desktop-gui
pip install sqlalchemy pymssql ollama python-dotenv
ollama pull llama3.2
```

### 2. Configure `.env`

```
DB_URL=mssql+pymssql://your_user:your_password@your_host:your_port/your_database
```

### 3. Run

```bash
python gui.py     # Tkinter GUI with chat history
python main.py     # CLI loop instead, if preferred
```

Requires [Ollama](https://ollama.com) running (`ollama serve`) and a SQL Server login with `db_datareader` access (see below).

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

 How It Works

1. **Schema Extractor** (`schemaconnector.py`) — connects to the DB, discovers tables/columns/types/row counts, formats it into prompt context.
2. **NL to SQL Engine** (`nl_to_sql.py`) — sends the question + schema context to the LLM, gets SQL back, auto-fixes common syntax issues (LIMIT→TOP, stray aliases, GROUP BY gaps, nested aggregates). The desktop GUI additionally retries once with the failed SQL + DB error fed back to the model if execution fails.
3. **Result Explainer** — passes query results back to the LLM for a 2-3 sentence plain-English summary.

---

 Project Structure

```
data-assistant/
├── app.py                       # Flask web app (llama-cpp, self-contained)
├── nl_to_sql.py                 # NL → SQL for the web app (llama-cpp backend)
├── schemaconnector.py           # schema extraction (web app)
├── init_db.py                   # seeds demo SQLite database
├── templates/index.html         # web UI
├── static/style.css             # web UI styles
├── Dockerfile / docker-compose.yml
├── requirements.txt
├── local-desktop-gui/
│   ├── gui.py                   # Tkinter desktop app (Ollama backend)
│   ├── main.py                  # CLI entry point (Ollama backend)
│   ├── nl_to_sql.py             # NL → SQL for the desktop app (Ollama backend)
│   └── schemaconnector.py       # schema extraction (desktop app)
├── .env                         # your credentials (not committed to Git)
└── .gitignore
```

---

 Notes

- This tool generates and runs SQL automatically. Always review generated SQL before pointing it at a production database; use a read-only login.
- If connecting from WSL to SQL Server on Windows, enable TCP/IP in SQL Server Configuration Manager and open port 1433 (or your dynamic port) in Windows Firewall.
- Web app's Docker image runs the LLM in-process via `llama-cpp-python` — no separate Ollama server needed for that path.

---

 What's Next

- [ ] Support for PostgreSQL, DuckDB, and CSV files
- [ ] Query history logging

---

## License

MIT
