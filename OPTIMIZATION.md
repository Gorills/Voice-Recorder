# Оптимизация ресурсов проекта

Этот документ описывает все оптимизации и ограничения ресурсов, примененные к проекту для предотвращения перегрузки системы.

## Ограничения Docker ресурсов

### База данных PostgreSQL
- **CPU**: лимит 1.0, резерв 0.5
- **Память**: лимит 512MB, резерв 256MB
- **Максимум соединений**: 50
- **Shared buffers**: 128MB
- **Effective cache size**: 256MB
- **Work memory**: 4MB

### Redis
- **CPU**: лимит 0.5, резерв 0.25
- **Память**: лимит 384MB, резерв 128MB
- **Maxmemory**: 256MB
- **Политика вытеснения**: allkeys-lru (удаление наименее используемых ключей)
- **Отключено сохранение на диск** для уменьшения нагрузки

### Web сервер (Gunicorn)
- **CPU**: лимит 2.0, резерв 0.5
- **Память**: лимит 1GB, резерв 256MB
- **Воркеры**: 2 (уменьшено с 4)
- **Потоки**: 2 на воркер
- **Timeout**: 120 секунд
- **Keepalive**: 5 секунд
- **Max requests**: 1000 запросов на воркер (после перезапуск)

### Celery Worker
- **CPU**: лимит 2.0, резерв 0.5
- **Память**: лимит 2GB, резерв 512MB
- **Concurrency**: 2 параллельных задачи
- **Max tasks per child**: 20 (перезапуск после 20 задач)
- **Max memory per child**: 400MB
- **Time limit**: 1800 секунд (30 минут)
- **Soft time limit**: 1500 секунд (25 минут)

### Celery Beat
- **CPU**: лимит 0.5, резерв 0.1
- **Память**: лимит 256MB, резерв 64MB

## Настройки Django

### Размеры загружаемых файлов
- **FILE_UPLOAD_MAX_MEMORY_SIZE**: 50MB (файлы больше сохраняются на диск)
- **DATA_UPLOAD_MAX_MEMORY_SIZE**: 50MB
- **MAX_AUDIO_FILE_SIZE**: 100MB (максимальный размер одного аудио файла)
- **DATA_UPLOAD_MAX_NUMBER_FIELDS**: 1000

### База данных
- **CONN_MAX_AGE**: 300 секунд (5 минут) - уменьшено для экономии памяти
- **Connection timeout**: 10 секунд
- **Statement timeout**: 30 секунд

### Celery
- **Prefetch multiplier**: 1 (не забирать задачи заранее)
- **Task acks late**: True (подтверждать после выполнения)
- **Task reject on worker lost**: True
- **Result expires**: 86400 секунд (24 часа)
- **Visibility timeout**: 3600 секунд (1 час)

## Очистка старых данных

### Команда cleanup_old_recordings

Для очистки старых записей используйте:

```bash
# Просмотр что будет удалено (dry-run)
docker compose exec web python manage.py cleanup_old_recordings --days=90 --dry-run

# Удалить записи старше 90 дней
docker compose exec web python manage.py cleanup_old_recordings --days=90

# Удалить только failed/uploaded записи (сохранить completed)
docker compose exec web python manage.py cleanup_old_recordings --days=90 --keep-completed
```

Рекомендуется настроить периодическое выполнение через cron или celery-beat:

```python
# В celery.py или settings.py
CELERY_BEAT_SCHEDULE = {
    'cleanup-old-recordings': {
        'task': 'recordings.tasks.cleanup_old_recordings',
        'schedule': crontab(hour=2, minute=0),  # Каждый день в 2:00
    },
}
```

## Мониторинг использования ресурсов

### Проверка использования ресурсов Docker

```bash
# Использование ресурсов всех контейнеров
docker stats

# Использование ресурсов конкретного контейнера
docker stats audio-web-1
docker stats audio-celery-1
docker stats audio-db-1
docker stats audio-redis-1
```

### Проверка размера данных

```bash
# Размер volumes
docker system df -v

# Размер медиа файлов
du -sh media/

# Размер базы данных
docker compose exec db psql -U postgres -d voice_recorder -c "SELECT pg_size_pretty(pg_database_size('voice_recorder'));"
```

### Проверка Redis памяти

```bash
docker compose exec redis redis-cli INFO memory
```

## Рекомендации

1. **Регулярно очищайте старые записи** - используйте команду `cleanup_old_recordings`
2. **Мониторьте использование памяти** - используйте `docker stats`
3. **Настройте автоматическую очистку** - добавьте задачу в celery-beat
4. **Используйте меньшие модели Whisper** для экономии памяти (tiny, base)
5. **Ограничьте размер загружаемых файлов** через настройки Django
6. **Проверяйте логи** на предмет ошибок памяти или таймаутов

## Настройка под вашу систему

Если у вас меньше ресурсов, вы можете уменьшить лимиты в `docker-compose.yml`:

- Уменьшите количество воркеров Gunicorn до 1
- Уменьшите concurrency Celery до 1
- Уменьшите лимиты памяти для всех сервисов
- Используйте только tiny/base модели Whisper

Если у вас больше ресурсов, можно увеличить лимиты для лучшей производительности.


