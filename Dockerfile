# Dockerfile для Django приложения
FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    ffmpeg \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копирование requirements и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копирование entrypoint скрипта
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Копирование проекта
COPY . .

# Создание директорий для медиа и статики
RUN mkdir -p /app/staticfiles /app/media /app/logs

# Пользователь для запуска приложения
RUN useradd -m -u 1000 django && \
    chown -R django:django /app && \
    chown django:django /entrypoint.sh
USER django

# Порт по умолчанию
EXPOSE 8000

# Entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Команда запуска (будет переопределена в docker-compose)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "voice_recorder.wsgi:application"]
