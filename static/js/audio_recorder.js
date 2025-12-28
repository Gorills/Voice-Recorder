// Audio Recorder для браузера
class BrowserAudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.stream = null;
        this.audioContext = null;
        this.analyser = null;
        this.microphone = null;
        this.dataArray = null;
        this.animationFrame = null;
        this.onVolumeUpdate = null;
        this.recordingStartTime = null;
        this.recordingTimer = null;
    }

    async startRecording() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                } 
            });
            
            // Создать AudioContext для анализа звука
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 2048; // Увеличиваем для более точных измерений
            this.analyser.smoothingTimeConstant = 0.8;
            this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
            
            this.microphone = this.audioContext.createMediaStreamSource(this.stream);
            this.microphone.connect(this.analyser);
            
            const options = {
                mimeType: 'audio/webm;codecs=opus'
            };
            
            if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                options.mimeType = 'audio/webm';
                if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                    options.mimeType = '';
                }
            }

            this.mediaRecorder = new MediaRecorder(this.stream, options);
            this.audioChunks = [];

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = () => {
                const audioBlob = new Blob(this.audioChunks, { type: this.mediaRecorder.mimeType });
                // Вызвать onRecordingComplete ДО сброса isRecording и recordingStartTime
                // чтобы getRecordingDuration() могла правильно вычислить длительность
                this.onRecordingComplete(audioBlob);
                // Теперь можно сбросить состояние
                this.isRecording = false;
                this.recordingStartTime = null;
                this.stopVolumeMonitoring();
                this.stopRecordingTimer();
                this.stream.getTracks().forEach(track => track.stop());
                if (this.audioContext && this.audioContext.state !== 'closed') {
                    this.audioContext.close().catch(err => console.error('Error closing AudioContext:', err));
                }
            };

            this.mediaRecorder.start();
            this.isRecording = true;
            this.recordingStartTime = Date.now();
            
            // Начать отслеживание уровня звука после старта записи
            this.startVolumeMonitoring();
            
            // Начать таймер записи
            this.startRecordingTimer();
            
            return true;
        } catch (error) {
            console.error('Ошибка при начале записи:', error);
            throw error;
        }
    }
    
    startVolumeMonitoring() {
        if (!this.analyser || !this.dataArray) {
            console.error('Analyser not initialized');
            return;
        }
        
        const updateVolume = () => {
            if (!this.isRecording || !this.analyser) {
                return;
            }
            
            // Используем getByteTimeDomainData для измерения уровня звука
            this.analyser.getByteTimeDomainData(this.dataArray);
            
            // Вычислить RMS (Root Mean Square) для более точного измерения
            let sum = 0;
            for (let i = 0; i < this.dataArray.length; i++) {
                const normalized = (this.dataArray[i] - 128) / 128;
                sum += normalized * normalized;
            }
            const rms = Math.sqrt(sum / this.dataArray.length);
            // Увеличиваем чувствительность, умножая на больший коэффициент
            const volume = Math.min(Math.round(rms * 300), 255);
            
            // Вызвать callback для обновления UI
            if (this.onVolumeUpdate) {
                this.onVolumeUpdate(volume);
            }
            
            if (this.isRecording) {
                this.animationFrame = requestAnimationFrame(updateVolume);
            }
        };
        
        updateVolume();
    }
    
    stopVolumeMonitoring() {
        this.isRecording = false; // Установить флаг до отмены анимации
        
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
            this.animationFrame = null;
        }
        
        if (this.onVolumeUpdate) {
            this.onVolumeUpdate(0);
        }
    }
    
    startRecordingTimer() {
        const timerElement = document.getElementById('recording-timer');
        if (!timerElement) {
            console.warn('Элемент recording-timer не найден!');
            return;
        }
        
        // Убрать класс скрытия и показать таймер
        timerElement.classList.remove('recording-timer-hidden');
        timerElement.style.display = 'inline-block';
        timerElement.style.visibility = 'visible';
        timerElement.textContent = '00:00';
        console.log('Таймер показан, display:', timerElement.style.display, 'classList:', timerElement.classList.toString());
        
        const updateTimer = () => {
            if (!this.isRecording || !this.recordingStartTime) {
                return;
            }
            
            const elapsed = Math.floor((Date.now() - this.recordingStartTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            
            timerElement.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
            
            this.recordingTimer = setTimeout(updateTimer, 1000);
        };
        
        // Запустить обновление таймера
        updateTimer();
    }
    
    stopRecordingTimer() {
        if (this.recordingTimer) {
            clearTimeout(this.recordingTimer);
            this.recordingTimer = null;
        }
        
        const timerElement = document.getElementById('recording-timer');
        if (timerElement) {
            timerElement.textContent = '00:00';
            timerElement.classList.add('recording-timer-hidden');
            timerElement.style.display = 'none';
        }
        
        // НЕ сбрасывать recordingStartTime здесь - он нужен для getRecordingDuration()
        // recordingStartTime будет сброшен в mediaRecorder.onstop
    }

    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            // НЕ сбрасывать isRecording и recordingStartTime здесь!
            // Они нужны для getRecordingDuration() в onRecordingComplete
            this.stopVolumeMonitoring();
            this.stopRecordingTimer();
            this.mediaRecorder.stop();
            // isRecording и recordingStartTime будут сброшены после onRecordingComplete
        }
    }

    getRecordingDuration() {
        if (!this.recordingStartTime) {
            return 0;
        }
        return Math.floor((Date.now() - this.recordingStartTime) / 1000);
    }

    onRecordingComplete(audioBlob) {
        // Будет переопределено
    }
}

