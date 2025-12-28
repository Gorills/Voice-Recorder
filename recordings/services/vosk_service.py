"""Service for speech recognition using Vosk (offline, fast recognition)"""
try:
    from vosk import Model, KaldiRecognizer
    import json
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    Model = None
    KaldiRecognizer = None

from pathlib import Path
from typing import Dict, List
import logging
import wave
import subprocess
import os

from .speech_recognition_service import SpeechRecognitionService

logger = logging.getLogger(__name__)


class VoskService(SpeechRecognitionService):
    """Service for speech recognition using Vosk (offline, fast)"""
    
    _models = {}  # Cache для моделей
    
    def __init__(self, model_id: str = None, model_path: str = None):
        """
        Initialize VoskService
        
        Args:
            model_id: Идентификатор модели Vosk (например, 'small-ru-0.22')
            model_path: Прямой путь к модели (устаревший способ, используется если model_id не указан)
        """
        if not VOSK_AVAILABLE:
            raise ImportError(
                "vosk is not installed. Install it with: pip install vosk"
            )
        
        # Если указан model_id, используем его для получения пути
        if model_id:
            from .vosk_model_manager import get_model_path
            model_full_path = get_model_path(model_id)
            if model_full_path:
                self.model_path = str(model_full_path)
                self.model_id = model_id
            else:
                raise ValueError(f"Модель Vosk '{model_id}' не найдена или недоступна")
        elif model_path:
            # Устаревший способ - прямой путь
            self.model_path = model_path
            self.model_id = None
            logger.warning("Использование model_path устарело, рекомендуется использовать model_id")
        else:
            # Попытка найти модель по умолчанию
            self.model_path = self._get_default_model_path()
            self.model_id = None
    
    def _get_default_model_path(self) -> str:
        """Get default model path (устаревший метод, рекомендуется использовать model_id)"""
        from .vosk_model_manager import get_all_available_models, get_model_path
        
        # Пробуем найти рекомендуемую модель
        all_models = get_all_available_models()
        for model_id, model_info in all_models.items():
            if model_info.get('recommended', False):
                model_path = get_model_path(model_id)
                if model_path:
                    logger.info(f"Используется рекомендуемая модель Vosk: {model_id}")
                    return str(model_path)
        
        # Если рекомендуемой нет, берем первую доступную
        if all_models:
            first_model_id = list(all_models.keys())[0]
            model_path = get_model_path(first_model_id)
            if model_path:
                logger.info(f"Используется первая доступная модель Vosk: {first_model_id}")
                return str(model_path)
        
        # Если ничего не найдено, возвращаем путь по умолчанию
        default_path = '/app/vosk-models/vosk-model-ru-0.22'
        logger.warning(f"Модель Vosk не найдена, используется путь по умолчанию: {default_path}")
        return default_path
    
    def load_model(self):
        """
        Load Vosk model (with caching)
        
        Note: Vosk uses its own model files, not Whisper model sizes.
        Models must be downloaded separately from https://alphacephei.com/vosk/models
        """
        # Используем model_id для кеширования если доступен
        cache_key = f"{self.model_id}_{self.model_path}" if self.model_id else f"{self.model_path}"
        
        if cache_key not in self._models:
            try:
                if not os.path.exists(self.model_path):
                    raise FileNotFoundError(
                        f"Модель Vosk не найдена по пути: {self.model_path}. "
                        f"Пожалуйста, скачайте модель с https://alphacephei.com/vosk/models"
                    )
                
                logger.info(f"Загрузка модели Vosk: {self.model_path}")
                model = Model(self.model_path)
                self._models[cache_key] = model
                logger.info(f"Модель Vosk успешно загружена")
            except Exception as e:
                logger.error(f"Ошибка при загрузке модели Vosk: {e}")
                raise Exception(f"Ошибка при загрузке модели Vosk: {e}")
        
        return self._models[cache_key]
    
    def _convert_to_wav(self, audio_path: Path, sample_rate: int = 16000) -> Path:
        """
        Convert audio file to WAV format with 16kHz sample rate
        Оптимизировано для качества и скорости распознавания Vosk
        """
        output_path = audio_path.parent / f"{audio_path.stem}_converted.wav"
        
        try:
            # Используем ffmpeg для конвертации с оптимизацией для распознавания речи
            # -ar 16000: частота дискретизации 16kHz (оптимально для Vosk)
            # -ac 1: моно (стерео не нужно для распознавания речи)
            # -sample_fmt s16: 16-bit PCM (оптимальный формат для Vosk)
            # -af 'highpass=f=80,lowpass=f=8000,volume=1.2': фильтры для улучшения качества речи
            #    highpass убирает низкочастотные шумы (< 80Hz)
            #    lowpass убирает высокочастотные шумы (> 8kHz, не важны для речи)
            #    volume=1.2: легкое увеличение громкости для лучшего распознавания
            cmd = [
                'ffmpeg', '-i', str(audio_path),
                '-ar', str(sample_rate),
                '-ac', '1',  # Моно
                '-sample_fmt', 's16',  # 16-bit PCM
                '-af', 'highpass=f=80,lowpass=f=8000,volume=1.2',  # Фильтры и нормализация
                '-y',  # Перезаписать если существует
                str(output_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                raise Exception(f"Ошибка конвертации аудио: {result.stderr}")
            
            return output_path
        except subprocess.TimeoutExpired:
            raise Exception("Конвертация аудио превысила лимит времени")
        except FileNotFoundError:
            raise Exception("ffmpeg не найден. Установите ffmpeg для работы с аудио")
    
    def transcribe_file(self, audio_path: Path, model_size: str = 'base', language: str = 'ru') -> Dict:
        """
        Transcribe audio file using Vosk
        
        Note: model_size parameter is ignored for Vosk, as Vosk uses its own model files.
        The model is determined by the model_path set during initialization.
        """
        try:
            # Vosk doesn't use model_size parameter - it uses the model_path set during initialization
            model = self.load_model()
            
            logger.info(f"Начало распознавания (Vosk): {audio_path}, модель: {self.model_path} (model_size параметр '{model_size}' игнорируется для Vosk)")
            
            # Vosk работает только с WAV файлами в формате 16kHz, моно
            # Конвертируем если нужно
            wav_path = audio_path
            converted = False
            
            if audio_path.suffix.lower() != '.wav':
                logger.info(f"Конвертация аудио файла в WAV формат...")
                wav_path = self._convert_to_wav(audio_path)
                converted = True
            
            # Проверяем формат WAV файла
            try:
                wf = wave.open(str(wav_path), "rb")
                sample_rate = wf.getframerate()
                channels = wf.getnchannels()
                wf.close()
                
                # Если не 16kHz моно, конвертируем
                if sample_rate != 16000 or channels != 1:
                    logger.info(f"Конвертация WAV файла: {sample_rate}Hz, {channels} каналов -> 16kHz моно")
                    wav_path = self._convert_to_wav(wav_path, sample_rate=16000)
                    converted = True
            except Exception as e:
                logger.warning(f"Не удалось прочитать WAV файл, пробуем конвертировать: {e}")
                wav_path = self._convert_to_wav(audio_path)
                converted = True
            
            # Инициализируем распознаватель с оптимизированными параметрами
            # Vosk работает с 16kHz моно WAV
            rec = KaldiRecognizer(model, 16000)
            
            # Оптимизация для качества и скорости
            rec.SetWords(True)  # Включить информацию о словах для временных меток
            # SetPartialWords можно использовать для частичных результатов, но это замедляет обработку
            # rec.SetPartialWords(True)  # Отключено для скорости
            
            # Попытка установить максимальное количество альтернатив для улучшения качества
            # SetMaxAlternatives(0) = использовать лучший результат (быстрее, оптимальный баланс)
            try:
                if hasattr(rec, 'SetMaxAlternatives'):
                    rec.SetMaxAlternatives(0)  # 0 = лучший результат, быстрее
                    logger.debug("SetMaxAlternatives установлен для оптимизации")
            except Exception:
                pass  # Метод может быть недоступен в некоторых версиях Vosk
            
            # Читаем и обрабатываем аудио
            # Оптимизированный размер буфера: 8000 байт (4000 фреймов * 2 байта на сэмпл)
            # Больший буфер может ускорить обработку, но требует больше памяти
            # 4000 фреймов = 0.25 секунды при 16kHz - оптимальный баланс
            wf = wave.open(str(wav_path), "rb")
            buffer_size = 4000  # Количество фреймов за раз (оптимально для скорости)
            
            text_parts = []
            segments = []
            
            while True:
                data = wf.readframes(buffer_size)
                if len(data) == 0:
                    break
                
                if rec.AcceptWaveform(data):
                    # AcceptWaveform вернул True - получили финальный фрагмент
                    result_str = rec.Result()
                    result = json.loads(result_str)
                    # Пробуем получить текст из 'text' или собрать из 'result'
                    text = None
                    if result.get('text'):
                        text = result['text'].strip()
                    elif result.get('result') and len(result['result']) > 0:
                        # Собираем текст из слов
                        words = [word.get('word', '') for word in result['result'] if word.get('word')]
                        text = ' '.join(words).strip()
                    
                    if text:
                        text_parts.append(text)
                        logger.debug(f"Добавлен текст из AcceptWaveform: '{text}'")
                        # Сегмент с временными метками
                        if result.get('result') and len(result['result']) > 0:
                            segments.append({
                                'start': result['result'][0].get('start', 0),
                                'end': result['result'][-1].get('end', 0),
                                'text': text
                            })
            
            # Получаем финальный результат - это важно, так как последний фрагмент может быть только в FinalResult
            final_result_str = rec.FinalResult()
            final_result = json.loads(final_result_str)
            # Пробуем получить текст из 'text' или собрать из 'result'
            final_text = None
            if final_result.get('text'):
                final_text = final_result['text'].strip()
            elif final_result.get('result') and len(final_result['result']) > 0:
                # Собираем текст из слов
                words = [word.get('word', '') for word in final_result['result'] if word.get('word')]
                final_text = ' '.join(words).strip()
            
            if final_text:
                text_parts.append(final_text)
                logger.debug(f"Добавлен текст из FinalResult: '{final_text}'")
                if final_result.get('result') and len(final_result['result']) > 0:
                    segments.append({
                        'start': final_result['result'][0].get('start', 0),
                        'end': final_result['result'][-1].get('end', 0),
                        'text': final_text
                    })
            
            wf.close()
            
            # Удаляем временный файл если был создан
            if converted and wav_path != audio_path and wav_path.exists():
                try:
                    wav_path.unlink()
                except Exception as e:
                    logger.warning(f"Не удалось удалить временный файл {wav_path}: {e}")
            
            text = ' '.join(text_parts).strip()
            
            logger.info(f"Распознавание завершено: {len(text)} символов")
            
            return {
                'text': text,
                'language': language,
                'segments': segments if segments else None,
            }
        except Exception as e:
            logger.error(f"Ошибка при распознавании (Vosk): {e}")
            raise Exception(f"Ошибка при распознавании (Vosk): {e}")
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available Vosk model identifiers
        
        Returns:
            List[str]: Список идентификаторов доступных моделей
        """
        from .vosk_model_manager import get_all_available_models
        all_models = get_all_available_models()
        return list(all_models.keys())
    
    def get_service_name(self) -> str:
        """Get human-readable service name"""
        return "Vosk (Offline, Fast)"

