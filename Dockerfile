FROM python:3.12-slim

WORKDIR /app

# Install system deps for psycopg2 and xhtml2pdf (pycairo)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc libcairo2-dev pkg-config && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend_core/ backend_core/
COPY kumar_frontend/ kumar_frontend/
COPY deploy/ deploy/

ENV ENVIRONMENT=production
ENV PORT=8080

EXPOSE 8080

CMD exec gunicorn -w 2 -k uvicorn.workers.UvicornWorker backend_core.app.main:app --bind 0.0.0.0:$PORT --timeout 120
