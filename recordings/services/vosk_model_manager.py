"""
Утилита для управления моделями Vosk
Поддерживает модели из settings и автоматическое сканирование директории
"""
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

# Кеш для списка моделей
_models_cache = None


def get_vosk_models_dir() -> Path:
    """Получить путь к директории с моделями Vosk"""
    models_dir = getattr(settings, 'VOSK_MODELS_DIR', '/app/vosk-models')
    return Path(models_dir)


def get_model_full_path(model_path: str) -> Path:
    """
    Получить полный путь к модели
    
    Args:
        model_path: Относительный или абсолютный путь к модели
    
    Returns:
        Path: Полный путь к модели
    """
    models_dir = get_vosk_models_dir()
    
    # Если путь абсолютный, использовать его
    if os.path.isabs(model_path):
        return Path(model_path)
    
    # Иначе объединить с базовой директорией
    return models_dir / model_path


def is_valid_vosk_model(model_path: Path) -> bool:
    """
    Проверить, является ли директория валидной моделью Vosk
    
    Модель Vosk должна содержать файлы:
    - am/final.mdl (или другие файлы в am/)
    - graph/
    - conf/mfcc.conf
    
    Args:
        model_path: Путь к директории модели
    
    Returns:
        bool: True если это валидная модель Vosk
    """
    if not model_path.exists() or not model_path.is_dir():
        return False
    
    # Проверяем наличие ключевых файлов/директорий
    required_items = [
        model_path / 'graph',
        model_path / 'conf',
    ]
    
    # Хотя бы один из этих элементов должен существовать
    has_am = (model_path / 'am').exists()
    has_graph = (model_path / 'graph').exists()
    has_conf = (model_path / 'conf').exists()
    
    return has_graph or has_conf or has_am


def scan_directory_for_models() -> Dict[str, Dict]:
    """
    Сканировать директорию моделей и найти доступные модели
    
    Returns:
        Dict: Словарь найденных моделей {model_id: model_info}
    """
    models_dir = get_vosk_models_dir()
    found_models = {}
    
    if not models_dir.exists():
        logger.warning(f"Директория моделей Vosk не найдена: {models_dir}")
        return found_models
    
    # Сканируем поддиректории
    try:
        for item in models_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                if is_valid_vosk_model(item):
                    # Используем имя директории как идентификатор
                    model_id = item.name
                    # Извлекаем информацию из имени (опционально)
                    found_models[model_id] = {
                        'name': f'Vosk Model ({model_id})',
                        'path': item.name,  # Относительный путь
                        'size': 'Unknown',
                        'description': f'Автоматически обнаруженная модель: {model_id}',
                        'language': 'ru',  # По умолчанию
                        'recommended': False,
                        'auto_detected': True,  # Флаг автоматического обнаружения
                    }
                    logger.info(f"Обнаружена модель Vosk: {model_id} в {item}")
    except Exception as e:
        logger.error(f"Ошибка при сканировании директории моделей: {e}")
    
    return found_models


def get_all_available_models() -> Dict[str, Dict]:
    """
    Получить все доступные модели Vosk (из settings + автоматическое сканирование)
    
    Returns:
        Dict: Словарь всех доступных моделей {model_id: model_info}
    """
    global _models_cache
    
    # Используем кеш если доступен
    if _models_cache is not None:
        return _models_cache
    
    all_models = {}
    
    # 1. Получить модели из settings
    configured_models = getattr(settings, 'VOSK_MODELS', {})
    for model_id, model_info in configured_models.items():
        # Преобразовать путь в полный путь для проверки
        full_path = get_model_full_path(model_info['path'])
        if is_valid_vosk_model(full_path):
            all_models[model_id] = model_info.copy()
            all_models[model_id]['auto_detected'] = False
        else:
            logger.warning(f"Модель {model_id} из settings не найдена: {full_path}")
    
    # 2. Сканировать директорию для дополнительных моделей
    scanned_models = scan_directory_for_models()
    for model_id, model_info in scanned_models.items():
        # Добавляем только если модель не была уже в settings
        if model_id not in all_models:
            all_models[model_id] = model_info
    
    # Кешируем результат
    _models_cache = all_models
    
    return all_models


def get_model_path(model_id: str) -> Optional[Path]:
    """
    Получить полный путь к модели по идентификатору
    
    Args:
        model_id: Идентификатор модели (например, 'small-ru-0.22')
    
    Returns:
        Path: Полный путь к модели или None если не найдена
    """
    all_models = get_all_available_models()
    
    if model_id not in all_models:
        logger.error(f"Модель Vosk не найдена: {model_id}")
        return None
    
    model_info = all_models[model_id]
    full_path = get_model_full_path(model_info['path'])
    
    if not is_valid_vosk_model(full_path):
        logger.error(f"Модель {model_id} найдена в конфигурации, но не существует: {full_path}")
        return None
    
    return full_path


def get_model_choices() -> List[tuple]:
    """
    Получить список choices для использования в формах Django
    
    Returns:
        List[tuple]: Список кортежей (model_id, display_name)
    """
    all_models = get_all_available_models()
    choices = []
    
    # Сначала добавляем рекомендуемые модели
    recommended = [(mid, info) for mid, info in all_models.items() if info.get('recommended', False)]
    recommended.sort(key=lambda x: x[0])
    
    for model_id, model_info in recommended:
        name = model_info['name']
        size = model_info.get('size', '')
        display = f"{name} ({size})" if size else name
        choices.append((model_id, display))
    
    # Затем остальные
    others = [(mid, info) for mid, info in all_models.items() if not info.get('recommended', False)]
    others.sort(key=lambda x: x[0])
    
    for model_id, model_info in others:
        name = model_info['name']
        size = model_info.get('size', '')
        display = f"{name} ({size})" if size else name
        choices.append((model_id, display))
    
    return choices


def get_model_info(model_id: str) -> Optional[Dict]:
    """
    Получить информацию о модели по идентификатору
    
    Args:
        model_id: Идентификатор модели
    
    Returns:
        Dict: Информация о модели или None
    """
    all_models = get_all_available_models()
    return all_models.get(model_id)


def clear_cache():
    """Очистить кеш моделей (полезно для тестирования или после изменения моделей)"""
    global _models_cache
    _models_cache = None

