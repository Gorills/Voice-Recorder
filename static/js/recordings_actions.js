/**
 * JavaScript for recording actions (transcribe, delete)
 */

document.addEventListener('DOMContentLoaded', function() {
    let currentRecordingId = null;
    let currentRecordingTitle = null;
    let currentTranscribeButton = null;
    
    // Инициализация модального окна
    const modal = document.getElementById('whisper-model-modal');
    const modalOverlay = modal?.querySelector('.modal-overlay');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const modalCancelBtn = document.getElementById('modal-cancel-btn');
    const modalConfirmBtn = document.getElementById('modal-confirm-btn');
    const modalSelect = document.getElementById('modal-whisper-model-select');
    
    // Функция открытия модального окна
    function openModal(recordingId, recordingTitle, button) {
        currentRecordingId = recordingId;
        currentRecordingTitle = recordingTitle;
        currentTranscribeButton = button;
        if (modal) {
            modal.style.display = 'block';
            document.body.style.overflow = 'hidden'; // Запретить прокрутку фона
        }
    }
    
    // Функция закрытия модального окна
    function closeModal() {
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = ''; // Восстановить прокрутку
        }
        currentRecordingId = null;
        currentRecordingTitle = null;
        currentTranscribeButton = null;
    }
    
    // Закрытие модального окна при клике на overlay
    if (modalOverlay) {
        modalOverlay.addEventListener('click', closeModal);
    }
    
    // Закрытие модального окна при клике на кнопку закрытия
    if (modalCloseBtn) {
        modalCloseBtn.addEventListener('click', closeModal);
    }
    
    // Закрытие модального окна при клике на кнопку отмены
    if (modalCancelBtn) {
        modalCancelBtn.addEventListener('click', closeModal);
    }
    
    // Закрытие модального окна при нажатии Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal && modal.style.display === 'block') {
            closeModal();
        }
    });
    
    // Обработка подтверждения распознавания
    if (modalConfirmBtn) {
        modalConfirmBtn.addEventListener('click', function() {
            if (!currentRecordingId) {
                return;
            }
            
            const selectedModel = modalSelect?.value || 'base';
            startTranscription(currentRecordingId, currentRecordingTitle, selectedModel, currentTranscribeButton);
            closeModal();
        });
    }
    
    // Обработка остановки обработки
    document.querySelectorAll('.button-icon-cancel').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const recordingId = this.dataset.recordingId;
            const recordingTitle = this.dataset.recordingTitle || 'запись';
            
            if (!recordingId) {
                console.error('Recording ID not found');
                return;
            }
            
            if (this.disabled) {
                return;
            }
            
            // Подтверждение остановки
            if (!confirm(`Вы уверены, что хотите остановить обработку записи "${recordingTitle}"?`)) {
                return;
            }
            
            // Отключить кнопку
            this.disabled = true;
            const originalHTML = this.innerHTML;
            this.innerHTML = '<svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24" class="spinning"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>';
            
            // Получить CSRF токен
            const csrfToken = getCsrfToken();
            
            fetch(`/recordings/${recordingId}/cancel-transcription/`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json',
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('success', 'Обработка остановлена', data.message || `Обработка записи "${recordingTitle}" остановлена`);
                    // Обновить статус в таблице и заменить кнопку
                    updateRecordingStatus(recordingId, 'uploaded');
                    // Перезагрузить страницу через 1 секунду для обновления интерфейса
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showNotification('error', 'Ошибка', data.error || 'Не удалось остановить обработку');
                    // Восстановить кнопку
                    this.disabled = false;
                    this.innerHTML = originalHTML;
                }
            })
            .catch(error => {
                console.error('Ошибка при остановке обработки:', error);
                showNotification('error', 'Ошибка', 'Не удалось остановить обработку');
                // Восстановить кнопку
                this.disabled = false;
                this.innerHTML = originalHTML;
            });
        });
    });
    
    // Обработка повторного распознавания
    document.querySelectorAll('.button-icon-transcribe').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const recordingId = this.dataset.recordingId;
            const recordingTitle = this.dataset.recordingTitle || 'запись';
            
            if (!recordingId) {
                console.error('Recording ID not found');
                return;
            }
            
            if (this.disabled) {
                return; // Уже обрабатывается
            }
            
            // Показать модальное окно
            openModal(recordingId, recordingTitle, this);
        });
    });
    
    // Функция запуска распознавания
    function startTranscription(recordingId, recordingTitle, whisperModel, button) {
        if (!button || button.disabled) {
            return;
        }
        
        // Отключить кнопку
        button.disabled = true;
        const originalHTML = button.innerHTML;
        button.innerHTML = '<svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24" class="spinning"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>';
        
        // Получить CSRF токен
        const csrfToken = getCsrfToken();
        
        // Создать FormData для отправки модели
        const formData = new FormData();
        formData.append('whisper_model', whisperModel);
        
        fetch(`/recordings/${recordingId}/transcribe/`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken,
            },
            body: formData,
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('success', 'Распознавание начато', `Распознавание для "${recordingTitle}" успешно запущено`);
                // Обновить статус в таблице
                updateRecordingStatus(recordingId, 'processing');
            } else {
                showNotification('error', 'Ошибка', data.error || 'Не удалось запустить распознавание');
                // Восстановить кнопку
                button.disabled = false;
                button.innerHTML = originalHTML;
            }
        })
        .catch(error => {
            console.error('Ошибка при запуске распознавания:', error);
            showNotification('error', 'Ошибка', 'Не удалось запустить распознавание');
            // Восстановить кнопку
            button.disabled = false;
            button.innerHTML = originalHTML;
        });
    }
    
    // Обработка удаления записи
    document.querySelectorAll('.button-icon-delete').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const recordingId = this.dataset.recordingId;
            const recordingTitle = this.dataset.recordingTitle || 'запись';
            const row = this.closest('tr');
            
            if (!recordingId) {
                console.error('Recording ID not found');
                return;
            }
            
            // Подтверждение удаления
            if (!confirm(`Вы уверены, что хотите удалить запись "${recordingTitle}"?\n\nЭто действие нельзя отменить.`)) {
                return;
            }
            
            if (this.disabled) {
                return; // Уже обрабатывается
            }
            
            // Отключить кнопку
            this.disabled = true;
            const originalHTML = this.innerHTML;
            this.innerHTML = '<svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24" class="spinning"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>';
            
            // Получить CSRF токен
            const csrfToken = getCsrfToken();
            
            fetch(`/recordings/${recordingId}/delete/`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json',
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('success', 'Запись удалена', data.message || `Запись "${recordingTitle}" успешно удалена`);
                    // Удалить строку из таблицы с анимацией
                    if (row) {
                        row.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                        row.style.opacity = '0';
                        row.style.transform = 'translateX(-20px)';
                        setTimeout(() => {
                            row.remove();
                            // Если строк не осталось, показать сообщение
                            const tbody = document.querySelector('.table tbody');
                            if (tbody && tbody.children.length === 0) {
                                location.reload(); // Перезагрузить страницу
                            }
                        }, 300);
                    } else {
                        // Если строка не найдена, просто перезагрузить страницу
                        setTimeout(() => location.reload(), 500);
                    }
                } else {
                    showNotification('error', 'Ошибка', data.error || 'Не удалось удалить запись');
                    // Восстановить кнопку
                    this.disabled = false;
                    this.innerHTML = originalHTML;
                }
            })
            .catch(error => {
                console.error('Ошибка при удалении записи:', error);
                showNotification('error', 'Ошибка', 'Не удалось удалить запись');
                // Восстановить кнопку
                this.disabled = false;
                this.innerHTML = originalHTML;
            });
        });
    });
    
    // Функция получения CSRF токена
    function getCsrfToken() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfToken) {
            return csrfToken.value;
        }
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return '';
    }
    
    // Функция показа уведомления
    function showNotification(type, title, message) {
        // Используем существующую систему уведомлений из dashboard.js если она есть
        if (window.DashboardUpdater && window.DashboardUpdater.prototype.createNotification) {
            const updater = new DashboardUpdater();
            const notification = updater.createNotification({ type, title, message });
            updater.displayNotification(notification);
            setTimeout(() => updater.hideNotification(notification), 5000);
            return;
        }
        
        // Простое уведомление через alert если система уведомлений не доступна
        // В реальном приложении можно использовать более сложную систему
        console.log(`[${type.toUpperCase()}] ${title}: ${message}`);
    }
    
    // Функция обновления статуса записи в таблице
    function updateRecordingStatus(recordingId, newStatus) {
        // Найти кнопку по data-recording-id и получить строку через closest('tr')
        const button = document.querySelector(`.button-icon-transcribe[data-recording-id="${recordingId}"], .button-icon-delete[data-recording-id="${recordingId}"]`);
        if (!button) {
            // Если кнопка не найдена, перезагрузить страницу через некоторое время
            setTimeout(() => location.reload(), 2000);
            return;
        }
        
        const row = button.closest('tr');
        if (!row) {
            setTimeout(() => location.reload(), 2000);
            return;
        }
        
        const statusCell = row.querySelector('.status-badge');
        if (statusCell) {
            // Обновить класс статуса
            statusCell.className = `status-badge status-${newStatus}`;
            
            // Обновить текст статуса
            const statusTexts = {
                'processing': 'В обработке',
                'completed': 'Завершено',
                'uploaded': 'Загружено',
                'failed': 'Ошибка'
            };
            statusCell.textContent = statusTexts[newStatus] || newStatus;
        }
        
        // Скрыть кнопку распознавания если статус processing
        const transcribeButton = row.querySelector('.button-icon-transcribe');
        if (transcribeButton && newStatus === 'processing') {
            transcribeButton.style.display = 'none';
        }
    }
});

