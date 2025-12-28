// Dashboard real-time updates
class DashboardUpdater {
    constructor() {
        this.updateInterval = null;
        this.updateFrequency = 3000; // 3 секунды
        this.isUpdating = false;
        this.lastStats = null;
        this.processingRecordings = new Set();
    }

    init() {
        // Начать обновление при загрузке страницы
        this.startUpdating();
        
        // Остановить обновление при уходе со страницы
        window.addEventListener('beforeunload', () => {
            this.stopUpdating();
        });
    }

    startUpdating() {
        if (this.updateInterval) {
            return; // Уже запущено
        }

        // Первое обновление сразу
        this.updateStatus();
        
        // Затем каждые N секунд
        this.updateInterval = setInterval(() => {
            this.updateStatus();
        }, this.updateFrequency);
    }

    stopUpdating() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    async updateStatus() {
        if (this.isUpdating) {
            return; // Предотвращаем параллельные запросы
        }

        this.isUpdating = true;

        try {
            const response = await fetch('/api/dashboard-status/', {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
            });

            if (response.ok) {
                const data = await response.json();
                this.processStatusUpdate(data);
            }
        } catch (error) {
            console.error('Ошибка при обновлении статуса:', error);
        } finally {
            this.isUpdating = false;
        }
    }

    processStatusUpdate(data) {
        // Обновить статистику
        this.updateStats(data);

        // Обновить список записей
        this.updateRecordings(data.recordings);

        // Проверить завершенные записи для уведомлений
        this.checkCompletedRecordings(data.recordings);
    }

    updateStats(data) {
        const statsChanged = !this.lastStats || 
            this.lastStats.total_recordings !== data.total_recordings ||
            this.lastStats.completed_recordings !== data.completed_recordings ||
            this.lastStats.processing_recordings !== data.processing_recordings;

        if (statsChanged) {
            // Обновить значения статистики
            const totalEl = document.querySelector('.stat-card:first-child .stat-value');
            const completedEl = document.querySelector('.stat-card:nth-child(2) .stat-value');
            const processingEl = document.querySelector('.stat-card:nth-child(3) .stat-value');

            if (totalEl) totalEl.textContent = data.total_recordings;
            if (completedEl) completedEl.textContent = data.completed_recordings;
            if (processingEl) processingEl.textContent = data.processing_recordings;
        }

        this.lastStats = data;
    }

    updateRecordings(recordings) {
        const recordingsTable = document.querySelector('.table tbody');
        if (!recordingsTable) {
            return;
        }

        // Найти все строки записей
        const rows = recordingsTable.querySelectorAll('tr[data-recording-id]');
        
        recordings.forEach(recordingData => {
            const row = recordingsTable.querySelector(`tr[data-recording-id="${recordingData.id}"]`);
            if (row) {
                // Обновить статус в строке
                const statusCell = row.querySelector('.status-badge');
                if (statusCell) {
                    statusCell.className = `status-badge status-${recordingData.status}`;
                    statusCell.textContent = recordingData.status_display;
                }
            }
        });
    }

    checkCompletedRecordings(recordings) {
        recordings.forEach(recordingData => {
            const recordingId = recordingData.id;
            const wasProcessing = this.processingRecordings.has(recordingId);
            const isCompleted = recordingData.status === 'completed';

            if (wasProcessing && isCompleted) {
                // Запись завершилась - показать уведомление
                this.showCompletionNotification(recordingData);
                this.processingRecordings.delete(recordingId);
            } else if (recordingData.status === 'processing' || recordingData.status === 'uploaded') {
                // Добавить в список обрабатываемых
                this.processingRecordings.add(recordingId);
            } else if (isCompleted) {
                // Уже завершена, не нужно отслеживать
                this.processingRecordings.delete(recordingId);
            }
        });
    }

    showCompletionNotification(recordingData) {
        // Создать уведомление
        const notification = this.createNotification({
            type: 'success',
            title: 'Обработка завершена',
            message: `Запись "${recordingData.title}" успешно обработана`,
            recordingId: recordingData.id,
        });

        // Показать уведомление
        this.displayNotification(notification);

        // Автоматически скрыть через 5 секунд
        setTimeout(() => {
            this.hideNotification(notification);
        }, 5000);
    }

    createNotification({ type, title, message, recordingId }) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.dataset.recordingId = recordingId || '';
        
        notification.innerHTML = `
            <div class="notification-content">
                <div class="notification-icon">
                    ${type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'}
                </div>
                <div class="notification-text">
                    <div class="notification-title">${title}</div>
                    <div class="notification-message">${message}</div>
                </div>
                ${recordingId ? `<a href="/recordings/${recordingId}/" class="notification-action">Открыть</a>` : ''}
                <button class="notification-close" onclick="this.closest('.notification').remove()">×</button>
            </div>
        `;

        return notification;
    }

    displayNotification(notification) {
        let container = document.getElementById('notifications-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notifications-container';
            document.body.appendChild(container);
        }

        container.appendChild(notification);

        // Анимация появления
        setTimeout(() => {
            notification.classList.add('notification-show');
        }, 10);
    }

    hideNotification(notification) {
        notification.classList.remove('notification-show');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    // Проверить, что мы на странице дашборда
    if (document.querySelector('.dashboard-view') || document.querySelector('.stats-grid')) {
        const updater = new DashboardUpdater();
        updater.init();
    }
});