// Функция сброса состояния формы записи
function resetRecordingForm() {
    const titleInput = document.getElementById('recording-title-input');
    if (titleInput) {
        titleInput.value = '';
    }
    
    const audioPreview = document.getElementById('audio-preview');
    const audioPreviewContainer = document.getElementById('audio-preview-container');
    
    // Очистить превью
    if (audioPreview) {
        audioPreview.src = '';
        audioPreview.load();
        audioPreview.controls = false;
    }
    if (audioPreviewContainer) {
        audioPreviewContainer.style.display = 'none';
    }
    
    // Скрыть визуализацию (на всякий случай)
    const volumeIndicator = document.getElementById('volume-indicator');
    const volumeIndicatorContainer = document.getElementById('volume-indicator-container');
    const volumeBars = document.getElementById('volume-bars');
    
    if (volumeIndicator) {
        volumeIndicator.style.width = '0%';
    }
    if (volumeIndicatorContainer) {
        volumeIndicatorContainer.style.display = 'none';
    }
    if (volumeBars) {
        volumeBars.style.display = 'none';
    }
    
    // Скрыть таймер
    const timerElement = document.getElementById('recording-timer');
    if (timerElement) {
        timerElement.style.display = 'none';
        timerElement.classList.add('recording-timer-hidden');
        timerElement.textContent = '00:00';
    }
}

// Функция сброса статуса записи
function resetRecordingStatus() {
    const statusElement = document.getElementById('recording-status');
    const statusText = document.getElementById('recording-status-text');
    const recordButton = document.getElementById('record-button');
    const stopButton = document.getElementById('stop-button');
    
    console.log('🔄 Сброс статуса записи');
    
    if (statusText) {
        statusText.textContent = 'Готов к записи';
    }
    if (statusElement) {
        statusElement.className = 'recording-status';
    }
    
    // Вернуть кнопки в исходное состояние
    if (recordButton) {
        recordButton.disabled = false;
        console.log('✅ Кнопка "Начать запись" активирована');
    }
    if (stopButton) {
        stopButton.disabled = true;
        console.log('✅ Кнопка "Остановить" деактивирована');
    }
}

