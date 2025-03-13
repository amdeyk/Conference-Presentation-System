import sys
import json
import os
import time
import logging
from datetime import datetime
import threading
import psutil
import paho.mqtt.client as mqtt
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QFrame, QPushButton, QComboBox)
from PyQt5.QtCore import QTimer, Qt, pyqtSlot, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("presentation_system.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PresentationSystem")

# System configuration
CONFIG = {
    "device_id": str(uuid.uuid4()),
    "device_role": "MAIN",  # MAIN or BACKUP
    "mqtt_broker": "localhost",
    "mqtt_port": 1883,
    "mqtt_topic_prefix": "conference/",
    "api_host": "0.0.0.0",
    "api_port": 8000,
    "webrtc_enabled": True,
    "backup_check_interval": 10,  # seconds
    "health_check_interval": 30,  # seconds
    "powerpoint_enabled": True,
    "is_active": True,
}

# Global state
STATE = {
    "current_presenter": "No presenter",
    "current_topic": "Welcome to the Conference",
    "timer_seconds": 600,  # 10 minutes default
    "timer_running": False,
    "timer_end_time": None,
    "announcement": "",
    "announcement_visible": False,
    "current_slide": 1,
    "total_slides": 30,
    "device_status": {
        "main": "ONLINE",
        "backup": "UNKNOWN",
        "moderator": "UNKNOWN"
    },
    "system_health": {
        "cpu": 0,
        "memory": 0,
        "disk": 0,
        "network": "OK"
    },
    "connected_clients": 0
}

# FastAPI App
app = FastAPI(title="Conference Presentation System")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# WebSocket connections
websocket_connections = []

class SystemMonitor(QThread):
    update_signal = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.running = True
    
    def run(self):
        while self.running:
            try:
                # Collect system stats
                health_data = {
                    "cpu": psutil.cpu_percent(),
                    "memory": psutil.virtual_memory().percent,
                    "disk": psutil.disk_usage('/').percent,
                    "network": "OK" 
                }
                
                # Update global state
                STATE["system_health"] = health_data
                
                # Emit signal with updated data
                self.update_signal.emit(health_data)
                
                # Publish to MQTT
                mqtt_client.publish(
                    f"{CONFIG['mqtt_topic_prefix']}health/{CONFIG['device_id']}", 
                    json.dumps(health_data)
                )
                
                # Check if we need to alert
                if health_data["cpu"] > 85 or health_data["memory"] > 80:
                    logger.warning(f"System resources critical: CPU {health_data['cpu']}%, Memory {health_data['memory']}%")
                
                time.sleep(CONFIG["health_check_interval"])
            except Exception as e:
                logger.error(f"Error in system monitor: {str(e)}")
                time.sleep(5)  # Wait and retry
    
    def stop(self):
        self.running = False

class BackupMonitor(QThread):
    status_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.running = True
    
    def run(self):
        while self.running:
            try:
                # In a real system, you'd check the backup laptop's status
                # For now, we'll simulate this
                mqtt_client.publish(
                    f"{CONFIG['mqtt_topic_prefix']}heartbeat/{CONFIG['device_id']}", 
                    json.dumps({
                        "timestamp": time.time(),
                        "role": CONFIG["device_role"],
                        "status": "ACTIVE" if CONFIG["is_active"] else "STANDBY"
                    })
                )
                
                time.sleep(CONFIG["backup_check_interval"])
            except Exception as e:
                logger.error(f"Error in backup monitor: {str(e)}")
                time.sleep(5)  # Wait and retry
    
    def stop(self):
        self.running = False

class PowerPointController:
    def __init__(self):
        self.connected = False
        # In a real implementation, we would connect to PowerPoint via COM or another method
    
    def connect(self):
        try:
            # Simulate PowerPoint connection
            logger.info("Connected to PowerPoint")
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to PowerPoint: {str(e)}")
            self.connected = False
            return False
    
    def next_slide(self):
        if not self.connected:
            return False
        
        try:
            # Simulate advancing to next slide
            STATE["current_slide"] += 1
            if STATE["current_slide"] > STATE["total_slides"]:
                STATE["current_slide"] = STATE["total_slides"]
            
            logger.info(f"Advanced to slide {STATE['current_slide']}")
            return True
        except Exception as e:
            logger.error(f"Error advancing slide: {str(e)}")
            return False
    
    def previous_slide(self):
        if not self.connected:
            return False
        
        try:
            # Simulate going back to previous slide
            STATE["current_slide"] -= 1
            if STATE["current_slide"] < 1:
                STATE["current_slide"] = 1
            
            logger.info(f"Went back to slide {STATE['current_slide']}")
            return True
        except Exception as e:
            logger.error(f"Error going to previous slide: {str(e)}")
            return False
    
    def goto_slide(self, slide_number):
        if not self.connected:
            return False
        
        try:
            # Simulate going to specific slide
            if 1 <= slide_number <= STATE["total_slides"]:
                STATE["current_slide"] = slide_number
                logger.info(f"Went to slide {STATE['current_slide']}")
                return True
            else:
                logger.warning(f"Invalid slide number: {slide_number}")
                return False
        except Exception as e:
            logger.error(f"Error going to slide {slide_number}: {str(e)}")
            return False

