/**
 * Audience interface JavaScript for Conference Presentation System
 */

// WebRTC client for screen sharing
let webrtcClient;

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
    }
    
    // Update slide indicator
    const slideIndicator = document.getElementById('slide-indicator');
    if (slideIndicator) {
        slideIndicator.textContent = `Slide: ${state.current_slide}/${state.total_slides}`;
    }
    
    // Update announcement banner
    const announcementBanner = document.getElementById('announcement-banner');
    const announcementText = document.getElementById('announcement-text');
    
    if (announcementBanner && announcementText) {
        if (state.announcement_visible && state.announcement) {
            announcementBanner.style.display = 'block';
            announcementText.textContent = state.announcement;
            
            // Add animation class if not already present
            if (!announcementBanner.classList.contains('animate-slide-in')) {
                announcementBanner.classList.add('animate-slide-in');
            }
        } else {
            announcementBanner.style.display = 'none';
            announcementBanner.classList.remove('animate-slide-in');
        }
    }
    
    // Update status indicators
    updateStatusIndicators();
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
            ? 'bg-green-100 text-green-800 p-2 rounded text-center' 
            : 'bg-red-100 text-red-800 p-2 rounded text-center';
    }
    
    // Backup status
    const backupStatus = document.getElementById('backup-status');
    if (backupStatus) {
        backupStatus.textContent = state.device_status.backup;
        
        let className = 'p-2 rounded text-center ';
        if (state.device_status.backup === 'ONLINE') {
            if (state.active_device === 'BACKUP') {
                className += 'bg-blue-100 text-blue-800';
            } else {
                className += 'bg-green-100 text-green-800';
            }
        } else if (state.device_status.backup === 'UNKNOWN') {
            className += 'bg-gray-100 text-gray-800';
        } else {
            className += 'bg-red-100 text-red-800';
        }
        
        backupStatus.className = className;
    }
}

/**
 * Initialize WebRTC for screen sharing
 */
function initWebRTC() {
    // Get video element
    const videoElement = document.getElementById('screen-share-video');
    if (!videoElement) return;
    
    // Create WebRTC client
    webrtcClient = new WebRTCClient(videoElement);
    
    // Connect
    webrtcClient.connect()
        .then(success => {
            if (success) {
                console.log('WebRTC connection established');
                
                // Hide placeholder
                const placeholder = document.querySelector('.screen-placeholder');
                if (placeholder) {
                    placeholder.style.display = 'none';
                }
            } else {
                console.error('Failed to establish WebRTC connection');
            }
        })
        .catch(error => {
            console.error('Error connecting to WebRTC:', error);
        });
    
    // Handle page unload
    window.addEventListener('beforeunload', () => {
        if (webrtcClient) {
            webrtcClient.disconnect();
        }
    });
}

/**
 * Initialize audience-specific functionality
 */
function initAudienceInterface() {
    // Initialize WebRTC if available
    if (typeof WebRTCClient !== 'undefined') {
        initWebRTC();
    } else {
        console.warn('WebRTC client not available');
    }
}

// Initialize the audience interface on page load
document.addEventListener('DOMContentLoaded', initAudienceInterface);

/**
 * WebRTC client for screen sharing
 */
class WebRTCClient {
    constructor(videoElement) {
        this.videoElement = videoElement;
        this.peerConnection = null;
        this.pcId = null;
    }
    
    async connect() {
        try {
            // Create a new RTCPeerConnection
            this.peerConnection = new RTCPeerConnection({
                iceServers: [
                    { urls: 'stun:stun.l.google.com:19302' }
                ]
            });
            
            // Set up event handlers
            this.peerConnection.addEventListener('track', (event) => {
                if (event.track.kind === 'video') {
                    this.videoElement.srcObject = event.streams[0];
                }
            });
            
            this.peerConnection.addEventListener('iceconnectionstatechange', () => {
                console.log('ICE connection state:', this.peerConnection.iceConnectionState);
            });
            
            // Get offer from server
            const response = await fetch('/api/webrtc/offer');
            const { sdp, type, id } = await response.json();
            this.pcId = id;
            
            // Set remote description (the offer)
            await this.peerConnection.setRemoteDescription({ type, sdp });
            
            // Create answer
            const answer = await this.peerConnection.createAnswer();
            await this.peerConnection.setLocalDescription(answer);
            
            // Send answer to server
            await fetch('/api/webrtc/answer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    id: this.pcId,
                    sdp: answer.sdp,
                    type: answer.type
                })
            });
            
            console.log('WebRTC connection established');
            return true;
        } catch (error) {
            console.error('Error establishing WebRTC connection:', error);
            this.disconnect();
            return false;
        }
    }
    
    disconnect() {
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }
        
        if (this.videoElement) {
            this.videoElement.srcObject = null;
        }
        
        if (this.pcId) {
            fetch('/api/webrtc/disconnect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ id: this.pcId })
            }).catch(error => {
                console.error('Error disconnecting:', error);
            });
            
            this.pcId = null;
        }
        
        console.log('WebRTC disconnected');
    }
}