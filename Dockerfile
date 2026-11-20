FROM node:22-bookworm-slim AS node
FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
COPY --from=node /usr/local/bin/node /usr/local/bin/node

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -U -r requirements.txt

COPY . .

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD ["python", "-c", "from http.client import HTTPConnection; from os import getenv; conn = HTTPConnection('127.0.0.1', int(getenv('PORT', '10000')), timeout=3); conn.request('GET', '/'); raise SystemExit(conn.getresponse().status != 200)"]

CMD ["python", "bot.py"]
