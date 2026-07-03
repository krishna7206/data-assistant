 NL to SQL Data Assistant

A command-line tool that lets you query your SQL Server database in plain English. Ask a question, get an answer — no SQL knowledge required.

Now added in a GUI interface where we are able to see the conversation history as well as improved the prompt to the underling LLM improving answer quality

Built with Python, SQLAlchemy, and a local LLM running via Ollama. No API keys, no cost, runs entirely on your machine.


<img width="687" height="199" alt="LLM_SQL_bot" src="https://github.com/user-attachments/assets/da0e3a82-ed7d-43af-811b-b88862b07ff2" />
<img width="1607" height="213" alt="LLM_response_0107" src="https://github.com/user-attachments/assets/3b981e4c-7ad2-4f5f-b932-bb18c4a55494" />
<img width="1602" height="181" alt="LLM_response_0109" src="https://github.com/user-attachments/assets/2b4d13b8-03ba-4afd-b9dc-cd368556251f" />
<img width="806" height="621" alt="image" src="https://github.com/user-attachments/assets/2481725a-7ab9-460d-a194-50bb69e18115" />



---

 Example Queries

**"Which department has the highest salary?"**
```
SQL: SELECT e.Department, MAX(e.Salary) FROM Sales.Employees e GROUP BY e.Department

Answer: The department with the highest salary is Sales, with a maximum salary of
$90,000 for John Smith. The Marketing department has the lowest maximum salary
among the listed departments, which is $65,000 for Emily Johnson.
```

**"Can you return the customer names who have no information available?"**
```
SQL: SELECT c.FirstName + ' ' + c.LastName FROM Sales.Customers c
     WHERE c.Score IS NULL OR c.Score = 0

Answer: The query returned the name "Anna Adams" as there is no information
available on customers with a score of either NULL or 0.
```

**"What are the top 3 countries by total sales?"**
```
SQL: SELECT TOP 3 c.Country, SUM(o.Sales) AS TotalSales
     FROM Sales.Customers c
     INNER JOIN Sales.Orders o ON c.CustomerID = o.CustomerID
     GROUP BY c.Country

Answer: The top 3 countries by sales are Germany and USA. Germany has generated
$200 in total sales, while USA has generated $180 in total sales.
```

---

 How It Works

1. **Schema Extractor** — connects to your database and automatically discovers all tables, columns, types, and row counts. Formats everything into a prompt the LLM can understand.
2. **NL to SQL Engine** — takes your question and the schema context, sends it to a local LLM via Ollama, and gets SQL back. Automatically fixes common SQL Server syntax issues.
3. **Result Explainer** — passes the query results back to the LLM and generates a plain English summary.

---
 Setup

### Prerequisites

- Python 3.10+
- SQL Server (local or remote)
- [Ollama](https://ollama.com) installed and running

### 1. Clone the repository

```bash
git clone https://github.com/krishna7206/data-assistant.git
cd data-assistant
```

### 2. Install dependencies

```bash
pip install sqlalchemy pymssql ollama python-dotenv
```

### 3. Pull the LLM model

```bash
ollama pull llama3.2
```

### 4. Create a `.env` file

Create a file called `.env` in the project folder:

```
DB_URL=mssql+pymssql://your_user:your_password@your_host:your_port/your_database
```

### 5. Set up a SQL Server login

Run this in SSMS to create a read-only login for the assistant:

```sql
CREATE LOGIN datauser WITH PASSWORD = 'your_password',
    CHECK_POLICY = OFF,
    CHECK_EXPIRATION = OFF;

USE your_database;
CREATE USER datauser FOR LOGIN datauser;
ALTER ROLE db_datareader ADD MEMBER datauser;
```

### 6. Run it

```bash
python main.py
```

---

 Project Structure

```
data-assistant/
├── main.py              # entry point, interactive query loop
├── schemaconnector.py   # connects to DB, extracts schema metadata
├── nl_to_sql.py         # NL → SQL generation and result explanation
├── .env                 # your credentials (not committed to Git)
└── .gitignore
```

---
 Requirements

| Package       | Purpose                        |
|---------------|--------------------------------|
| sqlalchemy    | Database connection and reflection |
| pymssql       | SQL Server driver              |
| ollama        | Local LLM inference            |
| python-dotenv | Load credentials from .env     |

---

 Notes

- This tool generates and runs SQL automatically. It is configured as read-only via the `db_datareader` role but always review generated SQL before running in production.
- The assistant works best with [Ollama](https://ollama.com) running in the background. Start it with `ollama serve` if it is not already running.
- If you are connecting from WSL to a SQL Server instance on Windows, make sure TCP/IP is enabled in SQL Server Configuration Manager and port 1433 (or your dynamic port) is open in Windows Firewall.

---

 What's Next



- [ ] Support for PostgreSQL, DuckDB, and CSV files
- [ ] Query history logging

---

## 📄 License

MIT


############################