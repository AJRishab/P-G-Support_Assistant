# -------------------------------------------------
#  Python backend (FastAPI) – slim, production ready
# -------------------------------------------------
FROM python:3.8-slim

# Set working directory
WORKDIR /app

# Install system build-tools needed for some wheels (gcc)
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching (from server/ subdir in project)
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source
COPY server/src/ ./src/
COPY server/run.py ./run.py

# Health-check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/tickets || exit 1

# Expose FastAPI port
EXPOSE 8000

# Default command – starts the uvicorn server
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]