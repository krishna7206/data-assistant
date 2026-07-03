# -------------------------------------------------------
# Python Runtime
# -------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# -------------------------------------------------------
# System packages (Only lightweight sqlite3)
# -------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# -------------------------------------------------------
# Python dependencies
# -------------------------------------------------------
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -------------------------------------------------------
# Copy application structures
# -------------------------------------------------------
COPY app/ .
COPY database ./database

# Run the database schema initializer script
RUN python database/init_db.py

EXPOSE 8080

# -------------------------------------------------------
# Run
# -------------------------------------------------------
CMD ["gunicorn", "-w", "2", "--reload", "-b", "0.0.0.0:8080", "app:app"]