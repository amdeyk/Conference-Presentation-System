/**
 * Moderator interface JavaScript for Conference Presentation System
 */

// Extend the global updateUI function
const originalUpdateUI = updateUI;
updateUI = function() {
    // Call the original function if it exists
    if (typeof originalUpdateUI === 'function') {
        originalUpdateUI();
    }
    
    // Update timer display
    const timerDisplay = document.getElementById('timer-display');
    if (timerDisplay) {
        timerDisplay.textContent = formatTime(state.timer_seconds);
        
        // Update timer color
        timerDisplay.classList.remove('timer-green', 'timer-yellow', 'timer-red');
        timerDisplay.classList.add(getTimerColorClass(state.timer_seconds));
    }
    
    // Update presenter fields
    const presenterName = document.getElementById('presenter-name');
    const presentationTopic = document.getElementById('presentation-topic');
    
    if (presenterName) {
        presenterName.value = state.current_presenter;
    }
    
    if (presentationTopic) {
        presentationTopic.value = state.current_topic;
    }
    
    // Update announcement field
    const announcementText = document.getElementById('announcement-text');
    if (announcementText) {
        announcementText.value = state.announcement;
    }
    
    // Update status indicators
    updateStatusIndicators();
    
    // Update system health
    updateSystemHealth();
};

/**
 * Update system status indicators
 */
function updateStatusIndicators() {
    // Main status
    const mainStatus = document.getElementById('main-status');
    if (mainStatus) {
        mainStatus.textContent = state.device_status.main;
        mainStatus.className = state.device_status.main === 'ONLINE' 
            ? 'bg-green-100 text-green-800 p-2 rounded' 
            : 'bg-red-100 text-red-800 p-2 rounded';
    }
    
    // Backup status
    const backupStatus = document.getElementById('backup-status');
    if (backupStatus) {
        backupStatus.textContent = state.device_status.backup;
        backupStatus.className = state.device_status.backup === 'ONLINE' 
            ? 'bg-green-100 text-green-800 p-2 rounded' 
            : (state.device_status.backup === 'UNKNOWN'
                ? 'bg-gray-100 text-gray-800 p-2 rounded'
                : 'bg-red-100 text-red-800 p-2 rounded');
    }
    
    // Connected clients
    const clientsCount = document.getElementById('clients-count');
    if (clientsCount) {
        clientsCount.textContent = state.connected_clients;
    }
    
    // System status
    const systemStatus = document.getElementById('system-status');
    if (systemStatus) {
        systemStatus.textContent = `System: ${state.device_status.main === 'ONLINE' ? 'Main' : 'Backup'}`;
    }
}

/**
 * Update system health indicators
 */
function updateSystemHealth() {
    const systemHealth = document.getElementById('system-health');
    if (!systemHealth) return;
    
    const health = state.system_health;
    let healthStatus = 'Good';
    let healthClass = 'bg-green-100 text-green-800';
    
    if (health.cpu > 80 || health.memory > 80) {
        healthStatus = 'Warning';
        healthClass = 'bg-yellow-100 text-yellow-800';
    }
    
    if (health.cpu > 90 || health.memory > 90 || health.network !== 'OK') {
        healthStatus = 'Critical';
        healthClass = 'bg-red-100 text-red-800';
    }
    
    systemHealth.textContent = healthStatus;
    systemHealth.className = healthClass + ' p-2 rounded';
}

/**
 * Initialize moderator-specific event handlers
 */
function initModeratorInterface() {
    // Timer control buttons
    document.getElementById('start-timer')?.addEventListener('click', function() {
        sendMessage('timer_control', { running: true });
    });
    
    document.getElementById('pause-timer')?.addEventListener('click', function() {
        sendMessage('timer_control', { running: false });
    });
    
    document.getElementById('reset-timer')?.addEventListener('click', function() {
        sendMessage('timer_control', { seconds: 600, running: false });
    });
    
    // Timer preset buttons
    document.querySelectorAll('[data-time]').forEach(button => {
        button.addEventListener('click', function() {
            const minutes = parseInt(this.getAttribute('data-time'));
            sendMessage('timer_control', { seconds: minutes * 60, running: false });
        });
    });
    
    // Custom timer
    document.getElementById('set-custom-time')?.addEventListener('click', function() {
        const minutes = parseInt(document.getElementById('custom-minutes').value) || 0;
        const seconds = parseInt(document.getElementById('custom-seconds').value) || 0;
        const totalSeconds = (minutes * 60) + seconds;
        
        if (totalSeconds > 0) {
            sendMessage('timer_control', { seconds: totalSeconds, running: false });
        }
    });
    
    // Presenter information
    document.getElementById('update-presenter')?.addEventListener('click', function() {
        const name = document.getElementById('presenter-name').value;
        const topic = document.getElementById('presentation-topic').value;
        
        sendMessage('presenter_update', { name: name, topic: topic });
    });
    
    // Announcements
    document.getElementById('send-announcement')?.addEventListener('click', function() {
        const message = document.getElementById('announcement-text').value;
        
        if (message.trim()) {
            sendMessage('announcement', { message: message, visible: true });
        }
    });
    
    document.getElementById('clear-announcement')?.addEventListener('click', function() {
        document.getElementById('announcement-text').value = '';
        sendMessage('announcement', { message: '', visible: false });
    });
    
    // Emergency controls
    document.getElementById('force-backup')?.addEventListener('click', function() {
        if (confirm('Are you sure you want to switch to the backup system?')) {
            sendMessage('control', { command: 'switch_to_backup' });
        }
    });
    
    document.getElementById('force-main')?.addEventListener('click', function() {
        if (confirm('Are you sure you want to switch back to the main system?')) {
            sendMessage('control', { command: 'switch_to_main' });
        }
    });
}

// Initialize the moderator interface on page load
document.addEventListener('DOMContentLoaded', initModeratorInterface);