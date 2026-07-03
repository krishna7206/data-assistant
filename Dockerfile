FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies needed for compiling and sqlite
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ make cmake wget sqlite3 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu

# Install python packages (using the prebuilt CPU index to keep it fast)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu

# Create a models directory and pull the 350MB Qwen model from Hugging Face
RUN mkdir -p /app/models && \
    wget -O /app/models/qwen.gguf https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf

COPY . .

RUN mkdir -p /app/database
RUN useradd -m -u 1000 user && chown -R user:user /app

USER user

RUN python init_db.py

EXPOSE 7860

# Increase timeout to 5 minutes (--timeout 300) to allow slow CPU loading, 
# and use a single sync worker (-k sync) to avoid C-level thread conflicts.
CMD ["sh", "-c", "gunicorn -w 1 -k sync --timeout 300 --reload -b 0.0.0.0:${PORT:-7860} app:app"]