# Инструкция по настройке веб-приложения

## Полная установка

### 1. Подготовка окружения

```bash
cd web
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

### 2. Установка зависимостей

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Настройка базы данных

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Создание суперпользователя (опционально)

```bash
python manage.py createsuperuser
```

### 5. Создание директорий

```bash
mkdir -p media/audio static
```

### 6. Запуск сервера

```bash
python manage.py runserver
```

Откройте http://127.0.0.1:8000/

## Настройка фоновых задач (Celery)

Для асинхронной обработки записей:

### 1. Установка Celery и Redis

```bash
pip install celery redis
```

### 2. Настройка Celery в settings.py

Добавьте в `voice_recorder/settings.py`:

```python
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
```

### 3. Создайте файл `voice_recorder/celery.py`:

```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'voice_recorder.settings')

app = Celery('voice_recorder')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

### 4. Запуск Celery worker

```bash
celery -A voice_recorder worker --loglevel=info
```

## Структура проекта

```
web/
├── voice_recorder/          # Настройки проекта
│   ├── settings.py         # Основные настройки
│   ├── urls.py             # Главные URL маршруты
│   └── wsgi.py             # WSGI конфигурация
├── recordings/             # Основное приложение
│   ├── models.py           # Модели (Recording, UserSettings)
│   ├── views.py            # Представления (views)
│   ├── forms.py            # Формы
│   ├── urls.py             # URL маршруты приложения
│   ├── services/            # Сервисы
│   │   ├── whisper_service.py  # Работа с Whisper
│   │   └── audio_service.py    # Работа с аудио
│   └── tasks.py            # Фоновые задачи
├── templates/              # HTML шаблоны
│   ├── base.html           # Базовый шаблон
│   └── recordings/         # Шаблоны приложения
├── static/                 # Статические файлы (CSS, JS)
├── media/                  # Загруженные файлы
└── manage.py              # Django управление
```

## Основные функции

### Для пользователей:

1. **Регистрация и вход** - система аутентификации
2. **Дашборд** - главная страница со статистикой
3. **Загрузка записей** - загрузка аудио файлов
4. **Распознавание** - выбор модели Whisper и запуск обработки
5. **Просмотр транскрипций** - просмотр результатов
6. **Скачивание** - скачивание аудио и текста
7. **Настройки** - персональные настройки пользователя

### Модели Whisper:

- **Tiny** - Самая быстрая (~75 MB)
- **Base** - Баланс (~150 MB) - рекомендуется
- **Small** - Хорошее качество (~500 MB)
- **Medium** - Высокое качество (~1.5 GB)
- **Large** - Наилучшее качество (~3 GB)

## Развертывание в продакшене

### 1. Настройка settings.py

```python
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com']
SECRET_KEY = os.environ.get('SECRET_KEY')  # Используйте переменную окружения
```

### 2. Использование PostgreSQL

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'voice_recorder',
        'USER': 'user',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### 3. Сбор статических файлов

```bash
python manage.py collectstatic
```

### 4. Использование Gunicorn

```bash
pip install gunicorn
gunicorn voice_recorder.wsgi:application
```

### 5. Настройка Nginx

Пример конфигурации для Nginx (в `/etc/nginx/sites-available/voice_recorder`):

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location /static/ {
        alias /path/to/web/staticfiles/;
    }

    location /media/ {
        alias /path/to/web/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Решение проблем

### Ошибка миграций

```bash
python manage.py makemigrations recordings
python manage.py migrate
```

### Ошибка с медиа файлами

Убедитесь что директория `media/` существует и доступна для записи:

```bash
chmod 755 media
chmod 755 media/audio
```

### Медленная обработка

- Используйте Celery для фоновой обработки
- Выберите меньшую модель Whisper
- Используйте более мощный сервер

### Ошибка с Whisper

Убедитесь что Whisper установлен:

```bash
pip install openai-whisper
```

При первом использовании модель будет автоматически загружена.

