"""Models for recordings app"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import os


def audio_upload_path(instance, filename):
    """Generate upload path for audio files"""
    return f'audio/{instance.user.id}/{filename}'


class Recording(models.Model):
    """Audio recording model"""
    WHISPER_MODEL_CHOICES = [
        ('tiny', 'Tiny - Самая быстрая (~75 MB)'),
        ('base', 'Base - Баланс (~150 MB)'),
        ('small', 'Small - Хорошее качество (~500 MB)'),
        ('medium', 'Medium - Высокое качество (~1.5 GB)'),
        ('large', 'Large - Наилучшее качество (~3 GB)'),
    ]
    
    STATUS_CHOICES = [
        ('uploaded', 'Загружено'),
        ('processing', 'Обработка'),
        ('completed', 'Завершено'),
        ('failed', 'Ошибка'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recordings')
    title = models.CharField(max_length=200, default='Без названия')
    audio_file = models.FileField(upload_to=audio_upload_path)
    whisper_model = models.CharField(max_length=10, choices=WHISPER_MODEL_CHOICES, default='base')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    transcription = models.TextField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True, help_text='Длительность в секундах')
    celery_task_id = models.CharField(max_length=255, blank=True, null=True, help_text='ID задачи Celery для отмены')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Запись'
        verbose_name_plural = 'Записи'
    
    def __str__(self):
        return f"{self.title} ({self.user.username})"
    
    def get_file_size(self):
        """Get file size in MB"""
        if self.audio_file:
            try:
                size = self.audio_file.size
                return round(size / (1024 * 1024), 2)
            except:
                return 0
        return 0
    
    def get_file_name(self):
        """Get original file name"""
        if self.audio_file:
            return os.path.basename(self.audio_file.name)
        return ''
    
    def get_duration_display(self):
        """Get formatted duration as MM:SS or SS сек"""
        if not self.duration:
            return None
        duration_int = int(self.duration)
        if duration_int >= 60:
            minutes = duration_int // 60
            seconds = duration_int % 60
            return f"{minutes}:{seconds:02d}"
        else:
            return f"{duration_int} сек"
    
    def delete(self, *args, **kwargs):
        """Delete file when recording is deleted"""
        if self.audio_file:
            if os.path.isfile(self.audio_file.path):
                os.remove(self.audio_file.path)
        super().delete(*args, **kwargs)


class UserSettings(models.Model):
    """User preferences and settings"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    default_whisper_model = models.CharField(
        max_length=10,
        choices=Recording.WHISPER_MODEL_CHOICES,
        default='base',
        verbose_name='Модель Whisper по умолчанию'
    )
    auto_transcribe = models.BooleanField(
        default=False,
        verbose_name='Автоматически распознавать после загрузки'
    )
    language = models.CharField(
        max_length=10,
        default='ru',
        verbose_name='Язык распознавания'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Настройки пользователя'
        verbose_name_plural = 'Настройки пользователей'
    
    def __str__(self):
        return f"Настройки {self.user.username}"

