FROM python:3.11-slim

WORKDIR /app

RUN pip install --upgrade pip
RUN pip install python-telegram-bot==20.7
RUN pip install aiohttp==3.9.5

COPY bot.py .

CMD ["python", "-u", "bot.py"]
