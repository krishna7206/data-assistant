import os
import re
from ollama import Client

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
# Fallback to local container host naming context if not explicitly defined
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")

# Initialize an isolated client instance targeting the adjacent container service
ollama_client = Client(host=OLLAMA_HOST)

def clean_llm_sql(sql: str) -> str:
    """
    Safely cleans minor structural wrappers the LLM might include,
    without trying to reconstruct or rewrite complex query clauses using regex.
    """
    # Strip markdown code blocks if the model ignores the prompt rule
    sql = re.sub(r"```sql", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"```", "", sql)
    
    # Remove backticks and trailing semicolons
    sql = sql.replace("`", "")
    sql = sql.rstrip(";").strip()
    
    return sql

def generate_sql(question: str, schema_context: str, tables: list, history: list) -> str:
    prompt = f"""
You are an expert database engineer generating optimal, syntax-perfect SQL queries targeting a SQLite database.

CRITICAL RULES:
1. Wrap table and column names in standard syntax if they conflict, but generally output clean column selections.
2. If using `GROUP BY`, every column in the `SELECT` block must either be wrapped in an aggregate function (like `SUM()`, `COUNT()`, `AVG()`) or explicitly present in the `GROUP BY` clause. Do not leave trailing columns out.
3. If the query references only ONE table, do NOT use a table alias. Write the full `tablename.columnname` for every column.
4. If joining multiple tables, always declare unique, short aliases in the `FROM`/`JOIN` clause before you reference them in the `SELECT` or `WHERE` blocks.
5. Return ONLY the raw SQL query string ready for execution. No conversational filler, no explanations, and no markdown formatting wrappers.

Database Schema Context:
{schema_context}

Example 1 (single table, no alias, valid grouping):
Question: What is the total order value per customer status?
SQL: SELECT Orders.Status, SUM(Orders.TotalValue) FROM Orders GROUP BY Orders.Status

Example 2 (join context using clear aliases):
Question: Give me the names of customers who placed orders in 2026.
SQL: SELECT c.CustomerName FROM Customers c INNER JOIN Orders o ON c.CustomerID = o.CustomerID WHERE o.OrderYear = 2026 GROUP BY c.CustomerName

Question: {question}
SQL:
"""

    response = ollama_client.chat(
        model=OLLAMA_MODEL,
        messages=history + [{"role": "user", "content": prompt}]
    )

    sql = response["message"]["content"].strip()
    sql = clean_llm_sql(sql)
    return sql

def explain_results(question: str, sql: str, results: list) -> str:
    prompt = f"""
A user asked: "{question}"

This SQL was run:
{sql}

These results came back:
{results}

Write a 2-3 sentence plain English summary of the results.
Be specific — mention actual names and numbers from the results.
"""
    response = ollama_client.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    return response["message"]["content"].strip()