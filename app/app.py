from flask import Flask, render_template, request, session, jsonify
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from database.init_db import init_database 
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

registry = extract(engine)
schema_context = registry.to_prompt_context()


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

    # Initialize a clean session-based chat history if it doesn't exist
    if "history" not in session:
        session["history"] = []

    if request.method == "POST":

        question = request.form.get("question", "").strip()

        if question:

            try:

                # Generate SQL using the user's isolated session history
                sql = generate_sql(
                    question,
                    schema_context,
                    registry.tables,
                    session["history"]
                )

                # Execute SQL
                with engine.connect() as conn:

                    result = conn.execute(text(sql))

                    headers = list(result.keys())

                    # Convert SQLAlchemy Row objects to standard lists for reliable template rendering
                    rows = [list(row) for row in result.fetchall()]

                # Generate explanation
                explanation = explain_results(
                    question,
                    sql,
                    rows
                )

                # Local mutable copy of history to manipulate
                local_history = session["history"]

                local_history.append({
                    "role": "user",
                    "content": question
                })

                # CRITICAL: Append the generated SQL here instead of the description. 
                # This aligns with the prompt's structural rule: "Return ONLY the raw SQL query".
                local_history.append({
                    "role": "assistant",
                    "content": sql
                })

                if len(local_history) > 8:
                    del local_history[:-8]
                
                # Reassign back to the session to persist the updates
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
        tables=", ".join(t.name for t in registry.tables)
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
        port=8080,
        debug=True
    )