# MQTT Callbacks
def on_mqtt_connect(client, userdata, flags, rc):
    logger.info(f"Connected to MQTT broker with result code {rc}")
    
    # Subscribe to relevant topics
    client.subscribe(f"{CONFIG['mqtt_topic_prefix']}timer/#")
    client.subscribe(f"{CONFIG['mqtt_topic_prefix']}presenter/#")
    client.subscribe(f"{CONFIG['mqtt_topic_prefix']}announcement/#")
    client.subscribe(f"{CONFIG['mqtt_topic_prefix']}heartbeat/#")
    client.subscribe(f"{CONFIG['mqtt_topic_prefix']}control/#")

def on_mqtt_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode())
        logger.debug(f"MQTT message: {topic} - {payload}")
        
        # Process message based on topic
        if topic.startswith(f"{CONFIG['mqtt_topic_prefix']}timer/"):
            if "seconds" in payload:
                STATE["timer_seconds"] = payload["seconds"]
            if "running" in payload:
                STATE["timer_running"] = payload["running"]
                if STATE["timer_running"]:
                    STATE["timer_end_time"] = time.time() + STATE["timer_seconds"]
                else:
                    STATE["timer_end_time"] = None
                    
        elif topic.startswith(f"{CONFIG['mqtt_topic_prefix']}presenter/"):
            if "name" in payload:
                STATE["current_presenter"] = payload["name"]
            if "topic" in payload:
                STATE["current_topic"] = payload["topic"]
                
        elif topic.startswith(f"{CONFIG['mqtt_topic_prefix']}announcement/"):
            if "message" in payload:
                STATE["announcement"] = payload["message"]
                STATE["announcement_visible"] = True
                
        elif topic.startswith(f"{CONFIG['mqtt_topic_prefix']}heartbeat/"):
            if "role" in payload and payload["role"] == "BACKUP":
                STATE["device_status"]["backup"] = "ONLINE"
            elif "role" in payload and payload["role"] == "MODERATOR":
                STATE["device_status"]["moderator"] = "ONLINE"
                
        elif topic.startswith(f"{CONFIG['mqtt_topic_prefix']}control/"):
            if "command" in payload:
                if payload["command"] == "next_slide":
                    powerpoint.next_slide()
                elif payload["command"] == "previous_slide":
                    powerpoint.previous_slide()
                elif payload["command"] == "goto_slide" and "slide" in payload:
                    powerpoint.goto_slide(payload["slide"])
        
        # Broadcast updates to WebSocket clients
        asyncio.run(broadcast_state_update())
    except Exception as e:
        logger.error(f"Error processing MQTT message: {str(e)}")

