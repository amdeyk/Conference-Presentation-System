/**
 * Presenter interface JavaScript for Conference Presentation System
 */

// Extend the global updateUI function
const originalUpdateUI = updateUI;
updateUI = function() {
    // Call the original function if it exists
    if (typeof originalUpdateUI === 'function') {
        originalUpdateUI();
    }
    
    // Update presenter info
    const presenterName = document.getElementById('presenter-name');
    const presentationTopic = document.getElementById('presentation-topic');
    
    if (presenterName) {
        presenterName.textContent = state.current_presenter;
    }
    
    if (presentationTopic) {
        presentationTopic.textContent = state.current_topic;
    }
    
    // Update timer display
    const timerDisplay = document.getElementById('timer-display');
    if (timerDisplay) {
        timerDisplay.textContent = formatTime(state.timer_seconds);
        
        // Update timer color
        timerDisplay.classList.remove('timer-green', 'timer-yellow', 'timer-red');
        timerDisplay.classList.add(getTimerColorClass(state.timer_seconds));
        
        // Add flashing effect for last 10 seconds
        if (state.timer_seconds <= 10 && state.timer_running) {
            timerDisplay.classList.add('timer-flashing');
        } else {
            timerDisplay.classList.remove('timer-flashing');
        }
    }
    
    // Update slide indicator
    const slideIndicator = document.getElementById('slide-indicator');
    if (slideIndicator) {
        slideIndicator.textContent = `Slide: ${state.current_slide}/${state.total_slides}`;
    }
    
    // Update announcement
    const announcementPanel = document.getElementById('announcement-panel');
    const announcementText = document.getElementById('announcement-text');
    
    if (announcementPanel && announcementText) {
        if (state.announcement_visible && state.announcement) {
            announcementPanel.style.display = 'block';
            announcementText.textContent = state.announcement;
            
            // Add animation class if not already present
            if (!announcementPanel.classList.contains('animate-slide-in')) {
                announcementPanel.classList.add('animate-slide-in');
            }
        } else {
            announcementPanel.style.display = 'none';
            announcementPanel.classList.remove('animate-slide-in');
        }
    }
};

/**
 * Initialize presenter-specific event handlers
 */
function initPresenterInterface() {
    // Slide navigation buttons
    document.getElementById('prev-slide')?.addEventListener('click', function() {
        sendMessage('slide_control', { command: 'previous_slide' });
    });
    
    document.getElementById('next-slide')?.addEventListener('click', function() {
        sendMessage('slide_control', { command: 'next_slide' });
    });
    
    // Go to specific slide
    document.getElementById('go-to-slide-btn')?.addEventListener('click', function() {
        const slideNumber = parseInt(document.getElementById('go-to-slide').value);
        if (slideNumber && slideNumber > 0 && slideNumber <= state.total_slides) {
            sendMessage('slide_control', { command: 'goto_slide', slide: slideNumber });
        }
    });
    
    // Request more time
    document.getElementById('request-more-time')?.addEventListener('click', function() {
        sendMessage('announcement', { 
            message: `${state.current_presenter} has requested more time`, 
            visible: true 
        });
        
        // Show confirmation
        alert('Time extension request sent to moderator');
    });
    
    // Keyboard navigation
    document.addEventListener('keydown', function(event) {
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
            // Don't intercept keys when typing in form elements
            return;
        }
        
        // Arrow right or space for next slide
        if (event.key === 'ArrowRight' || event.key === ' ') {
            sendMessage('slide_control', { command: 'next_slide' });
            event.preventDefault();
        }
        
        // Arrow left for previous slide
        if (event.key === 'ArrowLeft') {
            sendMessage('slide_control', { command: 'previous_slide' });
            event.preventDefault();
        }
    });
}

// Initialize the presenter interface on page load
document.addEventListener('DOMContentLoaded', initPresenterInterface);