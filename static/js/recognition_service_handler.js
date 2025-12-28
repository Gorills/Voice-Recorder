/**
 * Обработка выбора библиотеки распознавания и скрытие/показа поля выбора модели
 * Модели Vosk не выбираются через интерфейс, поэтому поле скрывается для Vosk
 */

document.addEventListener('DOMContentLoaded', function() {
    /**
     * Функция для управления видимостью полей выбора моделей
     * @param {string} serviceSelectId - ID элемента выбора библиотеки
     * @param {string} whisperModelSelectId - ID элемента выбора модели Whisper
     * @param {string} voskModelSelectId - ID элемента выбора модели Vosk
     */
    function toggleModelSelects(serviceSelectId, whisperModelSelectId, voskModelSelectId) {
        const serviceSelect = document.getElementById(serviceSelectId);
        const whisperModelSelect = document.getElementById(whisperModelSelectId);
        const voskModelSelect = document.getElementById(voskModelSelectId);
        
        if (!serviceSelect) {
            return;
        }
        
        function updateVisibility() {
            const selectedService = serviceSelect.value;
            const isVosk = selectedService === 'vosk';
            
            // Управление видимостью поля модели Whisper
            if (whisperModelSelect) {
                const whisperContainer = whisperModelSelect.closest('.form-group') || 
                                        whisperModelSelect.parentElement;
                if (whisperContainer) {
                    whisperContainer.style.display = isVosk ? 'none' : '';
                } else {
                    whisperModelSelect.style.display = isVosk ? 'none' : '';
                }
            }
            
            // Управление видимостью поля модели Vosk
            if (voskModelSelect) {
                const voskContainer = voskModelSelect.closest('.form-group') || 
                                     voskModelSelect.parentElement;
                if (voskContainer) {
                    voskContainer.style.display = isVosk ? '' : 'none';
                } else {
                    voskModelSelect.style.display = isVosk ? '' : 'none';
                }
            }
        }
        
        // Установить начальное состояние
        updateVisibility();
        
        // Добавить обработчик изменения
        serviceSelect.addEventListener('change', updateVisibility);
    }
    
    /**
     * Функция для управления видимостью поля выбора модели (старая версия для совместимости)
     * @param {string} serviceSelectId - ID элемента выбора библиотеки
     * @param {string} modelSelectId - ID элемента выбора модели
     * @param {string} modelLabelId - ID элемента label для модели (опционально)
     */
    function toggleModelSelect(serviceSelectId, modelSelectId, modelLabelId = null) {
        const serviceSelect = document.getElementById(serviceSelectId);
        const modelSelect = document.getElementById(modelSelectId);
        const modelLabel = modelLabelId ? document.getElementById(modelLabelId) : null;
        
        if (!serviceSelect || !modelSelect) {
            return;
        }
        
        function updateVisibility() {
            const selectedService = serviceSelect.value;
            const isVosk = selectedService === 'vosk';
            
            // Скрыть/показать поле модели
            const modelContainer = modelSelect.closest('.form-group') || 
                                 modelSelect.parentElement;
            
            if (modelContainer) {
                modelContainer.style.display = isVosk ? 'none' : '';
            } else {
                // Если не нашли контейнер, скрываем сам select
                modelSelect.style.display = isVosk ? 'none' : '';
            }
            
            // Скрыть/показать label если указан
            if (modelLabel) {
                const labelContainer = modelLabel.closest('.form-group') || 
                                      modelLabel.parentElement;
                if (labelContainer) {
                    labelContainer.style.display = isVosk ? 'none' : '';
                } else {
                    modelLabel.style.display = isVosk ? 'none' : '';
                }
            }
        }
        
        // Установить начальное состояние
        updateVisibility();
        
        // Добавить обработчик изменения
        serviceSelect.addEventListener('change', updateVisibility);
    }
    
    // Применить для всех форм на странице
    
    // 1. Форма загрузки файлов
    toggleModelSelects('file-recognition-service-select', 'file-whisper-model-select', 'file-vosk-model-select');
    
    // 2. Форма прямой записи
    toggleModelSelects('recognition-service-select', 'whisper-model-select', 'vosk-model-select');
    
    // 3. Модальное окно
    toggleModelSelects('modal-recognition-service-select', 'modal-whisper-model-select', 'modal-vosk-model-select');
    
    // 4. Страница настроек
    // Используем ID групп для правильного скрытия/показа
    const settingsServiceSelect = document.getElementById('id_default_recognition_service');
    const settingsWhisperGroup = document.getElementById('settings-whisper-model-group');
    const settingsVoskGroup = document.getElementById('settings-vosk-model-group');
    
    if (settingsServiceSelect && settingsWhisperGroup && settingsVoskGroup) {
        function updateSettingsVisibility() {
            const selectedService = settingsServiceSelect.value;
            const isVosk = selectedService === 'vosk';
            
            settingsWhisperGroup.style.display = isVosk ? 'none' : '';
            settingsVoskGroup.style.display = isVosk ? '' : 'none';
        }
        
        // Установить начальное состояние
        updateSettingsVisibility();
        
        // Добавить обработчик изменения
        settingsServiceSelect.addEventListener('change', updateSettingsVisibility);
    }
});

