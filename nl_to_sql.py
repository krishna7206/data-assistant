import ollama
import re
import os

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

def fix_groupby(sql: str) -> str:
    # find GROUP BY clause
    groupby_match = re.search(r'GROUP BY\s+(.+?)(?=ORDER BY|HAVING|$)', sql, re.IGNORECASE | re.DOTALL)
    select_match  = re.search(r'SELECT(?:\s+TOP\s*\(?\s*\d+\s*\)?)?\s+(.+?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)

    if not groupby_match or not select_match:
        return sql

    groupby_cols = [c.strip() for c in groupby_match.group(1).split(",")]
    select_cols  = [c.strip() for c in select_match.group(1).split(",")]

    # find non-aggregate select columns not in GROUP BY
    missing = []
    for col in select_cols:
        is_aggregate = any(fn in col.upper() for fn in ["SUM(", "COUNT(", "AVG(", "MAX(", "MIN("])
        if not is_aggregate and col not in groupby_cols:
            missing.append(col)

    # add missing columns to GROUP BY
    if missing:
        new_groupby = ", ".join(groupby_cols + missing)
        sql = re.sub(
            r'GROUP BY\s+(.+?)(?=ORDER BY|HAVING|$)',
            f'GROUP BY {new_groupby} ',
            sql,
            flags=re.IGNORECASE | re.DOTALL
        )

    return sql

def fix_sql(sql: str, tables: list) -> str:
    # remove backticks
    sql = sql.replace("`", "")

    # fix nested aggregates like SUM(SUM(x)) -> SUM(x)
    sql = re.sub(r'(SUM|AVG|COUNT|MAX|MIN)\(\s*(SUM|AVG|COUNT|MAX|MIN)\(([^)]+)\)\s*\)', r'\1(\3)', sql, flags=re.IGNORECASE)

    # remove trailing semicolon
    sql = sql.rstrip(";").strip()

    # replace LIMIT with TOP — handle LIMIT appearing after ORDER BY
    limit_match = re.search(r'LIMIT\s+(\d+)', sql, re.IGNORECASE)
    if limit_match:
        n = limit_match.group(1)
        # remove LIMIT clause wherever it appears
        sql = re.sub(r'\s*LIMIT\s+\d+', '', sql, flags=re.IGNORECASE).strip()
        # add TOP after SELECT only if not already there
        if not re.search(r'SELECT\s+TOP', sql, re.IGNORECASE):
            sql = re.sub(r'SELECT', f'SELECT TOP {n}', sql, count=1, flags=re.IGNORECASE)

    # model sometimes writes TOP n (or TOP (n)) in the wrong place, e.g. after
    # ORDER BY — reposition any stray TOP so it sits right after SELECT
    if not re.search(r'SELECT\s+TOP\s*\(?\s*\d+\s*\)?', sql, re.IGNORECASE):
        stray_top_match = re.search(r'\bTOP\s*\(?\s*(\d+)\s*\)?', sql, re.IGNORECASE)
        if stray_top_match:
            n = stray_top_match.group(1)
            sql = re.sub(r'\s*\bTOP\s*\(?\s*\d+\s*\)?', '', sql, flags=re.IGNORECASE).strip()
            sql = re.sub(r'SELECT', f'SELECT TOP {n}', sql, count=1, flags=re.IGNORECASE)

    # prefix unqualified table names
    for table in tables:
        sql = re.sub(
            rf'(?<!\.)(\b{table.name}\b)',
            f'{table.schema}.{table.name}',
            sql,
            flags=re.IGNORECASE
        )

    # fix GROUP BY
    sql = fix_groupby(sql)

    return sql.strip()
    

def generate_sql(question: str, schema_context: str, tables: list, history: list) -> str:
    prompt = f"""
You are a SQL Server expert. Given the database schema below, write a SQL query to answer the user's question.

Rules:
- Use ONLY the table and column names exactly as shown in the schema below
- Before writing the query, check which table each column belongs to
- If you need columns from multiple tables, use a JOIN
- Always use the full table name including schema, e.g. Sales.Orders not just Orders
- Use SQL Server syntax, so TOP instead of LIMIT
- Every column in the SELECT list must either be in an aggregate function like SUM() or COUNT(), or be in the GROUP BY clause
- If the query uses only ONE table, do NOT use a table alias — write the full schema.table name in front of each column instead
- Only use table aliases (like c, o) when joining two or more tables, and always define the alias in the FROM/JOIN clause before using it
- NEVER reference an alias (e.g. x.Column) unless that exact alias was defined in a FROM or JOIN clause in this same query
- For "top N per group" questions (e.g. top 2 per country), do NOT use TOP alone — TOP only limits the whole result, not per group. Use ROW_NUMBER() OVER (PARTITION BY <group column> ORDER BY <metric> DESC) in a subquery, then filter WHERE rn <= N in the outer query
- Return ONLY the raw SQL query, no explanations, no markdown

{schema_context}

Example 1 (single table, no alias):
Question: How many orders are there?
Thinking: OrderID is in Sales.Orders, only one table needed, no alias
SQL: SELECT COUNT(Sales.Orders.OrderID) FROM Sales.Orders

Example 2 (join, alias defined in FROM/JOIN):
Question: How many orders per country?
Thinking: Country is in Sales.Customers, OrderID is in Sales.Orders, join on CustomerID
SQL: SELECT c.Country, COUNT(o.OrderID) AS OrderCount FROM Sales.Customers c INNER JOIN Sales.Orders o ON c.CustomerID = o.CustomerID GROUP BY c.Country

Example 3 (top N per group, uses ROW_NUMBER + PARTITION BY):
Question: Top 2 customers by total sales, per country?
Thinking: need per-country ranking, not a global TOP, so rank within each country then keep rn <= 2
SQL: SELECT Country, CustomerID, TotalSales FROM (SELECT c.Country, c.CustomerID, SUM(o.Sales) AS TotalSales, ROW_NUMBER() OVER (PARTITION BY c.Country ORDER BY SUM(o.Sales) DESC) AS rn FROM Sales.Customers c INNER JOIN Sales.Orders o ON c.CustomerID = o.CustomerID GROUP BY c.Country, c.CustomerID) ranked WHERE rn <= 2

Question: {question}
SQL:
"""

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages= history + [{"role": "user", "content": prompt}]
    )

    sql = response["message"]["content"].strip()
    sql = fix_sql(sql, tables)
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
    response = ollama.chat(
        model="llama3.2",
        messages=[{"role": "user", "content": prompt}]
    )
    return response["message"]["content"].strip()