/**
 * File upload functionality for audio files
 */

// Инициализация загрузки файлов
function initFileUpload() {
    const fileInput = document.getElementById('file-upload-input');
    const fileUploadButton = document.getElementById('file-upload-button');
    const filePreviewContainer = document.getElementById('file-preview-container');
    const fileInfo = document.getElementById('file-info');
    const fileAudioPreview = document.getElementById('file-audio-preview');
    const fileUploadStatus = document.getElementById('file-upload-status');
    const fileUploadStatusText = document.getElementById('file-upload-status-text');
    const fileTitleInput = document.getElementById('file-upload-title-input');
    const fileModelSelect = document.getElementById('file-whisper-model-select');
    const fileUploadLabel = document.querySelector('.file-upload-label');
    
    let selectedFile = null;

    if (!fileInput || !fileUploadButton) {
        // Elements not found on this page, silently return
        return;
    }

    // Обработка выбора файла
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            handleFileSelect(file);
        }
    });

    // Drag and drop
    if (fileUploadLabel) {
        fileUploadLabel.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.stopPropagation();
            fileUploadLabel.style.borderColor = 'var(--primary)';
            fileUploadLabel.style.background = 'var(--bg-primary)';
        });

        fileUploadLabel.addEventListener('dragleave', function(e) {
            e.preventDefault();
            e.stopPropagation();
            fileUploadLabel.style.borderColor = '';
            fileUploadLabel.style.background = '';
        });

        fileUploadLabel.addEventListener('drop', function(e) {
            e.preventDefault();
            e.stopPropagation();
            fileUploadLabel.style.borderColor = '';
            fileUploadLabel.style.background = '';
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const file = files[0];
                if (file.type.startsWith('audio/')) {
                    fileInput.files = files;
                    handleFileSelect(file);
                } else {
                    updateStatus('Ошибка: выберите аудио файл', 'error');
                }
            }
        });

        // Клик по label открывает файловый диалог
        fileUploadLabel.addEventListener('click', function(e) {
            if (e.target !== fileInput) {
                fileInput.click();
            }
        });
    }

    // Обработка выбранного файла
    function handleFileSelect(file) {
        // Проверка типа файла
        if (!file.type.startsWith('audio/')) {
            updateStatus('Ошибка: выберите аудио файл', 'error');
            fileUploadButton.disabled = true;
            return;
        }

        // Проверка размера (100 MB максимум)
        const maxSize = 100 * 1024 * 1024; // 100 MB
        if (file.size > maxSize) {
            updateStatus(`Ошибка: файл слишком большой (максимум ${maxSize / (1024*1024)} MB)`, 'error');
            fileUploadButton.disabled = true;
            return;
        }

        selectedFile = file;

        // Показать информацию о файле
        const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
        fileInfo.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong style="color: var(--text-primary);">${file.name}</strong>
                    <div style="color: var(--text-secondary); font-size: 0.875rem; margin-top: 0.25rem;">
                        ${fileSizeMB} MB • ${file.type}
                    </div>
                </div>
            </div>
        `;

        // Показать превью
        filePreviewContainer.style.display = 'block';
        
        // Создать URL для превью
        const audioURL = URL.createObjectURL(file);
        fileAudioPreview.src = audioURL;

        // Активировать кнопку загрузки
        fileUploadButton.disabled = false;
        
        // Обновить статус
        updateStatus('Файл выбран, готов к загрузке', 'ready');
    }

    // Обработка загрузки файла
    fileUploadButton.addEventListener('click', async function() {
        if (!selectedFile) {
            updateStatus('Ошибка: файл не выбран', 'error');
            return;
        }

        await uploadFile(selectedFile);
    });

    // Функция загрузки файла
    async function uploadFile(file) {
        fileUploadButton.disabled = true;
        updateStatus('Загрузка файла на сервер...', 'uploading');

        try {
            const formData = new FormData();
            formData.append('audio_file', file);

            // Добавить название
            if (fileTitleInput && fileTitleInput.value.trim()) {
                formData.append('title', fileTitleInput.value.trim());
            } else {
                const now = new Date();
                const title = `Запись ${now.toLocaleDateString('ru-RU')} ${now.toLocaleTimeString('ru-RU')}`;
                formData.append('title', title);
            }

            // Добавить модель Whisper
            if (fileModelSelect) {
                formData.append('whisper_model', fileModelSelect.value);
            }

            // CSRF токен
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
            if (csrfToken) {
                formData.append('csrfmiddlewaretoken', csrfToken.value);
            } else {
                const cookies = document.cookie.split(';');
                for (let cookie of cookies) {
                    const [name, value] = cookie.trim().split('=');
                    if (name === 'csrftoken') {
                        formData.append('csrfmiddlewaretoken', value);
                        break;
                    }
                }
            }

            const response = await fetch(window.location.origin + '/recordings/upload/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (response.ok) {
                const result = await response.json();
                console.log('✅ Ответ сервера получен:', result);
                
                if (result.success) {
                    updateStatus(result.message || '✅ Файл успешно загружен!', 'success');
                    
                    // Очистить форму
                    resetFileUploadForm();
                    
                    // Если включено автоматическое распознавание, остаемся на странице
                    if (result.auto_transcribe) {
                        setTimeout(() => {
                            updateStatus('Выберите файл для загрузки', 'ready');
                        }, 2000);
                    } else {
                        // Если автоматическое распознавание выключено, делаем редирект
                        setTimeout(() => {
                            if (result.redirect_url) {
                                window.location.href = result.redirect_url;
                            } else {
                                window.location.reload();
                            }
                        }, 1500);
                    }
                } else {
                    updateStatus('❌ Ошибка: ' + (result.error || 'Неизвестная ошибка'), 'error');
                    fileUploadButton.disabled = false;
                }
            } else {
                const errorData = await response.json().catch(() => ({}));
                updateStatus('❌ Ошибка загрузки: ' + (errorData.error || 'Неизвестная ошибка'), 'error');
                fileUploadButton.disabled = false;
            }
        } catch (error) {
            console.error('Ошибка при загрузке файла:', error);
            updateStatus('❌ Ошибка: ' + error.message, 'error');
            fileUploadButton.disabled = false;
        }
    }

    // Функция обновления статуса
    function updateStatus(message, status = 'ready') {
        if (fileUploadStatusText) {
            fileUploadStatusText.textContent = message;
        }
        if (fileUploadStatus) {
            fileUploadStatus.className = 'recording-status';
            if (status === 'uploading') {
                fileUploadStatus.classList.add('uploading');
            } else if (status === 'success') {
                fileUploadStatus.classList.add('success');
            } else if (status === 'error') {
                fileUploadStatus.classList.add('error');
            }
        }
    }

    // Функция сброса формы загрузки
    function resetFileUploadForm() {
        selectedFile = null;
        if (fileInput) {
            fileInput.value = '';
        }
        if (filePreviewContainer) {
            filePreviewContainer.style.display = 'none';
        }
        if (fileAudioPreview) {
            fileAudioPreview.src = '';
            fileAudioPreview.load();
        }
        if (fileTitleInput) {
            fileTitleInput.value = '';
        }
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    initFileUpload();
});

