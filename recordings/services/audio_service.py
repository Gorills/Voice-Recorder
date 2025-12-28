"""Service for audio file processing"""
import os
import soundfile as sf
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class AudioService:
    """Service for audio file operations"""
    
    @staticmethod
    def get_audio_info(file_path: Path) -> dict:
        """Get audio file information"""
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        
        # Для webm/opus файлов из браузера - использовать базовую информацию
        if file_path.suffix.lower() in ['.webm', '.opus']:
            # Whisper может обработать эти форматы, но soundfile не всегда может
            # Возвращаем базовую информацию
            return {
                'duration': None,  # Будет определено при обработке Whisper
                'sample_rate': None,
                'channels': None,
                'format': file_path.suffix.lower(),
                'file_size': file_size,
            }
        
        # Для других форматов - использовать soundfile
        try:
            with sf.SoundFile(str(file_path)) as f:
                duration = len(f) / f.samplerate
                sample_rate = f.samplerate
                channels = f.channels
                format_type = f.format
                
            return {
                'duration': duration,
                'sample_rate': sample_rate,
                'channels': channels,
                'format': format_type,
                'file_size': file_size,
            }
        except Exception as e:
            logger.warning(f"Не удалось получить полную информацию об аудио {file_path}: {e}")
            # Возвращаем хотя бы размер файла
            return {
                'duration': None,
                'sample_rate': None,
                'channels': None,
                'format': file_path.suffix.lower(),
                'file_size': file_size,
            }
    
    @staticmethod
    def is_valid_audio_file(file_path: Path) -> bool:
        """Check if file is a valid audio file"""
        # Проверить расширение файла
        valid_extensions = ['.wav', '.mp3', '.m4a', '.flac', '.ogg', '.wma', '.webm', '.opus']
        if file_path.suffix.lower() not in valid_extensions:
            logger.warning(f"Неподдерживаемое расширение файла: {file_path.suffix}")
            # Для webm/opus файлов из браузера - разрешить без проверки soundfile
            if file_path.suffix.lower() in ['.webm', '.opus']:
                return os.path.exists(file_path) and os.path.getsize(file_path) > 0
        
        # Для других форматов - проверка через soundfile
        try:
            with sf.SoundFile(str(file_path)) as f:
                return True
        except Exception as e:
            logger.warning(f"Ошибка проверки аудио файла {file_path}: {e}")
            # Если soundfile не может прочитать, но файл существует и имеет правильное расширение - разрешить
            if file_path.suffix.lower() in ['.webm', '.opus', '.mp3', '.m4a']:
                return os.path.exists(file_path) and os.path.getsize(file_path) > 0
            return False
    
    @staticmethod
    def get_supported_formats():
        """Get list of supported audio formats"""
        return ['.wav', '.mp3', '.m4a', '.flac', '.ogg', '.wma', '.webm', '.opus']

