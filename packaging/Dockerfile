FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system bordle \
    && useradd --system --gid bordle --create-home bordle

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=bordle:bordle . .

USER bordle

EXPOSE 8000

CMD ["sh", "scripts/start_app.sh"]