async def broadcast_state_update():
    """Broadcast state update to all connected WebSocket clients"""
    if not websocket_connections:
        return
    
    # Prepare the message
    message = json.dumps(STATE)
    
    # Send to all connected clients
    for websocket in websocket_connections:
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {str(e)}")
            # Remove failed connection
            if websocket in websocket_connections:
                websocket_connections.remove(websocket)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Conference Presentation System")
        self.setMinimumSize(1024, 768)
        
        # Create central widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Add presenter section at top
        presenter_frame = QFrame()
        presenter_frame.setFrameShape(QFrame.StyledPanel)
        presenter_frame.setStyleSheet("background-color: #2c3e50; color: white;")
        presenter_layout = QVBoxLayout(presenter_frame)
        
        self.presenter_label = QLabel(STATE["current_presenter"])
        self.presenter_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.presenter_label.setAlignment(Qt.AlignCenter)
        
        self.topic_label = QLabel(STATE["current_topic"])
        self.topic_label.setFont(QFont("Arial", 20))
        self.topic_label.setAlignment(Qt.AlignCenter)
        
        presenter_layout.addWidget(self.presenter_label)
        presenter_layout.addWidget(self.topic_label)
        
        # Add timer section in middle
        timer_frame = QFrame()
        timer_frame.setFrameShape(QFrame.StyledPanel)
        timer_frame.setStyleSheet("background-color: #34495e; color: white;")
        timer_layout = QVBoxLayout(timer_frame)
        
        self.timer_label = QLabel(self.format_time(STATE["timer_seconds"]))
        self.timer_label.setFont(QFont("Arial", 72, QFont.Bold))
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setStyleSheet("color: #2ecc71;")  # Green when plenty of time
        
        timer_layout.addWidget(self.timer_label)
        
        # Add announcement section at bottom
        announcement_frame = QFrame()
        announcement_frame.setFrameShape(QFrame.StyledPanel)
        announcement_frame.setStyleSheet("background-color: #2c3e50; color: white;")
        announcement_layout = QVBoxLayout(announcement_frame)
        
        self.announcement_label = QLabel("")
        self.announcement_label.setFont(QFont("Arial", 18))
        self.announcement_label.setAlignment(Qt.AlignCenter)
        self.announcement_label.setWordWrap(True)
        
        announcement_layout.addWidget(self.announcement_label)
        announcement_frame.setVisible(False)
        self.announcement_frame = announcement_frame
        
        # Add slide indicator
        slide_frame = QFrame()
        slide_frame.setFrameShape(QFrame.StyledPanel)
        slide_frame.setStyleSheet("background-color: #34495e; color: white;")
        slide_layout = QHBoxLayout(slide_frame)
        
        self.slide_label = QLabel(f"Slide {STATE['current_slide']}/{STATE['total_slides']}")
        self.slide_label.setFont(QFont("Arial", 16))
        self.slide_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        slide_layout.addStretch()
        slide_layout.addWidget(self.slide_label)
        
        # Add status indicator
        status_frame = QFrame()
        status_frame.setFrameShape(QFrame.StyledPanel)
        status_frame.setStyleSheet("background-color: #2c3e50; color: white;")
        status_layout = QHBoxLayout(status_frame)
        
        self.status_label = QLabel("Main: ONLINE | Backup: UNKNOWN | Network: OK")
        self.status_label.setFont(QFont("Arial", 10))
        
        status_layout.addWidget(self.status_label)
        
        # Add system control buttons (for demonstration)
        control_frame = QFrame()
        control_layout = QHBoxLayout(control_frame)
        
        self.start_button = QPushButton("Start Timer")
        self.stop_button = QPushButton("Stop Timer")
        self.reset_button = QPushButton("Reset Timer")
        
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.reset_button)
        
        # Connect buttons
        self.start_button.clicked.connect(self.start_timer)
        self.stop_button.clicked.connect(self.stop_timer)
        self.reset_button.clicked.connect(self.reset_timer)
        
        # Arrange main layout
        main_layout.addWidget(presenter_frame, 2)
        main_layout.addWidget(timer_frame, 4)
        main_layout.addWidget(announcement_frame, 2)
        main_layout.addWidget(slide_frame, 1)
        main_layout.addWidget(status_frame, 1)
        main_layout.addWidget(control_frame, 1)
        
        # Set the central widget
        self.setCentralWidget(central_widget)
        
        # Setup timer for UI updates
        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self.update_ui)
        self.ui_timer.start(100)  # Update every 100ms
    
    def format_time(self, seconds):
        """Format seconds as MM:SS"""
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def update_ui(self):
        """Update UI elements based on current state"""
        # Update presenter info
        self.presenter_label.setText(STATE["current_presenter"])
        self.topic_label.setText(STATE["current_topic"])
        
        # Update timer
        if STATE["timer_running"] and STATE["timer_end_time"]:
            remaining = max(0, int(STATE["timer_end_time"] - time.time()))
            STATE["timer_seconds"] = remaining
        
        self.timer_label.setText(self.format_time(STATE["timer_seconds"]))
        
        # Set timer color based on remaining time
        if STATE["timer_seconds"] <= 30:
            self.timer_label.setStyleSheet("color: #e74c3c;")  # Red when < 30 seconds
        elif STATE["timer_seconds"] <= 60:
            self.timer_label.setStyleSheet("color: #f39c12;")  # Orange when < 1 minute
        else:
            self.timer_label.setStyleSheet("color: #2ecc71;")  # Green otherwise
        
        # Update announcement
        if STATE["announcement_visible"] and STATE["announcement"]:
            self.announcement_label.setText(STATE["announcement"])
            self.announcement_frame.setVisible(True)
        else:
            self.announcement_frame.setVisible(False)
        
        # Update slide indicator
        self.slide_label.setText(f"Slide {STATE['current_slide']}/{STATE['total_slides']}")
        
        # Update status indicator
        status_text = f"Main: {STATE['device_status']['main']} | "
        status_text += f"Backup: {STATE['device_status']['backup']} | "
        status_text += f"Network: {STATE['system_health']['network']}"
        self.status_label.setText(status_text)
    
    @pyqtSlot()
    def start_timer(self):
        STATE["timer_running"] = True
        STATE["timer_end_time"] = time.time() + STATE["timer_seconds"]
        logger.info("Timer started")
        
        # Publish to MQTT
        mqtt_client.publish(
            f"{CONFIG['mqtt_topic_prefix']}timer/control", 
            json.dumps({"running": True})
        )
    
    @pyqtSlot()
    def stop_timer(self):
        STATE["timer_running"] = False
        STATE["timer_end_time"] = None
        logger.info("Timer stopped")
        
        # Publish to MQTT
        mqtt_client.publish(
            f"{CONFIG['mqtt_topic_prefix']}timer/control", 
            json.dumps({"running": False})
        )
    
    @pyqtSlot()
    def reset_timer(self):
        STATE["timer_seconds"] = 600  # Reset to 10 minutes
        STATE["timer_running"] = False
        STATE["timer_end_time"] = None
        logger.info("Timer reset")
        
        # Publish to MQTT
        mqtt_client.publish(
            f"{CONFIG['mqtt_topic_prefix']}timer/control", 
            json.dumps({"seconds": 600, "running": False})
        )

