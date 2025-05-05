FROM python:3.10-slim AS builder


WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt 
COPY app /app/app
COPY app/.env /app/.env


FROM python:3.10-slim


WORKDIR /app
ENV PYTHONPATH="/app"

COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY --from=builder /app/app /app/app
COPY --from=builder /app/.env /app/.env

RUN pip install --no-cache-dir uvicorn

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

