import os
import re
from llama_cpp import Llama
# from datetime import datetime

LOG_FILE= "app.log"

# Load the model directly into memory from the local container path
llm = Llama(
    model_path="/app/models/qwen.gguf",
    n_ctx=1024,
    f16_kv=True,
    flash_attn=True,
    embedding=False,
    verbose=False,
    n_threads=2
)

def clean_llm_sql(sql: str) -> str:
    sql = re.sub(r"```sql", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"```", "", sql)
    sql = sql.replace("`", "")
    return sql.rstrip(";").strip()

def generate_sql(question: str, schema_context: str, tables: list, history: list) -> dict:
    prompt = f"<|im_start|>system\nYou are an expert database engineer generating optimal SQLite queries. Return ONLY the raw SQL string without formatting wrappers.<|im_end|>\n"
    prompt += f"<|im_start|>user\nSchema:\n{schema_context}\n\nQuestion: {question}<|im_end|>\n<|im_start|>assistant\nSQL:"

    output = llm(prompt, max_tokens=150, stop=["<|im_end|>", "\n\n"])
    raw_sql = output["choices"][0]["text"].strip()
    
    # Extract structural token usage metadata from the response object
    usage = output.get("usage", {})
    
    return {
        "sql": clean_llm_sql(raw_sql),
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0)
    }

def explain_results(question: str, sql: str, results: list) -> str:
    prompt = f"<|im_start|>system\nSummarize the database results in 2-3 sentences.<|im_end|>\n"
    prompt += f"<|im_start|>user\nQuestion: {question}\nSQL: {sql}\nResults: {results}<|im_end|>\n<|im_start|>assistant\n"
    
    output = llm(prompt, max_tokens=150, stop=["<|im_end|>"])
    usage = output.get("usage", {})

    return {
        "explanation": output["choices"][0]["text"].strip(),
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0)
    }

#==== FUTURE LOGGING WILDIN====
# def write_llm_trace(message: str):
#     """Utility to instantly write background LLM states to our real-time log interface."""
#     timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     with open(LOG_FILE, "a") as f:
#         f.write(f"[{timestamp}] [LLM ENGINE] {message}\n")    

# def generate_sql(question: str, schema_context: str, tables: list, history: list) -> str:
#     prompt = f"<|im_start|>system\nYou are an expert database engineer generating optimal SQLite queries. Return ONLY the raw SQL string without formatting wrappers.<|im_end|>\n"
#     prompt += f"<|im_start|>user\nSchema:\n{schema_context}\n\nQuestion: {question}<|im_end|>\n<|im_start|>assistant\nSQL:"

#     # Trace exactly what text context we are handing down to the model layers
#     write_llm_trace("----- INCOMING GENERATION TASK -----")
#     write_llm_trace(f"Evaluating user question: '{question}'")
#     write_llm_trace(f"Schema Prompt Context passed down:\n{schema_context}")

#     # Fire execution processing
#     write_llm_trace("Computing model layer token probabilities...")
#     output = llm(prompt, max_tokens=150, stop=["<|im_end|>", "\n\n"])
    
#     raw_response = output["choices"][0]["text"].strip()
#     write_llm_trace(f"Raw model completion output generated: '{raw_response}'")
    
#     sql = clean_llm_sql(raw_response)
#     write_llm_trace(f"Normalized execution SQL string: '{sql}'")
#     return sql

# def explain_results(question: str, sql: str, results: list) -> str:
#     prompt = f"<|im_start|>system\nSummarize the database results in 2-3 sentences.<|im_end|>\n"
#     prompt += f"<|im_start|>user\nQuestion: {question}\nSQL: {sql}\nResults: {results}<|im_end|>\n<|im_start|>assistant\n"
    
#     write_llm_trace("----- INCOMING SUMMARY TASK -----")
#     write_llm_trace(f"Analyzing Result matrix row count: {len(results)}")
    
#     output = llm(prompt, max_tokens=150, stop=["<|im_end|>"])
#     summary = output["choices"][0]["text"].strip()
    
#     write_llm_trace(f"Completed summary text: '{summary}'")
#     return summary


