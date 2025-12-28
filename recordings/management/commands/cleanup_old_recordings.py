"""
Management command для очистки старых записей и файлов
Использование: python manage.py cleanup_old_recordings --days=90 --dry-run
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import os
from recordings.models import Recording


class Command(BaseCommand):
    help = 'Удаляет старые записи и связанные файлы старше указанного количества дней'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Количество дней для сохранения записей (по умолчанию 90)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет удалено без фактического удаления',
        )
        parser.add_argument(
            '--keep-completed',
            action='store_true',
            help='Не удалять завершенные записи (только failed/uploaded старше N дней)',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        keep_completed = options['keep_completed']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Построить запрос
        query = Recording.objects.filter(created_at__lt=cutoff_date)
        
        if keep_completed:
            # Удалять только failed и uploaded, но не completed
            query = query.exclude(status='completed')
        
        old_recordings = query.select_related('user')
        count = old_recordings.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(f'Нет записей старше {days} дней для удаления')
            )
            return
        
        self.stdout.write(
            self.style.WARNING(f'Найдено {count} записей старше {days} дней')
        )
        
        if dry_run:
            self.stdout.write(self.style.WARNING('РЕЖИМ DRY-RUN - ничего не будет удалено'))
            for recording in old_recordings[:10]:  # Показать первые 10
                self.stdout.write(f'  - {recording.id}: {recording.title} ({recording.status}) - {recording.created_at}')
            if count > 10:
                self.stdout.write(f'  ... и еще {count - 10} записей')
            return
        
        # Удаление файлов и записей
        deleted_count = 0
        deleted_size = 0
        errors = 0
        
        for recording in old_recordings:
            try:
                # Удалить файл если он существует
                if recording.audio_file:
                    file_path = recording.audio_file.path
                    if os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        deleted_size += file_size
                        
                        # Попытаться удалить родительскую директорию если она пуста
                        try:
                            parent_dir = os.path.dirname(file_path)
                            if os.path.exists(parent_dir) and not os.listdir(parent_dir):
                                os.rmdir(parent_dir)
                        except OSError:
                            pass  # Директория не пуста или ошибка - не критично
                
                # Удалить запись из БД
                recording.delete()
                deleted_count += 1
                
                if deleted_count % 100 == 0:
                    self.stdout.write(f'Удалено {deleted_count} записей...')
                    
            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f'Ошибка при удалении записи {recording.id}: {e}')
                )
        
        # Результаты
        size_mb = deleted_size / (1024 * 1024)
        self.stdout.write(
            self.style.SUCCESS(
                f'\nУспешно удалено {deleted_count} записей\n'
                f'Освобождено места: {size_mb:.2f} MB'
            )
        )
        
        if errors > 0:
            self.stdout.write(
                self.style.WARNING(f'Произошло {errors} ошибок при удалении')
            )


