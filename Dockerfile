FROM python:3.13-slim

WORKDIR /app

# Only system deps needed for matplotlib (no Chrome/Playwright needed)
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8048

CMD ["python", "server.py"]
