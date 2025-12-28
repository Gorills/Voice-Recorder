"""Service for Whisper speech recognition"""
import whisper
import numpy as np
import torch
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class WhisperService:
    """Service for speech recognition using Whisper"""
    
    _models = {}  # Cache для моделей
    
    def __init__(self):
        self.device = "cpu"  # Используем CPU для избежания проблем с CUDA
    
    def load_model(self, model_size: str = 'base'):
        """Load Whisper model (with caching)"""
        if model_size not in self._models:
            try:
                logger.info(f"Загрузка модели Whisper: {model_size}")
                model = whisper.load_model(model_size, device=self.device)
                self._models[model_size] = model
                logger.info(f"Модель {model_size} успешно загружена")
            except Exception as e:
                logger.error(f"Ошибка при загрузке модели {model_size}: {e}")
                raise Exception(f"Ошибка при загрузке модели Whisper: {e}")
        
        return self._models[model_size]
    
    def transcribe_file(self, audio_path: Path, model_size: str = 'base', language: str = 'ru') -> dict:
        """Transcribe audio file"""
        try:
            model = self.load_model(model_size)
            
            logger.info(f"Начало распознавания: {audio_path}, модель: {model_size}")
            result = model.transcribe(
                str(audio_path),
                language=language,
                task="transcribe"
            )
            
            text = result.get("text", "").strip()
            language_detected = result.get("language", language)
            
            logger.info(f"Распознавание завершено: {len(text)} символов")
            
            return {
                'text': text,
                'language': language_detected,
                'segments': result.get('segments', []),
            }
        except Exception as e:
            logger.error(f"Ошибка при распознавании: {e}")
            raise Exception(f"Ошибка при распознавании: {e}")
    
    def get_available_models(self):
        """Get list of available Whisper models"""
        return ['tiny', 'base', 'small', 'medium', 'large']

