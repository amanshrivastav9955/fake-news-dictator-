# Stage 1: Build & Dependency installation
FROM python:3.10-slim as builder

WORKDIR /app

# Install system utilities needed for building packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install dependencies into a wheels directory
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Final lightweight image
FROM python:3.10-slim

WORKDIR /app

# Install runtime library dependencies (e.g. for PostgreSQL client)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed libraries from builder stage
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application assets
COPY . .

# Environment settings
ENV PORT=5000
ENV PYTHONUNBUFFERED=1
ENV DATABASE_TYPE=sqlite
ENV DATABASE_NAME=database.db

# Prefetch NLTK collections to prevent runtime latency
RUN python -c "import nltk; nltk.download('stopwords', quiet=True); nltk.download('vader_lexicon', quiet=True); nltk.download('punkt', quiet=True); nltk.download('averaged_perceptron_tagger', quiet=True)"

# Expose server port
EXPOSE 5000

# Start command (Runs the Socket.IO server directly)
CMD ["python", "app.py"]
