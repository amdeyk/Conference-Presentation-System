"""
System Monitor Module for the Conference Presentation System.
Monitors system health and performance metrics.
"""

import os
import sys
import time
import logging
import threading
import json
import platform
from typing import Dict, Any, Optional, Callable

# Configure logging
logger = logging.getLogger("SystemMonitor")

class SystemMonitor(threading.Thread):
    """
    Monitors system health metrics including CPU, memory, disk, and network.
    Runs in a separate thread and periodically reports metrics.
    """
    
    def __init__(self, config: Dict[str, Any], callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        """
        Initialize the system monitor.
        
        Args:
            config: System configuration dictionary
            callback: Optional callback function that receives the health data
        """
        super().__init__()
        self.daemon = True
        self.config = config
        self.callback = callback
        self.running = False
        self.interval = config.get("health_check_interval", 30)  # seconds
        self.cpu_threshold_warning = 80
        self.cpu_threshold_critical = 90
        self.memory_threshold_warning = 80
        self.memory_threshold_critical = 90
        self.disk_threshold_warning = 80
        self.disk_threshold_critical = 90
        
        # Import platform-specific modules
        try:
            import psutil
            self.psutil = psutil
        except ImportError:
            logger.error("psutil module not found. System monitoring will be limited.")
            self.psutil = None
        
        # Initialize health data
        self.health_data = {
            "cpu": 0,
            "memory": 0,
            "disk": 0,
            "network": "OK",
            "temperature": None,
            "battery": None,
            "uptime": 0,
            "timestamp": time.time(),
            "status": "OK"
        }
    
    def run(self):
        """Main thread function. Collects system metrics periodically."""
        self.running = True
        start_time = time.time()
        
        while self.running:
            try:
                # Update health data
                self._update_health_data()
                
                # Update uptime
                self.health_data["uptime"] = int(time.time() - start_time)
                
                # Update timestamp
                self.health_data["timestamp"] = time.time()
                
                # Determine overall status
                self._update_status()
                
                # Call callback if provided
                if self.callback:
                    self.callback(self.health_data)
                
                # Log warnings if thresholds exceeded
                self._log_warnings()
                
                # Sleep until next check
                time.sleep(self.interval)
            
            except Exception as e:
                logger.error(f"Error in system monitor: {str(e)}")
                time.sleep(5)  # Wait and retry on error
    
    def _update_health_data(self):
        """Update all health metrics."""
        # CPU usage
        self.health_data["cpu"] = self._get_cpu_usage()
        
        # Memory usage
        self.health_data["memory"] = self._get_memory_usage()
        
        # Disk usage
        self.health_data["disk"] = self._get_disk_usage()
        
        # Network status
        self.health_data["network"] = self._get_network_status()
        
        # System temperature (if available)
        temp = self._get_temperature()
        if temp is not None:
            self.health_data["temperature"] = temp
        
        # Battery status (if available)
        battery = self._get_battery_status()
        if battery is not None:
            self.health_data["battery"] = battery
    
    def _update_status(self):
        """Update the overall system status based on metrics."""
        if (self.health_data["cpu"] > self.cpu_threshold_critical or
            self.health_data["memory"] > self.memory_threshold_critical or
            self.health_data["disk"] > self.disk_threshold_critical or
            self.health_data["network"] != "OK"):
            self.health_data["status"] = "CRITICAL"
        
        elif (self.health_data["cpu"] > self.cpu_threshold_warning or
              self.health_data["memory"] > self.memory_threshold_warning or
              self.health_data["disk"] > self.disk_threshold_warning):
            self.health_data["status"] = "WARNING"
        
        else:
            self.health_data["status"] = "OK"
    
    def _log_warnings(self):
        """Log warnings if thresholds are exceeded."""
        if self.health_data["status"] == "CRITICAL":
            logger.warning(f"CRITICAL: System resources critical: "
                          f"CPU {self.health_data['cpu']}%, "
                          f"Memory {self.health_data['memory']}%, "
                          f"Disk {self.health_data['disk']}%, "
                          f"Network {self.health_data['network']}")
        
        elif self.health_data["status"] == "WARNING":
            logger.info(f"WARNING: System resources high: "
                       f"CPU {self.health_data['cpu']}%, "
                       f"Memory {self.health_data['memory']}%, "
                       f"Disk {self.health_data['disk']}%")
    
    def _get_cpu_usage(self) -> float:
        """Get CPU usage percentage."""
        if self.psutil:
            return self.psutil.cpu_percent()
        return 0
    
    def _get_memory_usage(self) -> float:
        """Get memory usage percentage."""
        if self.psutil:
            return self.psutil.virtual_memory().percent
        return 0
    
    def _get_disk_usage(self) -> float:
        """Get disk usage percentage."""
        if self.psutil:
            return self.psutil.disk_usage('/').percent
        return 0
    
    def _get_network_status(self) -> str:
        """Get network status."""
        try:
            # Simple check: Try to resolve a hostname
            import socket
            socket.gethostbyname("www.google.com")
            return "OK"
        except:
            return "ERROR"
    
    def _get_temperature(self) -> Optional[float]:
        """Get CPU temperature if available."""
        if self.psutil:
            try:
                temps = self.psutil.sensors_temperatures()
                if temps:
                    # Different systems report temperature differently
                    # Try to find CPU temperature
                    for name, entries in temps.items():
                        if entries:
                            # Return the first temperature reading
                            return entries[0].current
            except:
                pass
        return None
    
    def _get_battery_status(self) -> Optional[Dict[str, Any]]:
        """Get battery status if available."""
        if self.psutil:
            try:
                battery = self.psutil.sensors_battery()
                if battery:
                    return {
                        "percent": battery.percent,
                        "power_plugged": battery.power_plugged,
                        "seconds_left": battery.secsleft if battery.secsleft != -1 else None
                    }
            except:
                pass
        return None
    
    def get_health_data(self) -> Dict[str, Any]:
        """Get the current health data."""
        return self.health_data
    
    def stop(self):
        """Stop the monitor thread."""
        self.running = False