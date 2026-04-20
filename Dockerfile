FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY fastapi_app /app/fastapi_app

EXPOSE 8000

CMD ["uvicorn", "fastapi_app.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

