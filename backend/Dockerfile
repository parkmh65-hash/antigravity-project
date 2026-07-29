# Use official lightweight Python image
FROM python:3.11-slim

# Set environment variables
# Note: Allow writing bytecode (.pyc) for faster startup
ENV PYTHONUNBUFFERED=1 \
    PORT=8080

# Set working directory
WORKDIR /app

# Copy requirements file first for caching
COPY requirements.txt .

# Install dependencies and clean pip cache
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the necessary source directories and DB files
# This prevents copying scratch folders, tests, or large local assets
COPY backend/ ./backend/
COPY storage/ ./storage/

# Pre-compile python source files to bytecode (.pyc) for zero runtime compilation overhead (reduces cold start)
RUN python -m compileall .

# Expose target port for Cloud Run
EXPOSE 8080

# Command to run uvicorn with optimized worker management
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT} --workers 2"]
