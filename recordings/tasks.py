"""Background tasks for recordings"""
from django.utils import timezone
from celery import shared_task
from celery.exceptions import Retry, MaxRetriesExceededError
import logging
from pathlib import Path

from .models import Recording
from .services.whisper_service import WhisperService
from .services.audio_service import AudioService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def transcribe_recording_task(self, recording_id):
    """Transcribe recording in background"""
    try:
        recording = Recording.objects.get(pk=recording_id)
        
        if recording.status == 'completed':
            logger.info(f"Запись {recording_id} уже обработана")
            return
        
        recording.status = 'processing'
        recording.celery_task_id = self.request.id
        recording.save()
        
        # Получить путь к файлу
        audio_path = Path(recording.audio_file.path)
        
        # Распознать речь
        whisper_service = WhisperService()
        result = whisper_service.transcribe_file(
            audio_path,
            model_size=recording.whisper_model,
            language='ru'  # Можно добавить в модель
        )
        
        # Сохранить результат
        recording.transcription = result['text']
        recording.status = 'completed'
        recording.processed_at = timezone.now()
        recording.save()
        
        logger.info(f"Запись {recording_id} успешно обработана")
        
    except Recording.DoesNotExist:
        logger.error(f"Запись {recording_id} не найдена")
    except Exception as e:
        logger.error(f"Ошибка при обработке записи {recording_id}: {e}", exc_info=True)
        # Попробовать повторить задачу
        try:
            raise self.retry(exc=e, countdown=60)
        except MaxRetriesExceededError:
            # Если достигнут максимум попыток, отметить запись как failed
            try:
                recording = Recording.objects.get(pk=recording_id)
                recording.status = 'failed'
                recording.error_message = f"Ошибка после {self.max_retries} попыток: {str(e)}"
                recording.save()
                logger.error(f"Запись {recording_id} не удалось обработать после {self.max_retries} попыток")
            except Recording.DoesNotExist:
                logger.error(f"Запись {recording_id} не найдена при финальной обработке ошибки")
