/**
 * Main JavaScript functionality for Conference Presentation System
 */

// Global state
let state = {
    timer_seconds: 600,
    timer_running: false,
    current_presenter: "No presenter",
    current_topic: "Welcome to the Conference",
    announcement: "",
    announcement_visible: false,
    current_slide: 1,
    total_slides: 30,
    device_status: {
        main: "UNKNOWN",
        backup: "UNKNOWN",
        moderator: "UNKNOWN"
    },
    system_health: {
        cpu: 0,
        memory: 0,
        disk: 0,
        network: "OK"
    },
    connected_clients: 0
};

// WebSocket connection
let socket;
let reconnectAttempts = 0;
const maxReconnectAttempts = 10;
const reconnectDelay = 3000; // ms

/**
 * Connect to the WebSocket server
 */
function connectWebSocket() {
    // Get the correct WebSocket URL based on the current URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    // Update connection status UI if element exists
    const connectionStatus = document.getElementById('connection-status');
    if (connectionStatus) {
        connectionStatus.textContent = 'Connecting...';
        connectionStatus.classList.remove('bg-green-600', 'bg-red-600');
        connectionStatus.classList.add('bg-gray-800');
    }
    
    // Create WebSocket connection
    socket = new WebSocket(wsUrl);
    
    // Connection opened
    socket.addEventListener('open', function(event) {
        console.log('Connected to WebSocket server');
        reconnectAttempts = 0;
        
        if (connectionStatus) {
            connectionStatus.textContent = 'Connected';
            connectionStatus.classList.remove('bg-gray-800', 'bg-red-600');
            connectionStatus.classList.add('bg-green-600');
        }
    });
    
    // Connection closed
    socket.addEventListener('close', function(event) {
        console.log('Disconnected from WebSocket server');
        
        if (connectionStatus) {
            connectionStatus.textContent = 'Disconnected';
            connectionStatus.classList.remove('bg-gray-800', 'bg-green-600');
            connectionStatus.classList.add('bg-red-600');
        }
        
        // Try to reconnect
        if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++;
            console.log(`Attempting to reconnect (${reconnectAttempts}/${maxReconnectAttempts})...`);
            setTimeout(connectWebSocket, reconnectDelay);
        } else {
            console.error('Maximum reconnection attempts reached');
            if (connectionStatus) {
                connectionStatus.textContent = 'Connection failed';
            }
        }
    });
    
    // Listen for messages
    socket.addEventListener('message', function(event) {
        try {
            const data = JSON.parse(event.data);
            updateState(data);
            updateUI();
        } catch (error) {
            console.error('Error parsing message:', error);
        }
    });
    
    // Connection error
    socket.addEventListener('error', function(event) {
        console.error('WebSocket error:', event);
    });
}

/**
 * Update global state with new data
 * @param {Object} newState - The new state data
 */
function updateState(newState) {
    // Update the state object with new values
    for (const key in newState) {
        if (newState.hasOwnProperty(key)) {
            state[key] = newState[key];
        }
    }
    
    // Trigger custom event for state update
    const event = new CustomEvent('stateUpdate', { detail: state });
    document.dispatchEvent(event);
}

/**
 * Update UI elements based on current state
 */
function updateUI() {
    // This function will be overridden in page-specific JS files
    // with implementations relevant to each page
}

/**
 * Send a message to the server
 * @param {string} type - Message type
 * @param {Object} data - Message data
 */
function sendMessage(type, data) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        const message = {
            type: type,
            data: data
        };
        
        socket.send(JSON.stringify(message));
    } else {
        console.error('Cannot send message: WebSocket is not connected');
    }
}

/**
 * Format seconds as MM:SS
 * @param {number} seconds - Number of seconds
 * @returns {string} Formatted time string
 */
function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Get timer display color based on time remaining
 * @param {number} seconds - Number of seconds remaining
 * @returns {string} CSS class for the timer
 */
function getTimerColorClass(seconds) {
    if (seconds <= 30) {
        return 'timer-red';
    } else if (seconds <= 60) {
        return 'timer-yellow';
    } else {
        return 'timer-green';
    }
}

/**
 * Initialize the application
 */
function initApp() {
    // Connect to WebSocket server
    connectWebSocket();
    
    // Listen for state updates
    document.addEventListener('stateUpdate', (event) => {
        // This event will be handled in page-specific code
    });
    
    // Page-specific initialization will be called from each page
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initApp);