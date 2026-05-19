FROM python:3.11-slim

WORKDIR /app

# Cache bust: v2
RUN pip install --upgrade pip && \
    pip install python-telegram-bot==20.7 aiohttp==3.9.5

COPY bot.py .

CMD ["python", "bot.py"]
