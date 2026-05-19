FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir python-telegram-bot==20.7 aiohttp==3.9.5

COPY bot.py .

CMD ["python", "bot.py"]
