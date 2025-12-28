# Инструкция по развертыванию

## Локальная разработка

### 1. Подготовка

```bash
# cd web (не нужно)
cp .env.example .env
# Отредактируйте .env при необходимости
```

### 2. Запуск

```bash
# Запустить все сервисы
docker-compose up --build

# Или в фоне
docker-compose up -d --build
```

### 3. Миграции и создание суперпользователя

```bash
# Применить миграции
docker-compose exec web python manage.py migrate

# Создать суперпользователя (опционально)
docker-compose exec web python manage.py createsuperuser
```

### 4. Использование Makefile (удобнее)

```bash
# Запустить
make up

# Миграции
make migrate

# Создать суперпользователя
make createsuperuser

# Логи
make logs

# Остановить
make down
```

Приложение будет доступно по адресу: http://localhost:8000/

## Продакшен развертывание

### 1. Подготовка

```bash
# cd web (не нужно)
cp .env.prod.example .env
```

**ВАЖНО:** Отредактируйте `.env` и измените:
- `SECRET_KEY` - сгенерируйте новый секретный ключ
- `POSTGRES_PASSWORD` - установите сильный пароль
- `ALLOWED_HOSTS` - укажите ваш домен
- `DEBUG=False` - убедитесь что отключен

### 2. Генерация SECRET_KEY

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Скопируйте результат в `.env` как `SECRET_KEY`.

### 3. Запуск в продакшен режиме

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### 4. Настройка SSL (HTTPS)

1. Получите SSL сертификаты (например, через Let's Encrypt)
2. Поместите сертификаты в `nginx/ssl/`:
   - `cert.pem` - сертификат
   - `key.pem` - приватный ключ
3. Раскомментируйте HTTPS секцию в `nginx/conf.d/default.conf`
4. Перезапустите nginx:
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart nginx
```

### 5. Миграции

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py migrate
```

### 6. Создание суперпользователя

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

## Мониторинг

### Просмотр логов

```bash
# Все логи
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f web
docker-compose logs -f celery

# Продакшен
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
```

### Проверка статуса

```bash
docker-compose ps
```

### Мониторинг Celery

```bash
# Статус worker
docker-compose exec web celery -A voice_recorder inspect active

# Мониторинг задач
docker-compose exec web celery -A voice_recorder events

# Статистика
docker-compose exec web celery -A voice_recorder inspect stats
```

## Резервное копирование

### База данных

```bash
# Создать бэкап
docker-compose exec db pg_dump -U postgres voice_recorder > backup_$(date +%Y%m%d_%H%M%S).sql

# Или через Makefile
make backup-db
```

### Восстановление

```bash
# Восстановить из бэкапа
docker-compose exec -T db psql -U postgres voice_recorder < backup.sql

# Или через Makefile
make restore-db FILE=backup.sql
```

### Медиа файлы

Медиа файлы хранятся в `./media/`. Просто скопируйте эту директорию для бэкапа.

## Обновление

```bash
# Остановить приложение
docker-compose down

# Получить обновления кода (git pull и т.д.)

# Пересобрать и запустить
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Применить миграции
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py migrate
```

## Масштабирование

### Увеличение количества Celery workers

Отредактируйте `docker-compose.prod.yml`:

```yaml
celery:
  command: celery -A voice_recorder worker --loglevel=info --concurrency=4
```

Или запустите несколько инстансов:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml scale celery=3
```

### Увеличение количества Gunicorn workers

Отредактируйте `docker-compose.prod.yml`:

```yaml
web:
  command: gunicorn --workers 8 --threads 2 ...
```

## Производительность

### Настройка ресурсов

Отредактируйте `docker-compose.prod.yml` для ограничения ресурсов:

```yaml
services:
  web:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### Оптимизация PostgreSQL

Добавьте в `docker-compose.prod.yml`:

```yaml
db:
  environment:
    - POSTGRES_SHARED_BUFFERS=256MB
    - POSTGRES_EFFECTIVE_CACHE_SIZE=1GB
```

## Безопасность

1. ✅ Используйте сильные пароли для БД
2. ✅ Измените SECRET_KEY
3. ✅ Включите HTTPS
4. ✅ Настройте ALLOWED_HOSTS
5. ✅ Отключите DEBUG в продакшене
6. ✅ Регулярно обновляйте зависимости
7. ✅ Настройте firewall для ограничения доступа к портам

## Решение проблем

### Ошибка подключения к БД

```bash
# Проверить статус PostgreSQL
docker-compose logs db

# Перезапустить
docker-compose restart db
```

### Ошибка с Celery

```bash
# Проверить статус Redis
docker-compose logs redis

# Перезапустить Celery
docker-compose restart celery
```

### Проблемы с правами доступа

```bash
# Исправить права на медиа файлы
sudo chown -R 1000:1000 media/
sudo chmod -R 755 media/
```

### Очистка

```bash
# Остановить и удалить все
docker-compose down -v

# Очистить неиспользуемые образы
docker system prune -a
```

