import sys
import json
import os
import time
import logging
import threading
import requests
import psutil
import paho.mqtt.client as mqtt
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QFrame, QPushButton)
from PyQt5.QtCore import QTimer, Qt, pyqtSlot, QThread, pyqtSignal
from PyQt5.QtGui import QFont

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("backup_system.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BackupSystem")

# System configuration
CONFIG = {
    "device_id": "backup-" + str(psutil.Process().pid),
    "device_role": "BACKUP",
    "mqtt_broker": "localhost",
    "mqtt_port": 1883,
    "mqtt_topic_prefix": "conference/",
    "main_api_url": "http://localhost:8000",
    "backup_check_interval": 5,  # seconds
    "health_check_interval": 30,  # seconds
    "failover_timeout": 15,  # seconds without heartbeat before failover
    "powerpoint_enabled": True,
    "is_active": False,  # Backup starts in standby mode
}

# Global state (synced from main)
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
        "backup": "ONLINE",
        "moderator": "UNKNOWN"
    },
    "system_health": {
        "cpu": 0,
        "memory": 0,
        "disk": 0,
        "network": "OK"
    },
    "main_last_heartbeat": time.time(),
    "connected_clients": 0
}

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
                
                # Publish to MQTT (only if active or for heartbeat)
                mqtt_client.publish(
                    f"{CONFIG['mqtt_topic_prefix']}health/{CONFIG['device_id']}", 
                    json.dumps(health_data)
                )
                
                time.sleep(CONFIG["health_check_interval"])
            except Exception as e:
                logger.error(f"Error in system monitor: {str(e)}")
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
            if "role" in payload and payload["role"] == "MAIN":
                STATE["main_last_heartbeat"] = time.time()
                STATE["device_status"]["main"] = "ONLINE"
            elif "role" in payload and payload["role"] == "MODERATOR":
                STATE["device_status"]["moderator"] = "ONLINE"
                
        elif topic.startswith(f"{CONFIG['mqtt_topic_prefix']}control/"):
            if "command" in payload and CONFIG["is_active"]:
                if payload["command"] == "next_slide":
                    powerpoint.next_slide()
                elif payload["command"] == "previous_slide":
                    powerpoint.previous_slide()
                elif payload["command"] == "goto_slide" and "slide" in payload:
                    powerpoint.goto_slide(payload["slide"])
    
    except Exception as e:
        logger.error(f"Error processing MQTT message: {str(e)}")

class BackupWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Backup Controller - Conference System")
        self.setMinimumSize(800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Add status section
        status_frame = QFrame()
        status_frame.setFrameShape(QFrame.StyledPanel)
        status_frame.setStyleSheet("background-color: #2c3e50; color: white;")
        status_layout = QVBoxLayout(status_frame)
        
        self.role_label = QLabel("BACKUP (STANDBY)")
        self.role_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.role_label.setAlignment(Qt.AlignCenter)
        
        self.main_status_label = QLabel("Main Laptop: CHECKING...")
        self.main_status_label.setFont(QFont("Arial", 18))
        self.main_status_label.setAlignment(Qt.AlignCenter)
        
        status_layout.addWidget(self.role_label)
        status_layout.addWidget(self.main_status_label)
        
        # Add presenter section
        presenter_frame = QFrame()
        presenter_frame.setFrameShape(QFrame.StyledPanel)
        presenter_frame.setStyleSheet("background-color: #34495e; color: white;")
        presenter_layout = QVBoxLayout(presenter_frame)
        
        self.presenter_label = QLabel(f"Presenter: {STATE['current_presenter']}")
        self.presenter_label.setFont(QFont("Arial", 16))
        self.presenter_label.setAlignment(Qt.AlignCenter)
        
        self.topic_label = QLabel(f"Topic: {STATE['current_topic']}")
        self.topic_label.setFont(QFont("Arial", 14))
        self.topic_label.setAlignment(Qt.AlignCenter)
        
        presenter_layout.addWidget(self.presenter_label)
        presenter_layout.addWidget(self.topic_label)
        
        # Add timer section
        timer_frame = QFrame()
        timer_frame.setFrameShape(QFrame.StyledPanel)
        timer_frame.setStyleSheet("background-color: #34495e; color: white;")
        timer_layout = QVBoxLayout(timer_frame)
        
        self.timer_label = QLabel(self.format_time(STATE["timer_seconds"]))
        self.timer_label.setFont(QFont("Arial", 48, QFont.Bold))
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setStyleSheet("color: #2ecc71;")  # Green when plenty of time
        
        timer_layout.addWidget(self.timer_label)
        
        # Add slide section
        slide_frame = QFrame()
        slide_frame.setFrameShape(QFrame.StyledPanel)
        slide_frame.setStyleSheet("background-color: #34495e; color: white;")
        slide_layout = QVBoxLayout(slide_frame)
        
        self.slide_label = QLabel(f"Slide: {STATE['current_slide']}/{STATE['total_slides']}")
        self.slide_label.setFont(QFont("Arial", 16))
        self.slide_label.setAlignment(Qt.AlignCenter)
        
        slide_layout.addWidget(self.slide_label)
        
        # Add control section
        control_frame = QFrame()
        control_layout = QHBoxLayout(control_frame)
        
        self.takeover_button = QPushButton("TAKE OVER (FAILOVER)")
        self.takeover_button.setFont(QFont("Arial", 14, QFont.Bold))
        self.takeover_button.setStyleSheet("background-color: #e74c3c; color: white; padding: 10px;")
        
        self.standby_button = QPushButton("RETURN TO STANDBY")
        self.standby_button.setFont(QFont("Arial", 14))
        self.standby_button.setStyleSheet("background-color: #3498db; color: white; padding: 10px;")
        self.standby_button.setEnabled(False)  # Disabled initially
        
        control_layout.addWidget(self.takeover_button)
        control_layout.addWidget(self.standby_button)
        
        # Connect buttons
        self.takeover_button.clicked.connect(self.activate_backup)
        self.standby_button.clicked.connect(self.deactivate_backup)
        
        # Arrange main layout
        main_layout.addWidget(status_frame, 2)
        main_layout.addWidget(presenter_frame, 2)
        main_layout.addWidget(timer_frame, 3)
        main_layout.addWidget(slide_frame, 1)
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
        # Update role label
        if CONFIG["is_active"]:
            self.role_label.setText("BACKUP (ACTIVE)")
            self.role_label.setStyleSheet("color: #e74c3c;")  # Red when active
            self.takeover_button.setEnabled(False)
            self.standby_button.setEnabled(True)
        else:
            self.role_label.setText("BACKUP (STANDBY)")
            self.role_label.setStyleSheet("color: #2ecc71;")  # Green when standby
            self.takeover_button.setEnabled(True)
            self.standby_button.setEnabled(False)
        
        # Update main status
        if STATE["device_status"]["main"] == "ONLINE":
            self.main_status_label.setText("Main Laptop: ONLINE")
            self.main_status_label.setStyleSheet("color: #2ecc71;")  # Green
        else:
            self.main_status_label.setText("Main Laptop: OFFLINE")
            self.main_status_label.setStyleSheet("color: #e74c3c;")  # Red
        
        # Update presenter info
        self.presenter_label.setText(f"Presenter: {STATE['current_presenter']}")
        self.topic_label.setText(f"Topic: {STATE['current_topic']}")
        
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
        
        # Update slide indicator
        self.slide_label.setText(f"Slide: {STATE['current_slide']}/{STATE['total_slides']}")
    
    @pyqtSlot()
    def activate_backup(self):
        """Activate backup mode (take over from main)"""
        CONFIG["is_active"] = True
        logger.warning("BACKUP ACTIVATED: Taking over from main laptop")
        
        # Publish takeover message
        mqtt_client.publish(
            f"{CONFIG['mqtt_topic_prefix']}control/failover", 
            json.dumps({
                "device_id": CONFIG["device_id"],
                "timestamp": time.time(),
                "action": "TAKEOVER"
            })
        )
        
        # Connect to PowerPoint if needed
        if CONFIG["powerpoint_enabled"] and not powerpoint.connected:
            powerpoint.connect()
    
    @pyqtSlot()
    def deactivate_backup(self):
        """Return to standby mode"""
        CONFIG["is_active"] = False
        logger.info("BACKUP DEACTIVATED: Returning to standby mode")
        
        # Publish standby message
        mqtt_client.publish(
            f"{CONFIG['mqtt_topic_prefix']}control/failover", 
            json.dumps({
                "device_id": CONFIG["device_id"],
                "timestamp": time.time(),
                "action": "STANDBY"
            })
        )

def main():
    # Initialize PowerPoint controller
    global powerpoint
    powerpoint = PowerPointController()
    # Don't connect to PowerPoint until activated
    
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
    
    main_monitor = MainMonitor()
    main_monitor.status_signal.connect(lambda status: logger.info(f"Main laptop status: {status}"))
    main_monitor.failover_signal.connect(lambda: window.activate_backup() if window else None)
    main_monitor.start()
    
    # Start the Qt application
    app = QApplication(sys.argv)
    global window
    window = BackupWindow()
    window.show()
    
    # Run the event loop
    exit_code = app.exec_()
    
    # Clean up
    system_monitor.stop()
    main_monitor.stop()
    mqtt_client.loop_stop()
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())

class MainMonitor(QThread):
    status_signal = pyqtSignal(str)
    failover_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.running = True
    
    def run(self):
        while self.running:
            try:
                # Send heartbeat
                mqtt_client.publish(
                    f"{CONFIG['mqtt_topic_prefix']}heartbeat/{CONFIG['device_id']}", 
                    json.dumps({
                        "timestamp": time.time(),
                        "role": CONFIG["device_role"],
                        "status": "ACTIVE" if CONFIG["is_active"] else "STANDBY"
                    })
                )
                
                # Check if main is alive
                time_since_heartbeat = time.time() - STATE["main_last_heartbeat"]
                
                if time_since_heartbeat > CONFIG["failover_timeout"]:
                    if not CONFIG["is_active"]:
                        logger.warning(f"Main laptop heartbeat timeout. Initiating failover...")
                        self.failover_signal.emit()
                    STATE["device_status"]["main"] = "OFFLINE"
                else:
                    STATE["device_status"]["main"] = "ONLINE"
                
                self.status_signal.emit(STATE["device_status"]["main"])
                
                # Try to fetch state from main (if it's online and we're not active)
                if STATE["device_status"]["main"] == "ONLINE" and not CONFIG["is_active"]:
                    try:
                        response = requests.get(f"{CONFIG['main_api_url']}/api/state", timeout=2)
                        if response.status_code == 200:
                            main_state = response.json()
                            # Sync only certain fields to avoid overriding local status
                            for key in ["current_presenter", "current_topic", "timer_seconds", 
                                      "timer_running", "announcement", "announcement_visible", 
                                      "current_slide", "total_slides"]:
                                if key in main_state:
                                    STATE[key] = main_state[key]
                    except requests.exceptions.RequestException:
                        # Can't connect to main API - this is expected if main is down
                        pass
                
                time.sleep(CONFIG["backup_check_interval"])
            except Exception as e:
                logger.error(f"Error in main monitor: {str(e)}")
                time.sleep(5)  # Wait and retry
    
    def stop(self):
        self.running = False