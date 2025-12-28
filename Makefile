.PHONY: help build up down restart logs shell migrate createsuperuser collectstatic backup restore

help: ## Показать справку
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Собрать Docker образы
	docker-compose build

up: ## Запустить приложение (разработка)
	docker-compose up -d

up-prod: ## Запустить приложение (продакшен)
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

down: ## Остановить приложение
	docker-compose down

down-prod: ## Остановить приложение (продакшен)
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

restart: ## Перезапустить приложение
	docker-compose restart

restart-prod: ## Перезапустить приложение (продакшен)
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart

logs: ## Показать логи
	docker-compose logs -f

logs-prod: ## Показать логи (продакшен)
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

shell: ## Открыть Django shell
	docker-compose exec web python manage.py shell

migrate: ## Применить миграции
	docker-compose exec web python manage.py migrate

makemigrations: ## Создать миграции
	docker-compose exec web python manage.py makemigrations

createsuperuser: ## Создать суперпользователя
	docker-compose exec web python manage.py createsuperuser

collectstatic: ## Собрать статические файлы
	docker-compose exec web python manage.py collectstatic --noinput

backup-db: ## Создать бэкап базы данных
	docker-compose exec db pg_dump -U postgres voice_recorder > backup_$$(date +%Y%m%d_%H%M%S).sql

restore-db: ## Восстановить базу данных (использовать: make restore-db FILE=backup.sql)
	docker-compose exec -T db psql -U postgres voice_recorder < $(FILE)

clean: ## Очистить неиспользуемые образы и volumes
	docker-compose down -v
	docker system prune -f

ps: ## Показать статус контейнеров
	docker-compose ps

ps-prod: ## Показать статус контейнеров (продакшен)
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps

