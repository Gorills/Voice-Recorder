"""Views for recordings app"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from django.conf import settings
import os
import logging
from pathlib import Path

from .models import Recording, UserSettings
from .forms import RecordingForm, UserSettingsForm
from .services.audio_service import AudioService
from .tasks import transcribe_recording_task

logger = logging.getLogger(__name__)


def register_view(request):
    """User registration"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                # Создать настройки по умолчанию
                UserSettings.objects.get_or_create(user=user)
                messages.success(request, f'Добро пожаловать, {username}!')
                return redirect('dashboard')
    else:
        form = UserCreationForm()
    
    return render(request, 'recordings/register.html', {'form': form})


def login_view(request):
    """User login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, f'Добро пожаловать, {username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
    
    return render(request, 'recordings/login.html')


@login_required
def dashboard_view(request):
    """Main dashboard"""
    user_settings, _ = UserSettings.objects.get_or_create(user=request.user)
    
    # Статистика
    total_recordings = Recording.objects.filter(user=request.user).count()
    completed_recordings = Recording.objects.filter(user=request.user, status='completed').count()
    processing_recordings = Recording.objects.filter(user=request.user, status__in=['processing', 'uploaded']).count()
    
    # Последние записи (упорядочить по дате создания)
    recent_recordings = Recording.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    # Логирование для отладки
    logger.info(f"Дашборд для пользователя {request.user.username}: всего={total_recordings}, завершено={completed_recordings}, обработка={processing_recordings}, недавних={recent_recordings.count()}")
    for rec in recent_recordings:
        logger.debug(f"  Запись {rec.id}: {rec.title}, статус={rec.status}, файл={rec.audio_file.name if rec.audio_file else 'нет'}")
    
    # Получить доступные модели Vosk для шаблона
    from .services.vosk_model_manager import get_all_available_models
    vosk_models = get_all_available_models()
    
    context = {
        'user_settings': user_settings,
        'total_recordings': total_recordings,
        'completed_recordings': completed_recordings,
        'processing_recordings': processing_recordings,
        'recent_recordings': recent_recordings,
        'vosk_models': vosk_models,
    }
    
    return render(request, 'recordings/dashboard.html', context)


@login_required
def dashboard_status_api(request):
    """API для получения статуса записей для реактивного обновления"""
    from django.core import serializers
    from django.http import JsonResponse
    
    # Статистика
    total_recordings = Recording.objects.filter(user=request.user).count()
    completed_recordings = Recording.objects.filter(user=request.user, status='completed').count()
    processing_recordings = Recording.objects.filter(user=request.user, status__in=['processing', 'uploaded']).count()
    
    # Последние записи с их статусами
    recent_recordings = Recording.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    recordings_data = []
    for rec in recent_recordings:
        recordings_data.append({
            'id': rec.id,
            'title': rec.title,
            'status': rec.status,
            'status_display': rec.get_status_display(),
            'created_at': rec.created_at.isoformat(),
            'processed_at': rec.processed_at.isoformat() if rec.processed_at else None,
            'has_transcription': bool(rec.transcription),
        })
    
    return JsonResponse({
        'total_recordings': total_recordings,
        'completed_recordings': completed_recordings,
        'processing_recordings': processing_recordings,
        'recordings': recordings_data,
    })


@login_required
def recording_status_api(request, recording_id):
    """API для получения статуса конкретной записи"""
    from django.http import JsonResponse
    
    recording = get_object_or_404(Recording, pk=recording_id, user=request.user)
    
    return JsonResponse({
        'id': recording.id,
        'title': recording.title,
        'status': recording.status,
        'status_display': recording.get_status_display(),
        'transcription': recording.transcription if recording.transcription else '',
        'error_message': recording.error_message if recording.error_message else '',
        'processed_at': recording.processed_at.isoformat() if recording.processed_at else None,
        'has_transcription': bool(recording.transcription),
    })


@login_required
def recordings_list_view(request):
    """List of all recordings"""
    recordings = Recording.objects.filter(user=request.user)
    
    # Поиск
    search_query = request.GET.get('search', '')
    if search_query:
        recordings = recordings.filter(
            Q(title__icontains=search_query) | 
            Q(transcription__icontains=search_query)
        )
    
    # Фильтр по статусу
    status_filter = request.GET.get('status', '')
    if status_filter:
        recordings = recordings.filter(status=status_filter)
    
    # Фильтр по модели
    model_filter = request.GET.get('model', '')
    if model_filter:
        recordings = recordings.filter(whisper_model=model_filter)
    
    # Сортировка
    sort_by = request.GET.get('sort', '-created_at')
    recordings = recordings.order_by(sort_by)
    
    # Пагинация
    paginator = Paginator(recordings, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'recordings': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'model_filter': model_filter,
        'sort_by': sort_by,
        'is_paginated': page_obj.has_other_pages(),
    }
    
    return render(request, 'recordings/recordings_list.html', context)


@login_required
def recording_detail_view(request, pk):
    """Recording detail view"""
    recording = get_object_or_404(Recording, pk=pk, user=request.user)
    
    context = {
        'recording': recording,
    }
    
    return render(request, 'recordings/recording_detail.html', context)


@login_required
@require_http_methods(["POST"])
def upload_recording_view(request):
    """Upload new recording"""
    # Проверка размера файла
    if 'audio_file' in request.FILES:
        audio_file = request.FILES['audio_file']
        max_size = getattr(settings, 'MAX_AUDIO_FILE_SIZE', 100 * 1024 * 1024)  # 100 MB по умолчанию
        # Проверить размер файла (может быть None для некоторых типов файлов)
        if hasattr(audio_file, 'size') and audio_file.size and audio_file.size > max_size:
            error_msg = f'Размер файла слишком большой. Максимальный размер: {max_size / (1024*1024):.0f} MB'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect('dashboard')
    
    # Получить настройки пользователя для установки значений по умолчанию
    user_settings, _ = UserSettings.objects.get_or_create(user=request.user)
    
    # Установить значения по умолчанию для формы, если не указаны в запросе
    form_data = request.POST.copy()
    if not form_data.get('recognition_service'):
        form_data['recognition_service'] = user_settings.default_recognition_service or 'faster-whisper'
    
    form = RecordingForm(form_data, request.FILES)
    
    if form.is_valid():
        recording = form.save(commit=False)
        recording.user = request.user
        
        # Если название не указано, сгенерировать автоматически
        if not recording.title or recording.title.strip() == '':
            from django.utils import timezone
            recording.title = f"Запись {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Убедиться, что recognition_service установлен
        if not recording.recognition_service:
            recording.recognition_service = user_settings.default_recognition_service or 'faster-whisper'
        
        # Получить модель из формы
        if recording.recognition_service == 'vosk':
            # Для Vosk используем vosk_model
            vosk_model = request.POST.get('vosk_model') or request.GET.get('vosk_model')
            if vosk_model:
                recording.vosk_model = vosk_model
            elif user_settings.default_vosk_model:
                # Используем модель по умолчанию из настроек
                recording.vosk_model = user_settings.default_vosk_model
            recording.whisper_model = None  # Очищаем whisper_model для Vosk
        else:
            # Для Whisper/Faster-Whisper используем whisper_model
            if not recording.whisper_model:
                recording.whisper_model = user_settings.default_whisper_model
            recording.vosk_model = None  # Очищаем vosk_model для не-Vosk
        
        # Получить длительность из формы, если передана
        duration_from_form = request.POST.get('duration')
        if duration_from_form:
            try:
                recording.duration = float(duration_from_form)
                logger.info(f"✅ Длительность из формы: {recording.duration} секунд")
            except (ValueError, TypeError) as e:
                logger.warning(f"⚠️ Не удалось преобразовать длительность '{duration_from_form}': {e}")
        else:
            logger.warning("⚠️ Длительность не передана в форме")
        
        # Сохранить запись в БД сначала (чтобы получить путь к файлу)
        # Это важно - файл должен быть сохранен на диск перед проверкой
        recording.save()
        logger.info(f"✅ Запись {recording.id} СОЗДАНА в БД: user={request.user.username}, title={recording.title}, file={recording.audio_file.name}")
        
        # Проверить файл и получить информацию
        audio_service = AudioService()
        try:
            # Проверить валидность файла
            if not audio_service.is_valid_audio_file(Path(recording.audio_file.path)):
                # Удалить запись если файл невалидный
                recording.delete()
                error_msg = 'Некорректный аудио файл'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': error_msg}, status=400)
                messages.error(request, error_msg)
                return redirect('recordings_list')
            
            # Получить информацию об аудио
            audio_info = audio_service.get_audio_info(Path(recording.audio_file.path))
            
            # Использовать длительность из формы, если передана (для webm файлов это более надежно)
            # Если длительность не была передана из формы, попытаться получить из файла
            if not recording.duration or recording.duration == 0:
                file_duration = audio_info.get('duration')
                if file_duration:
                    recording.duration = file_duration
            
            # Обновить запись с информацией об аудио
            recording.save()
            logger.info(f"✅ Запись {recording.id} УСПЕШНО СОХРАНЕНА в БД: title={recording.title}, file={recording.audio_file.name}, size={recording.get_file_size()}MB, duration={recording.duration}")
        except Exception as e:
            # Удалить запись при ошибке
            recording.delete()
            error_msg = f'Ошибка обработки файла: {str(e)}'
            logger.error(f"❌ Ошибка обработки аудио файла: {e}", exc_info=True)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect('recordings_list')
        
        # Автоматическое распознавание если включено
        if user_settings.auto_transcribe:
            task = transcribe_recording_task.delay(recording.id)
            recording.status = 'processing'
            recording.celery_task_id = task.id
            recording.save()
            success_message = 'Запись загружена. Распознавание начато.'
            logger.info(f"Запущено автоматическое распознавание для записи {recording.id}")
        else:
            success_message = 'Запись успешно загружена.'
        
        logger.info(f"✅✅✅ Запись {recording.id} ПОЛНОСТЬЮ ГОТОВА: user={recording.user.username}, title={recording.title}, status={recording.status}, file={recording.audio_file.name}")
        
        # Если это AJAX запрос, вернуть JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.urls import reverse
            response_data = {
                'success': True,
                'message': success_message,
                'recording_id': recording.id,
                'recording_title': recording.title,
                'auto_transcribe': user_settings.auto_transcribe
            }
            # Если автоматическое распознавание выключено, добавляем redirect_url
            if not user_settings.auto_transcribe:
                response_data['redirect_url'] = reverse('recording_detail', args=[recording.pk])
            return JsonResponse(response_data)
        
        messages.success(request, success_message)
        return redirect('recording_detail', pk=recording.pk)
    else:
        error_message = 'Ошибка при загрузке файла: ' + ', '.join([str(e) for e in form.errors.values()])
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_message}, status=400)
        messages.error(request, error_message)
        return redirect('recordings_list')


@login_required
@require_http_methods(["POST"])
def transcribe_recording_view(request, pk):
    """Start transcription for recording"""
    recording = get_object_or_404(Recording, pk=pk, user=request.user)
    
    if recording.status == 'processing':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Распознавание уже выполняется'}, status=400)
        messages.warning(request, 'Распознавание уже выполняется')
        return redirect('recording_detail', pk=recording.pk)
    
    # Получить библиотеку распознавания из запроса (если указана)
    recognition_service = request.POST.get('recognition_service') or request.GET.get('recognition_service')
    if recognition_service:
        valid_services = ['whisper', 'faster-whisper', 'vosk']
        if recognition_service in valid_services:
            recording.recognition_service = recognition_service
            logger.info(f"Использована библиотека {recognition_service} для повторного распознавания записи {recording.id}")
            # Для Vosk очищаем whisper_model
            if recognition_service == 'vosk':
                recording.whisper_model = None
    
    # Получить модель Whisper из запроса (если указана, и только для не-Vosk)
    if recording.recognition_service != 'vosk':
        whisper_model = request.POST.get('whisper_model') or request.GET.get('whisper_model')
        if whisper_model:
            # Проверить валидность модели
            valid_models = ['tiny', 'base', 'small', 'medium', 'large']
            if whisper_model in valid_models:
                recording.whisper_model = whisper_model
                logger.info(f"Использована модель {whisper_model} для повторного распознавания записи {recording.id}")
    
    if recognition_service:
        recording.save()
    
    # Запустить задачу распознавания
    task = transcribe_recording_task.delay(recording.id)
    recording.status = 'processing'
    recording.celery_task_id = task.id
    recording.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'Распознавание начато. Это может занять некоторое время.'
        })
    
    messages.success(request, 'Распознавание начато. Это может занять некоторое время.')
    return redirect('recording_detail', pk=recording.pk)


@login_required
@require_http_methods(["POST"])
def cancel_transcription_view(request, pk):
    """Cancel transcription task for recording"""
    from celery import current_app
    
    recording = get_object_or_404(Recording, pk=pk, user=request.user)
    
    # Если запись уже не в обработке, это не ошибка - возможно обработка уже завершилась
    if recording.status != 'processing':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True, 
                'message': 'Запись уже не находится в обработке.',
                'status': recording.status
            })
        messages.info(request, 'Запись уже не находится в обработке')
        return redirect('recording_detail', pk=recording.pk)
    
    # Отменить задачу Celery
    if recording.celery_task_id:
        try:
            current_app.control.revoke(recording.celery_task_id, terminate=True)
            logger.info(f"Задача {recording.celery_task_id} отменена для записи {recording.id}")
        except Exception as e:
            logger.warning(f"Не удалось отменить задачу {recording.celery_task_id}: {e}")
    
    # Изменить статус записи обратно на uploaded
    recording.status = 'uploaded'
    recording.celery_task_id = None
    recording.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'Обработка остановлена. Теперь вы можете запустить распознавание заново.',
            'status': 'uploaded'
        })
    
    messages.success(request, 'Обработка остановлена')
    return redirect('recording_detail', pk=recording.pk)


@login_required
def download_audio_view(request, pk):
    """Download audio file"""
    recording = get_object_or_404(Recording, pk=pk, user=request.user)
    
    if not recording.audio_file:
        raise Http404("Файл не найден")
    
    file_path = recording.audio_file.path
    if not os.path.exists(file_path):
        raise Http404("Файл не найден")
    
    return FileResponse(
        open(file_path, 'rb'),
        as_attachment=True,
        filename=recording.get_file_name()
    )


@login_required
def download_transcription_view(request, pk):
    """Download transcription as text file"""
    recording = get_object_or_404(Recording, pk=pk, user=request.user)
    
    if not recording.transcription:
        messages.error(request, 'Транскрипция отсутствует')
        return redirect('recording_detail', pk=recording.pk)
    
    from django.http import HttpResponse
    response = HttpResponse(recording.transcription, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="transcription_{recording.id}.txt"'
    return response


@login_required
@require_http_methods(["POST"])
def delete_recording_view(request, pk):
    """Delete recording"""
    recording = get_object_or_404(Recording, pk=pk, user=request.user)
    recording_title = recording.title
    recording.delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': f'Запись "{recording_title}" успешно удалена'
        })
    
    messages.success(request, 'Запись удалена')
    return redirect('recordings_list')


@login_required
def settings_view(request):
    """User settings"""
    user_settings, _ = UserSettings.objects.get_or_create(user=request.user)
    
    # Получить доступные модели Vosk для шаблона
    from .services.vosk_model_manager import get_all_available_models
    vosk_models = get_all_available_models()
    
    if request.method == 'POST':
        form = UserSettingsForm(request.POST, instance=user_settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Настройки сохранены')
            return redirect('settings')
    else:
        form = UserSettingsForm(instance=user_settings)
    
    context = {
        'form': form,
        'user_settings': user_settings,
        'vosk_models': vosk_models.items(),
    }
    
    return render(request, 'recordings/settings.html', context)



