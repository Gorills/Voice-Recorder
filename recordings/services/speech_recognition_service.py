"""Base interface for speech recognition services"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List


class SpeechRecognitionService(ABC):
    """Abstract base class for speech recognition services"""
    
    @abstractmethod
    def transcribe_file(self, audio_path: Path, model_size: str = 'base', language: str = 'ru') -> Dict:
        """
        Transcribe audio file
        
        Args:
            audio_path: Path to audio file
            model_size: Model size/name
            language: Language code (default: 'ru')
        
        Returns:
            Dictionary with keys:
                - 'text': Transcribed text
                - 'language': Detected language
                - 'segments': List of segments (optional)
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available model sizes/names"""
        pass
    
    @abstractmethod
    def get_service_name(self) -> str:
        """Get human-readable service name"""
        pass

