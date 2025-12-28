"""Background tasks for recordings"""
from django.utils import timezone
from celery import shared_task
from celery.exceptions import Retry, MaxRetriesExceededError
import logging
from pathlib import Path

from .models import Recording
from .services.service_factory import SpeechRecognitionServiceFactory
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
        
        # Создать сервис распознавания речи
        # Для Vosk создаем сервис с model_id, для других - без параметров
        if recording.recognition_service == 'vosk':
            from .services.vosk_service import VoskService
            if recording.vosk_model:
                recognition_service = VoskService(model_id=recording.vosk_model)
            else:
                recognition_service = VoskService()  # Использует модель по умолчанию
        else:
            recognition_service = SpeechRecognitionServiceFactory.get_service(
                recording.recognition_service or 'faster-whisper',
                device='cpu'
            )
        
        # Распознать речь
        result = recognition_service.transcribe_file(
            audio_path,
            model_size=recording.whisper_model or 'base' if recording.recognition_service != 'vosk' else 'base',
            language=recording.user.settings.language
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
