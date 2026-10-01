FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -r requirements.txt -e .

COPY . .

USER nobody

EXPOSE 8000

CMD ["uvicorn", "integration_hub.main:app", "--host", "0.0.0.0", "--port", "8000"]
