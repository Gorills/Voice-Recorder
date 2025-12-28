# Быстрый старт с Docker

## Локальная разработка

1. **Клонируйте и перейдите в директорию:**
```bash
# cd web (не нужно)
```

2. **Скопируйте файл с переменными окружения:**
```bash
cp .env.example .env
```

3. **Запустите все сервисы:**
```bash
docker-compose up --build
```

4. **В другом терминале примените миграции:**
```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

5. **Откройте в браузере:**
http://localhost:8000/

## Продакшен

1. **Подготовка:**
```bash
cp .env.prod.example .env
# Отредактируйте .env - ОБЯЗАТЕЛЬНО измените SECRET_KEY и пароли!
```

2. **Запуск:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

3. **Миграции:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py migrate
```

## Полезные команды

```bash
# Просмотр логов
docker-compose logs -f

# Остановить
docker-compose down

# Перезапустить
docker-compose restart

# Выполнить команду
docker-compose exec web python manage.py shell
```

Подробнее см. `DEPLOY.md`