# FastAPI routes
@app.get("/", response_class=HTMLResponse)
async def get_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/moderator", response_class=HTMLResponse)
async def get_moderator(request: Request):
    return templates.TemplateResponse("moderator.html", {"request": request})

@app.get("/presenter", response_class=HTMLResponse)
async def get_presenter(request: Request):
    return templates.TemplateResponse("presenter.html", {"request": request})

@app.get("/audience", response_class=HTMLResponse)
async def get_audience(request: Request):
    return templates.TemplateResponse("audience.html", {"request": request})

@app.get("/api/state")
async def get_state():
    return STATE

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        # Send current state immediately after connection
        await websocket.send_text(json.dumps(STATE))
        
        # Update connected clients count
        STATE["connected_clients"] = len(websocket_connections)
        
        # Process incoming messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if "type" in message:
                if message["type"] == "timer_control":
                    # Forward to MQTT
                    mqtt_client.publish(
                        f"{CONFIG['mqtt_topic_prefix']}timer/control", 
                        json.dumps(message["data"])
                    )
                
                elif message["type"] == "presenter_update":
                    # Forward to MQTT
                    mqtt_client.publish(
                        f"{CONFIG['mqtt_topic_prefix']}presenter/update", 
                        json.dumps(message["data"])
                    )
                
                elif message["type"] == "announcement":
                    # Forward to MQTT
                    mqtt_client.publish(
                        f"{CONFIG['mqtt_topic_prefix']}announcement/new", 
                        json.dumps(message["data"])
                    )
                
                elif message["type"] == "slide_control":
                    # Forward to MQTT
                    mqtt_client.publish(
                        f"{CONFIG['mqtt_topic_prefix']}control/slide", 
                        json.dumps(message["data"])
                    )
            
            # Broadcast updated state to all clients
            await broadcast_state_update()
    
    except WebSocketDisconnect:
        # Clean up on disconnect
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)
        STATE["connected_clients"] = len(websocket_connections)
    
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)
        STATE["connected_clients"] = len(websocket_connections)

class APIServer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
    
    def run(self):
        uvicorn.run(app, host=CONFIG["api_host"], port=CONFIG["api_port"])

def main():
    # Initialize PowerPoint controller
    global powerpoint
    powerpoint = PowerPointController()
    if CONFIG["powerpoint_enabled"]:
        powerpoint.connect()
    
    # Setup MQTT client
    global mqtt_client
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_message = on_mqtt_message
    
    try:
        mqtt_client.connect(CONFIG["mqtt_broker"], CONFIG["mqtt_port"], 60)
        mqtt_client.loop_start()
    except Exception as e:
        logger.error(f"Failed to connect to MQTT broker: {str(e)}")
    
    # Start monitoring threads
    system_monitor = SystemMonitor()
    system_monitor.start()
    
    backup_monitor = BackupMonitor()
    backup_monitor.start()
    
    # Start API server in a separate thread
    api_server = APIServer()
    api_server.start()
    
    # Start the Qt application
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    # Run the event loop
    exit_code = app.exec_()
    
    # Clean up
    system_monitor.stop()
    backup_monitor.stop()
    mqtt_client.loop_stop()
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())