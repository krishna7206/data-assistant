#init_db.py
import sqlite3
import os

db_path = "/app/database/dev.db"

def init_database():
    # Ensure directory framework exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"Initializing SQLite database at: {db_path}...")
    
    # Create sample tables matching your example prompts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Customers (
        CustomerID INTEGER PRIMARY KEY,
        CustomerName TEXT NOT NULL,
        Country TEXT NOT NULL
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Orders (
        OrderID INTEGER PRIMARY KEY,
        CustomerID INTEGER,
        Status TEXT NOT NULL,
        TotalValue NUMERIC,
        OrderYear INTEGER,
        FOREIGN KEY(CustomerID) REFERENCES Customers(CustomerID)
    );
    """)
    
    # Insert dummy data if empty
    cursor.execute("SELECT COUNT(*) FROM Customers")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO Customers VALUES (?, ?, ?)", [
            (1, "Alice Corp", "USA"),
            (2, "Bob LLC", "Canada")
        ])
        cursor.executemany("INSERT INTO Orders VALUES (?, ?, ?, ?, ?)", [
            (101, 1, "Completed", 1500.00, 2026),
            (102, 1, "Pending", 450.00, 2026),
            (103, 2, "Completed", 2300.00, 2025)
        ])
        conn.commit()
    
    conn.close()

if __name__ == "__main__":
    init_database()