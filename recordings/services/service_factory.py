"""Factory for creating speech recognition services"""
import logging
from typing import Optional
from pathlib import Path

from .speech_recognition_service import SpeechRecognitionService
from .whisper_service import WhisperService

logger = logging.getLogger(__name__)


class SpeechRecognitionServiceFactory:
    """Factory class for creating speech recognition services"""
    
    @staticmethod
    def get_service(service_name: str, device: str = 'cpu') -> SpeechRecognitionService:
        """
        Returns an instance of the requested speech recognition service.
        
        Args:
            service_name: The name of the service to retrieve (e.g., 'whisper', 'faster-whisper', 'vosk').
            device: Device to use ('cpu', 'cuda')
        
        Returns:
            An instance of a class inheriting from SpeechRecognitionService.
        
        Raises:
            ValueError: If an unknown service_name is requested.
        """
        if service_name == 'whisper':
            return WhisperService()
        elif service_name == 'faster-whisper':
            try:
                from .faster_whisper_service import FasterWhisperService
                # Для CPU используем int8 для лучшей производительности
                compute_type = 'int8' if device == 'cpu' else 'float16'
                return FasterWhisperService(device=device, compute_type=compute_type)
            except ImportError:
                logger.warning("faster-whisper не установлен, используем обычный Whisper")
                return WhisperService()
        elif service_name == 'vosk':
            try:
                from .vosk_service import VoskService
                # VoskService теперь принимает model_id, но пока оставляем без параметров
                # для обратной совместимости. model_id будет установлен при вызове transcribe_file
                return VoskService()
            except ImportError:
                logger.warning("vosk не установлен, используем обычный Whisper")
                return WhisperService()
            except Exception as e:
                logger.warning(f"Ошибка инициализации Vosk: {e}, используем обычный Whisper")
                return WhisperService()
        else:
            logger.error(f"Неизвестная служба распознавания: {service_name}")
            raise ValueError(f"Неизвестная служба распознавания: {service_name}")


def create_speech_recognition_service(service_type: str = 'whisper', device: str = 'cpu') -> SpeechRecognitionService:
    """
    Create speech recognition service instance (legacy function, use SpeechRecognitionServiceFactory.get_service)
    
    Args:
        service_type: Type of service ('whisper', 'faster-whisper', 'vosk')
        device: Device to use ('cpu', 'cuda')
    
    Returns:
        SpeechRecognitionService instance
    """
    return SpeechRecognitionServiceFactory.get_service(service_type, device)

