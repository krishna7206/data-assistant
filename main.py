from schemaconnector import extract
from nl_to_sql import generate_sql, explain_results
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

# connect and extract schema once
print(os.getenv("DB_URL"))
engine = create_engine(os.getenv("DB_URL"))

registry = extract(engine)
schema_context = registry.to_prompt_context()

print("✅ Connected to salesdb")
print(f"📋 Found {len(registry.tables)} tables: {', '.join(t.name for t in registry.tables)}")
print("\nAsk a question about your data (or type 'exit' to quit)\n")

# interactive loop
while True:
    question = input("You: ").strip()

    if question.lower() in ("exit", "quit"):
        print("Bye!")
        break

    if not question:
        continue

    try:
        # generate and run SQL
        sql = generate_sql(question, schema_context, registry.tables)
        print(f"\nSQL: {sql}\n")

        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = result.fetchall()

        # explain results
        explanation = explain_results(question, sql, rows)
        print(f"Answer: {explanation}\n")

    except Exception as e:
        print(f"Error: {e}\n")
        print("Try rephrasing your question\n")
