FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY bot.py .
COPY .env .env.example

# Create data and logs directories
RUN mkdir -p data logs

# Run bot
CMD ["python", "bot.py"]