// Инициализация записи
function initAudioRecorder() {
    const recorder = new BrowserAudioRecorder();
    const recordButton = document.getElementById('record-button');
    const stopButton = document.getElementById('stop-button');
    const statusElement = document.getElementById('recording-status');
    const audioPreview = document.getElementById('audio-preview');
    const audioPreviewContainer = document.getElementById('audio-preview-container');
    let recordedBlob = null;
    let recordedDuration = 0;

    if (!recordButton || !stopButton || !statusElement) {
        return;
    }

    // Найти элементы визуализации уровня звука
    const volumeIndicator = document.getElementById('volume-indicator');
    const volumeIndicatorContainer = document.getElementById('volume-indicator-container');
    const volumeBars = document.getElementById('volume-bars');
    
    // Callback для обновления визуализации уровня звука
    recorder.onVolumeUpdate = (volume) => {
        // Нормализовать значение от 0 до 100 для процентов
        const volumePercent = Math.min((volume / 255) * 100, 100);
        
        if (volumeIndicator) {
            volumeIndicator.style.width = `${volumePercent}%`;
        }
        
        if (volumeBars) {
            // Обновить анимацию полосок
            const bars = volumeBars.querySelectorAll('.volume-bar');
            const barCount = bars.length;
            const normalizedVolume = volume / 255;
            // Используем более чувствительную шкалу
            const activeBars = Math.ceil(normalizedVolume * barCount);
            
            bars.forEach((bar, index) => {
                if (index < activeBars && normalizedVolume > 0.01) {
                    // Интенсивность зависит от позиции полоски
                    const position = index / barCount;
                    const intensity = Math.max(0, normalizedVolume - position);
                    const barIntensity = Math.min(intensity * 2, 1);
                    
                    bar.style.opacity = 0.4 + barIntensity * 0.6;
                    bar.style.transform = `scaleY(${0.4 + barIntensity * 0.6})`;
                } else {
                    bar.style.opacity = 0.2;
                    bar.style.transform = 'scaleY(0.3)';
                }
            });
        }
    };

    // Функция загрузки записи
    async function uploadRecording() {
        if (!recordedBlob || recordedBlob.size === 0) {
            const statusText = document.getElementById('recording-status-text');
            if (statusText) {
                statusText.textContent = '❌ Ошибка: нет записанного аудио';
            }
            statusElement.className = 'recording-status';
            resetRecordingStatus();
            return;
        }

        const statusText = document.getElementById('recording-status-text');
        if (statusText) {
            statusText.textContent = 'Загрузка записи на сервер...';
        }
        statusElement.className = 'recording-status uploading';
        console.log('📤 Начало загрузки записи на сервер...');

        try {
            const formData = new FormData();
            
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const fileName = `recording_${timestamp}.webm`;
            const audioFile = new File([recordedBlob], fileName, { type: recordedBlob.type });
            formData.append('audio_file', audioFile);
            
            const titleInput = document.getElementById('recording-title-input');
            if (titleInput && titleInput.value.trim()) {
                formData.append('title', titleInput.value.trim());
            } else {
                const now = new Date();
                const title = `Запись ${now.toLocaleDateString('ru-RU')} ${now.toLocaleTimeString('ru-RU')}`;
                formData.append('title', title);
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

            const modelSelect = document.getElementById('whisper-model-select');
            if (modelSelect) {
                formData.append('whisper_model', modelSelect.value);
            }
            
            // Добавить длительность записи (в секундах) из таймера
            if (recordedDuration && recordedDuration > 0) {
                formData.append('duration', recordedDuration.toString());
                console.log(`✅ Отправка длительности на сервер: ${recordedDuration} секунд`);
            } else {
                console.warn('⚠️ Длительность не установлена или равна 0, recordedDuration:', recordedDuration);
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
                    const statusText = document.getElementById('recording-status-text');
                    if (statusText) {
                        statusText.textContent = result.message || '✅ Запись успешно загружена!';
                    }
                    statusElement.className = 'recording-status success';
                    
                    // Сбросить переменные
                    recordedBlob = null;
                    recordedDuration = 0;
                    console.log('🧹 Переменные сброшены');
                    
                    // Сбросить состояние формы для новой записи
                    resetRecordingForm();
                    console.log('🧹 Форма сброшена');
                    
                    // Если включено автоматическое распознавание, остаемся на странице
                    // и просто обновляем список записей (dashboard.js уже делает это)
                    if (result.auto_transcribe) {
                        console.log('⏳ Автоматическое распознавание включено, ожидание 2 секунды перед сбросом статуса...');
                        // Обновим статус через 2 секунды обратно на "Готов к записи"
                        setTimeout(() => {
                            console.log('🔄 Запуск resetRecordingStatus()...');
                            resetRecordingStatus();
                        }, 2000);
                    } else {
                        console.log('↪️ Автоматическое распознавание выключено, редирект через 1.5 секунды...');
                        // Если автоматическое распознавание выключено, делаем редирект на страницу записи
                        setTimeout(() => {
                            if (result.redirect_url) {
                                window.location.href = result.redirect_url;
                            } else {
                                window.location.reload();
                            }
                        }, 1500);
                    }
                } else {
                    // Ошибка при загрузке - сбросить форму
                    resetRecordingForm();
                    resetRecordingStatus();
                    
                    const statusText = document.getElementById('recording-status-text');
                    if (statusText) {
                        statusText.textContent = '❌ Ошибка: ' + (result.error || 'Неизвестная ошибка');
                    }
                    statusElement.className = 'recording-status';
                    
                    // Вернуть кнопки в исходное состояние
                    recordButton.disabled = false;
                    stopButton.disabled = true;
                }
            } else {
                // Ошибка при загрузке - сбросить форму
                resetRecordingForm();
                resetRecordingStatus();
                
                try {
                    const errorData = await response.json();
                    const statusText = document.getElementById('recording-status-text');
                    if (statusText) {
                        statusText.textContent = '❌ Ошибка загрузки: ' + (errorData.error || 'Неизвестная ошибка');
                    }
                    statusElement.className = 'recording-status';
                } catch (e) {
                    const statusText = document.getElementById('recording-status-text');
                    if (statusText) {
                        statusText.textContent = '❌ Ошибка загрузки';
                    }
                    statusElement.className = 'recording-status';
                }
                
                // Вернуть кнопки в исходное состояние
                recordButton.disabled = false;
                stopButton.disabled = true;
            }
        } catch (error) {
            console.error('Ошибка при загрузке:', error);
            
            // Ошибка при загрузке - сбросить форму
            resetRecordingForm();
            resetRecordingStatus();
            
            const statusText = document.getElementById('recording-status-text');
            if (statusText) {
                statusText.textContent = '❌ Ошибка при загрузке: ' + error.message;
            }
            statusElement.className = 'recording-status';
            
            // Вернуть кнопки в исходное состояние
            recordButton.disabled = false;
            stopButton.disabled = true;
        }
    }

    // Обработчик начала записи
    recordButton.addEventListener('click', async () => {
        try {
            await recorder.startRecording();
            recordButton.disabled = true;
            stopButton.disabled = false;
            
            const statusText = document.getElementById('recording-status-text');
            if (statusText) {
                statusText.textContent = '🔴 Идет запись...';
            }
            statusElement.className = 'recording-status recording';
            
            if (audioPreviewContainer) {
                audioPreviewContainer.style.display = 'none';
            }
            
            // Показать визуализацию
            if (volumeBars) {
                volumeBars.style.display = 'flex';
            }
            if (volumeIndicatorContainer) {
                volumeIndicatorContainer.style.display = 'block';
            }
        } catch (error) {
            alert('Ошибка доступа к микрофону: ' + error.message);
            console.error(error);
        }
    });

    // Обработчик остановки записи
    stopButton.addEventListener('click', () => {
        recorder.stopRecording();
        
        const statusText = document.getElementById('recording-status-text');
        const timerElement = document.getElementById('recording-timer');
        if (statusText) {
            statusText.textContent = 'Подготовка к загрузке...';
        }
        if (timerElement) {
            timerElement.style.display = 'none';
            timerElement.classList.add('recording-timer-hidden');
        }
        statusElement.className = 'recording-status uploading';
        
        // Скрыть визуализацию
        if (volumeIndicator) {
            volumeIndicator.style.width = '0%';
        }
        if (volumeIndicatorContainer) {
            volumeIndicatorContainer.style.display = 'none';
        }
        if (volumeBars) {
            volumeBars.style.display = 'none';
        }
        
        // Заблокировать кнопки во время загрузки
        recordButton.disabled = true;
        stopButton.disabled = true;
    });

    // Обработчик завершения записи
    recorder.onRecordingComplete = async (audioBlob) => {
        recordedBlob = audioBlob;
        
        // Получить длительность из таймера (более надежно, чем из blob)
        const duration = recorder.getRecordingDuration();
        recordedDuration = duration; // Сохранить для использования при загрузке
        console.log(`📊 Длительность записи: ${duration} секунд`);
        console.log(`📊 recordingStartTime: ${recorder.recordingStartTime}, isRecording: ${recorder.isRecording}, currentTime: ${Date.now()}`);
        
        if (duration === 0) {
            console.error('❌ ОШИБКА: длительность равна 0! recordingStartTime:', recorder.recordingStartTime, 'isRecording:', recorder.isRecording);
        }
        
        const audioUrl = URL.createObjectURL(audioBlob);
        
        if (audioPreview) {
            audioPreview.src = audioUrl;
            audioPreview.controls = true;
        }
        
        if (audioPreviewContainer) {
            audioPreviewContainer.style.display = 'block';
        }
        
        // Скрыть визуализацию
        if (volumeIndicator) {
            volumeIndicator.style.width = '0%';
        }
        if (volumeIndicatorContainer) {
            volumeIndicatorContainer.style.display = 'none';
        }
        if (volumeBars) {
            volumeBars.style.display = 'none';
        }
        
        // Автоматически начать загрузку после небольшой задержки
        setTimeout(async () => {
            await uploadRecording();
        }, 500);
    };

    // Проверка поддержки
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        recordButton.disabled = true;
        const statusText = document.getElementById('recording-status-text');
        if (statusText) {
            statusText.textContent = 'Ваш браузер не поддерживает запись аудио';
        }
        statusElement.className = 'recording-status';
    }
}

document.addEventListener('DOMContentLoaded', initAudioRecorder);
