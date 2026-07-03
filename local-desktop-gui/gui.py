import tkinter as tk
from tkinter import scrolledtext
import threading

from schemaconnector import extract
from nl_to_sql import generate_sql, explain_results
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

engine = create_engine(os.getenv("DB_URL"))
registry = extract(engine)
schema_context = registry.to_prompt_context()

history = []


class DataAssistantGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Data Assistant")
        self.geometry("800x600")

        table_names = ", ".join(t.name for t in registry.tables)
        header = tk.Label(
            self,
            text=f"Connected to salesdb — {len(registry.tables)} tables: {table_names}",
            anchor="w",
            justify="left",
            wraplength=780,
        )
        header.pack(fill="x", padx=8, pady=(8, 0))

        self.chat_box = scrolledtext.ScrolledText(self, state="disabled", wrap="word")
        self.chat_box.pack(fill="both", expand=True, padx=8, pady=8)
        self.chat_box.tag_config("question", foreground="#0055aa", font=("TkDefaultFont", 10, "bold"))
        self.chat_box.tag_config("sql", foreground="#666666", font=("TkFixedFont", 9))
        self.chat_box.tag_config("error", foreground="#cc0000")

        input_frame = tk.Frame(self)
        input_frame.pack(fill="x", padx=8, pady=(0, 8))

        self.entry = tk.Entry(input_frame)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry.bind("<Return>", lambda event: self.on_submit())

        self.submit_btn = tk.Button(input_frame, text="Ask", command=self.on_submit)
        self.submit_btn.pack(side="right")

        self.entry.focus()

    def append(self, text_line, tag=None):
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", text_line + "\n", tag)
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

    def on_submit(self):
        question = self.entry.get().strip()
        if not question:
            return

        self.entry.delete(0, "end")
        self.submit_btn.config(state="disabled")
        self.append(f"You: {question}", "question")
        self.append("Thinking...")

        thread = threading.Thread(target=self.run_query, args=(question,), daemon=True)
        thread.start()

    def run_query(self, question):
        retry_context = None
        last_error = None
        sql = None
        for attempt in range(2):
            try:
                sql = generate_sql(question, schema_context, registry.tables, history, retry_context)

                with engine.connect() as conn:
                    result = conn.execute(text(sql))
                    rows = result.fetchall()

                explanation = explain_results(question, sql, rows)

                history.append({"role": "user", "content": question})
                history.append({"role": "assistant", "content": explanation})
                if len(history) > 8:
                    del history[:-8]

                self.after(0, self.show_result, sql, explanation)
                return
            except Exception as e:
                last_error = e
                if sql is not None:
                    retry_context = (sql, str(e))

        self.after(0, self.show_error, str(last_error))

    def show_result(self, sql, explanation):
        self.append(f"SQL: {sql}", "sql")
        self.append(f"Assistant: {explanation}\n")
        self.submit_btn.config(state="normal")
        self.entry.focus()

    def show_error(self, message):
        self.append(f"Error: {message}", "error")
        self.append("Try rephrasing your question\n")
        self.submit_btn.config(state="normal")
        self.entry.focus()


if __name__ == "__main__":
    app = DataAssistantGUI()
    app.mainloop()
