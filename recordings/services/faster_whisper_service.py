"""Service for speech recognition using faster-whisper (CTranslate2)"""
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    WhisperModel = None

from pathlib import Path
from typing import Dict, List
import logging

from .speech_recognition_service import SpeechRecognitionService

logger = logging.getLogger(__name__)


class FasterWhisperService(SpeechRecognitionService):
    """Service for speech recognition using faster-whisper (much faster than openai-whisper)"""
    
    _models = {}  # Cache для моделей
    
    def __init__(self, device: str = "cpu", compute_type: str = "int8"):
        """
        Initialize FasterWhisperService
        
        Args:
            device: Device to use ("cpu" or "cuda")
            compute_type: Compute type ("int8", "int8_float16", "int16", "float16", "float32")
        """
        if not FASTER_WHISPER_AVAILABLE:
            raise ImportError(
                "faster-whisper is not installed. Install it with: pip install faster-whisper"
            )
        
        self.device = device
        self.compute_type = compute_type
    
    def load_model(self, model_size: str = 'base'):
        """Load Whisper model (with caching)"""
        cache_key = f"{model_size}_{self.device}_{self.compute_type}"
        
        if cache_key not in self._models:
            try:
                logger.info(f"Загрузка модели faster-whisper: {model_size} (device={self.device}, compute_type={self.compute_type})")
                
                # Оптимизация для CPU: используем все доступные ядра для обработки
                model_kwargs = {
                    'model_size_or_path': model_size,
                    'device': self.device,
                    'compute_type': self.compute_type,
                }
                
                # Для CPU оптимизируем использование потоков
                if self.device == 'cpu':
                    import os
                    # Используем все доступные CPU ядра, но не более 4 для оптимального баланса
                    cpu_count = min(os.cpu_count() or 2, 4)
                    model_kwargs['cpu_threads'] = cpu_count
                    model_kwargs['num_workers'] = 1  # Для CPU лучше использовать 1 worker
                    logger.info(f"Использование {cpu_count} CPU потоков для обработки")
                
                model = WhisperModel(**model_kwargs)
                self._models[cache_key] = model
                logger.info(f"Модель {model_size} успешно загружена")
            except Exception as e:
                logger.error(f"Ошибка при загрузке модели {model_size}: {e}")
                raise Exception(f"Ошибка при загрузке модели faster-whisper: {e}")
        
        return self._models[cache_key]
    
    def transcribe_file(self, audio_path: Path, model_size: str = 'base', language: str = 'ru') -> Dict:
        """Transcribe audio file"""
        try:
            model = self.load_model(model_size)
            
            logger.info(f"Начало распознавания (faster-whisper): {audio_path}, модель: {model_size}")
            
            # faster-whisper использует другой API
            # Оптимизация для CPU: уменьшаем beam_size для ускорения
            # beam_size=1 (greedy decoding) - самый быстрый, но может быть немного менее точным
            # beam_size=2-3 - баланс между скоростью и качеством
            beam_size = 1 if self.device == 'cpu' else 5
            
            # Параметры для transcribe
            transcribe_params = {
                'language': language if language else None,
                'beam_size': beam_size,
                'vad_filter': True,  # Фильтр голосовой активности - ускоряет обработку, пропуская тишину
            }
            
            # Для CPU также используем дополнительные параметры оптимизации
            if self.device == 'cpu':
                transcribe_params['vad_parameters'] = dict(
                    min_silence_duration_ms=100,  # Минимальная длительность тишины
                    threshold=0.5,  # Порог для определения тишины
                )
                # Дополнительные параметры для ускорения
                transcribe_params['patience'] = 1.0  # По умолчанию 1.0
                transcribe_params['condition_on_previous_text'] = False  # Отключаем условие на предыдущий текст - ускоряет обработку
                transcribe_params['compression_ratio_threshold'] = 2.4  # Порог компрессии для определения повторов
                transcribe_params['log_prob_threshold'] = -1.0  # Порог вероятности для отсеивания некачественных результатов
            
            segments, info = model.transcribe(str(audio_path), **transcribe_params)
            
            # Собрать текст из сегментов
            text_parts = []
            segments_list = []
            for segment in segments:
                text_parts.append(segment.text)
                segments_list.append({
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text
                })
            
            text = " ".join(text_parts).strip()
            language_detected = info.language if hasattr(info, 'language') else language
            
            logger.info(f"Распознавание завершено: {len(text)} символов")
            
            return {
                'text': text,
                'language': language_detected,
                'segments': segments_list,
            }
        except Exception as e:
            logger.error(f"Ошибка при распознавании: {e}")
            raise Exception(f"Ошибка при распознавании (faster-whisper): {e}")
    
    def get_available_models(self) -> List[str]:
        """Get list of available Whisper models"""
        return ['tiny', 'tiny.en', 'base', 'base.en', 'small', 'small.en', 'medium', 'medium.en', 'large-v1', 'large-v2', 'large-v3', 'large']
    
    def get_service_name(self) -> str:
        """Get human-readable service name"""
        return "Faster-Whisper (CTranslate2)"

