from flask import Flask, render_template, request, session, jsonify, Response
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from init_db import init_database
import time 
import os

from schemaconnector import extract
from nl_to_sql import generate_sql, explain_results

load_dotenv()

init_database()

app = Flask(__name__)

# Flask sessions require a secret key to sign the session cookie.
# Always set a secure fallback or load it from your environment (.env).
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# ------------------------------------------------------------------
# Database setup
# ------------------------------------------------------------------

DATABASE_URL = os.getenv("DB_URL")
engine = create_engine(DATABASE_URL)

with engine.connect() as startup_conn:
    startup_conn.execute(text("SELECT 1;"))

registry = extract(engine)
schema_context = registry.to_prompt_context()

# ------------------------------------------------------------------
# Logs
# ------------------------------------------------------------------
@app.route("/stream-logs")
def stream_logs():
    def generate_log_stream():
        # Change this path if you log to a dedicated text file,
        # otherwise we can simulate a live application heartbeat feed
        log_file_path = "app.log"
        
        # Ensure the log file exists
        if not os.path.exists(log_file_path):
            with open(log_file_path, "w") as f:
                f.write("[SYSTEM] Live Log Monitoring Engine Initialized.\n")

        # Open the file and keep checking for new additions (like tail -f)
        with open(log_file_path, "r") as f:
            # Go to the end of the file first
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.5)  # Pause briefly if no new log line exists
                    continue
                yield f"data: {line}\n\n"

    return Response(generate_log_stream(), mimetype="text/event-stream")


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def index():
    sql = None
    explanation = None
    headers = []
    rows = []
    error = None
    question = ""
    metrics = None # Initialize empty metrics dictionary container

    if "history" not in session:
        session["history"] = []

    if request.method == "POST":
        question = request.form.get("question", "").strip()

        if question:
            try:
                # 1. Generate SQL and unpack metrics payload
                sql_res = generate_sql(question, schema_context, registry.tables, session["history"])
                sql = sql_res["sql"]

                # Execute SQL
                with engine.connect() as conn:
                    result = conn.execute(text(sql))
                    headers = list(result.keys())
                    rows = [list(row) for row in result.fetchall()]

                # 2. Generate summary explanation and unpack metrics payload
                exp_res = explain_results(question, sql, rows)
                explanation = exp_res["explanation"]

                # Aggregate the combined performance totals
                metrics = {
                    "sql_prompt_tokens": sql_res["prompt_tokens"],
                    "sql_gen_tokens": sql_res["completion_tokens"],
                    "exp_prompt_tokens": exp_res["prompt_tokens"],
                    "exp_gen_tokens": exp_res["completion_tokens"],
                    "total_tokens": sql_res["total_tokens"] + exp_res["total_tokens"]
                }

                # Manage session history updates
                local_history = session["history"]
                local_history.append({"role": "user", "content": question})
                local_history.append({"role": "assistant", "content": sql})
                if len(local_history) > 8:
                    del local_history[:-8]
                session["history"] = local_history

            except Exception as ex:
                error = str(ex)

    return render_template(
        "index.html",
        question=question,
        sql=sql,
        explanation=explanation,
        headers=headers,
        rows=rows,
        error=error,
        table_count=len(registry.tables),
        tables=", ".join(t.name for t in registry.tables),
        metrics=metrics # <-- Pass statistics to UI
    )

# ------------------------------------------------------------------
# Health Check
# ------------------------------------------------------------------

@app.route("/health")
def health():
    return {
        "status": "ok",
        "database": DATABASE_URL
    }


# ------------------------------------------------------------------
# Start
# ------------------------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 7860)),
        debug=True
    )