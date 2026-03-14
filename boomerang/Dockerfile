FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    build-essential git curl wget nodejs npm \
    && npm install -g @anthropic-ai/claude-code \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/boomerang_tools /app/temp_tools /app/tests /app/backups /app/data \
    && touch /app/boomerang_tools/__init__.py \
    && touch /app/temp_tools/__init__.py \
    && touch /app/tests/__init__.py

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
