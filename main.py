from schemaconnector import extract
from nl_to_sql import generate_sql, explain_results
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

engine = create_engine(os.getenv("DB_URL"))

registry = extract(engine)
schema_context = registry.to_prompt_context()

print("✅ Connected to salesdb")
print(f"📋 Found {len(registry.tables)} tables: {', '.join(t.name for t in registry.tables)}")
print("\nAsk a question about your data (or type 'exit' to quit)\n")

history = []

while True:
    question = input("You: ").strip()

    if question.lower() in ("exit", "quit"):
        print("Bye!")
        break

    if not question:
        continue

    try:
        # 1. generate SQL
        sql = generate_sql(question, schema_context, registry.tables, history)
        #print(f"\nSQL: {sql}\n")

        # 2. run SQL and get rows
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = result.fetchall()
            headers = list(result.keys())

        

        # 4. explain results
        explanation = explain_results(question, sql, rows)
        print(f"Explanation: {explanation}\n")
        

        # 5. update history
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": explanation})

        if len(history) > 8:
            history = history[-8:]

    except Exception as e:
        print(f"Error: {e}\n")
        print("Try rephrasing your question\n")