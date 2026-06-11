# Use official slim Python runtime as parent image
FROM python:3.10-slim

# Prevent Python from writing .pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1

# Prevent Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the remaining project files
COPY . .

# Create a non-root group and user for running the application securely
RUN groupadd -r appgroup && \
    useradd -r -g appgroup -d /app -s /sbin/nologin appuser

# Create data directory for SQLite database storage and set permissions
RUN mkdir -p /app/data && \
    chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

# Start the application
CMD ["python", "main.py"]
