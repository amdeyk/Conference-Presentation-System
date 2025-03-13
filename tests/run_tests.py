"""
Unit Testing Module for the Conference Presentation System.
Provides comprehensive tests for system components and network connectivity.
"""

import os
import sys
import json
import time
import socket
import logging
import subprocess
import requests
import argparse
import concurrent.futures
import unittest
from typing import Dict, List, Optional, Tuple, Any, Callable

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("UnitTests")

class SystemTests:
    """
    Tests for system hardware and software requirements.
    """
    
    @staticmethod
    def check_cpu(min_cores: int = 2) -> Tuple[bool, str]:
        """
        Check if the CPU meets minimum requirements.
        
        Args:
            min_cores: Minimum number of CPU cores required
            
        Returns:
            (success, message) tuple
        """
        try:
            import psutil
            cpu_count = psutil.cpu_count(logical=False)
            if cpu_count is None:
                cpu_count = psutil.cpu_count(logical=True)
                if cpu_count is None:
                    return False, "Could not determine CPU core count"
            
            if cpu_count < min_cores:
                return False, f"Insufficient CPU cores: {cpu_count} (minimum {min_cores} required)"
            
            return True, f"CPU OK: {cpu_count} cores"
        
        except ImportError:
            # Try alternative method if psutil is not available
            try:
                if sys.platform == "win32":
                    # Windows
                    import platform
                    cpu_count = len(set([p.get('ProcessorId', '') for p in platform.processor()]))
                    if cpu_count < min_cores:
                        return False, f"Insufficient CPU cores: {cpu_count} (minimum {min_cores} required)"
                    return True, f"CPU OK: {cpu_count} cores"
                else:
                    # Linux/Unix/Mac
                    import multiprocessing
                    cpu_count = multiprocessing.cpu_count()
                    if cpu_count < min_cores:
                        return False, f"Insufficient CPU cores: {cpu_count} (minimum {min_cores} required)"
                    return True, f"CPU OK: {cpu_count} cores"
            
            except Exception as e:
                return False, f"Error checking CPU: {str(e)}"
    
    @staticmethod
    def check_memory(min_gb: float = 4.0) -> Tuple[bool, str]:
        """
        Check if the system has enough RAM.
        
        Args:
            min_gb: Minimum RAM in GB required
            
        Returns:
            (success, message) tuple
        """
        try:
            import psutil
            memory = psutil.virtual_memory()
            total_gb = memory.total / (1024 ** 3)
            
            if total_gb < min_gb:
                return False, f"Insufficient memory: {total_gb:.2f} GB (minimum {min_gb:.2f} GB required)"
            
            return True, f"Memory OK: {total_gb:.2f} GB"
        
        except ImportError:
            # Alternative method if psutil is not available
            try:
                if sys.platform == "win32":
                    # Windows
                    import ctypes
                    kernel32 = ctypes.windll.kernel32
                    c_ulonglong = ctypes.c_ulonglong
                    class MEMORYSTATUSEX(ctypes.Structure):
                        _fields_ = [
                            ('dwLength', ctypes.c_ulong),
                            ('dwMemoryLoad', ctypes.c_ulong),
                            ('ullTotalPhys', c_ulonglong),
                            ('ullAvailPhys', c_ulonglong),
                            ('ullTotalPageFile', c_ulonglong),
                            ('ullAvailPageFile', c_ulonglong),
                            ('ullTotalVirtual', c_ulonglong),
                            ('ullAvailVirtual', c_ulonglong),
                            ('ullExtendedVirtual', c_ulonglong),
                        ]
                    
                    memoryStatus = MEMORYSTATUSEX()
                    memoryStatus.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                    kernel32.GlobalMemoryStatusEx(ctypes.byref(memoryStatus))
                    total_gb = memoryStatus.ullTotalPhys / (1024 ** 3)
                    
                    if total_gb < min_gb:
                        return False, f"Insufficient memory: {total_gb:.2f} GB (minimum {min_gb:.2f} GB required)"
                    
                    return True, f"Memory OK: {total_gb:.2f} GB"
                
                else:
                    # Linux/Unix/Mac
                    with open('/proc/meminfo', 'r') as f:
                        for line in f:
                            if 'MemTotal' in line:
                                total_kb = int(line.split()[1])
                                total_gb = total_kb / (1024 ** 2)
                                
                                if total_gb < min_gb:
                                    return False, f"Insufficient memory: {total_gb:.2f} GB (minimum {min_gb:.2f} GB required)"
                                
                                return True, f"Memory OK: {total_gb:.2f} GB"
                    
                    return False, "Could not determine total memory"
                    
            except Exception as e:
                return False, f"Error checking memory: {str(e)}"
    
    @staticmethod
    def check_disk_space(min_gb: float = 10.0, check_path: str = None) -> Tuple[bool, str]:
        """
        Check if there's enough disk space.
        
        Args:
            min_gb: Minimum free disk space in GB required
            check_path: Path to check (None = current working directory)
            
        Returns:
            (success, message) tuple
        """
        if check_path is None:
            check_path = os.getcwd()
        
        try:
            import shutil
            total, used, free = shutil.disk_usage(check_path)
            
            # Convert to GB
            free_gb = free / (1024 ** 3)
            total_gb = total / (1024 ** 3)
            
            if free_gb < min_gb:
                return False, f"Insufficient disk space: {free_gb:.2f} GB free out of {total_gb:.2f} GB (minimum {min_gb:.2f} GB required)"
            
            return True, f"Disk space OK: {free_gb:.2f} GB free out of {total_gb:.2f} GB"
        
        except ImportError:
            # Alternative method if shutil is not available
            try:
                if sys.platform == "win32":
                    # Windows
                    import ctypes
                    free_bytes = ctypes.c_ulonglong(0)
                    total_bytes = ctypes.c_ulonglong(0)
                    ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                        ctypes.c_wchar_p(check_path),
                        None,
                        ctypes.byref(total_bytes),
                        ctypes.byref(free_bytes)
                    )
                    
                    free_gb = free_bytes.value / (1024 ** 3)
                    total_gb = total_bytes.value / (1024 ** 3)
                    
                    if free_gb < min_gb:
                        return False, f"Insufficient disk space: {free_gb:.2f} GB free out of {total_gb:.2f} GB (minimum {min_gb:.2f} GB required)"
                    
                    return True, f"Disk space OK: {free_gb:.2f} GB free out of {total_gb:.2f} GB"
                
                else:
                    # Linux/Unix/Mac
                    import os
                    stat = os.statvfs(check_path)
                    free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
                    total_gb = (stat.f_blocks * stat.f_frsize) / (1024 ** 3)
                    
                    if free_gb < min_gb:
                        return False, f"Insufficient disk space: {free_gb:.2f} GB free out of {total_gb:.2f} GB (minimum {min_gb:.2f} GB required)"
                    
                    return True, f"Disk space OK: {free_gb:.2f} GB free out of {total_gb:.2f} GB"
            
            except Exception as e:
                return False, f"Error checking disk space: {str(e)}"
    
    @staticmethod
    def check_display_resolution(min_width: int = 1024, min_height: int = 768) -> Tuple[bool, str]:
        """
        Check if the display resolution meets minimum requirements.
        
        Args:
            min_width: Minimum width in pixels
            min_height: Minimum height in pixels
            
        Returns:
            (success, message) tuple
        """
        try:
            if sys.platform == "win32":
                # Windows
                import ctypes
                user32 = ctypes.windll.user32
                width = user32.GetSystemMetrics(0)  # SM_CXSCREEN
                height = user32.GetSystemMetrics(1)  # SM_CYSCREEN
            
            elif sys.platform == "darwin":
                # macOS
                try:
                    from AppKit import NSScreen
                    frame = NSScreen.mainScreen().frame()
                    width, height = frame.size.width, frame.size.height
                except ImportError:
                    # Fallback to running system command
                    output = subprocess.check_output(["system_profiler", "SPDisplaysDataType"])
                    for line in output.decode().split("\n"):
                        if "Resolution" in line:
                            parts = line.split(":")
                            if len(parts) > 1:
                                res_parts = parts[1].strip().split(" x ")
                                if len(res_parts) >= 2:
                                    width = int(res_parts[0])
                                    height = int(res_parts[1])
                                    break
                    else:
                        return False, "Could not determine display resolution"
            
            else:
                # Linux
                try:
                    import tkinter as tk
                    root = tk.Tk()
                    width = root.winfo_screenwidth()
                    height = root.winfo_screenheight()
                    root.destroy()
                except ImportError:
                    # Try using subprocess to call xrandr
                    try:
                        output = subprocess.check_output(["xrandr"]).decode()
                        for line in output.split("\n"):
                            if " connected" in line and "primary" in line:
                                parts = line.split()
                                for part in parts:
                                    if "x" in part and part[0].isdigit():
                                        res_parts = part.split("x")
                                        if len(res_parts) >= 2:
                                            width = int(res_parts[0])
                                            height = int(res_parts[1].split("+")[0])
                                            break
                        else:
                            return False, "Could not determine display resolution"
                    except:
                        return False, "Could not determine display resolution"
            
            if width < min_width or height < min_height:
                return False, f"Insufficient display resolution: {width}x{height} (minimum {min_width}x{min_height} required)"
            
            return True, f"Display resolution OK: {width}x{height}"
        
        except Exception as e:
            return False, f"Error checking display resolution: {str(e)}"
    
    @staticmethod
    def check_python_version(min_major: int = 3, min_minor: int = 8) -> Tuple[bool, str]:
        """
        Check if Python version meets minimum requirements.
        
        Args:
            min_major: Minimum major version required
            min_minor: Minimum minor version required
            
        Returns:
            (success, message) tuple
        """
        major, minor = sys.version_info[:2]
        
        if major < min_major or (major == min_major and minor < min_minor):
            return False, f"Insufficient Python version: {major}.{minor} (minimum {min_major}.{min_minor} required)"
        
        return True, f"Python version OK: {major}.{minor}"
    
    @staticmethod
    def check_required_packages(packages: List[str]) -> Tuple[bool, str]:
        """
        Check if required Python packages are installed.
        
        Args:
            packages: List of required package names
            
        Returns:
            (success, message) tuple
        """
        missing = []
        
        for package in packages:
            try:
                __import__(package)
            except ImportError:
                missing.append(package)
        
        if missing:
            return False, f"Missing required packages: {', '.join(missing)}"
        
        return True, "All required packages are installed"


class NetworkTests:
    """
    Tests for network connectivity and related services.
    """
    
    @staticmethod
    def check_internet_connection(timeout: float = 5.0) -> Tuple[bool, str]:
        """
        Check if there's an active internet connection.
        
        Args:
            timeout: Connection timeout in seconds
            
        Returns:
            (success, message) tuple
        """
        try:
            # Try to connect to Google DNS
            socket.create_connection(("8.8.8.8", 53), timeout=timeout)
            
            # Try to fetch a known URL as well
            requests.get("https://www.google.com", timeout=timeout)
            
            return True, "Internet connection OK"
        
        except (socket.error, requests.RequestException) as e:
            return False, f"No internet connection: {str(e)}"
    
    @staticmethod
    def check_port_open(host: str, port: int, timeout: float = 2.0) -> Tuple[bool, str]:
        """
        Check if a specific port is open on a host.
        
        Args:
            host: Hostname or IP address
            port: Port number to check
            timeout: Connection timeout in seconds
            
        Returns:
            (success, message) tuple
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                return True, f"Port {port} on {host} is open"
            else:
                return False, f"Port {port} on {host} is closed"
        
        except Exception as e:
            return False, f"Error checking port {port} on {host}: {str(e)}"
    
    @staticmethod
    def check_mqtt_broker(host: str, port: int = 1883, timeout: float = 5.0) -> Tuple[bool, str]:
        """
        Check if an MQTT broker is accessible.
        
        Args:
            host: MQTT broker hostname or IP
            port: MQTT broker port
            timeout: Connection timeout in seconds
            
        Returns:
            (success, message) tuple
        """
        try:
            import paho.mqtt.client as mqtt
            
            # This event will be set when the connection is successful
            connected = False
            
            def on_connect(client, userdata, flags, rc):
                nonlocal connected
                connected = (rc == 0)
            
            # Set up client
            client = mqtt.Client()
            client.on_connect = on_connect
            client.connect_async(host, port)
            
            # Start the loop
            client.loop_start()
            
            # Wait for the connection to be established
            start_time = time.time()
            while time.time() - start_time < timeout:
                if connected:
                    break
                time.sleep(0.1)
            
            # Stop the loop
            client.loop_stop()
            client.disconnect()
            
            if connected:
                return True, f"MQTT broker at {host}:{port} is accessible"
            else:
                return False, f"Could not connect to MQTT broker at {host}:{port}"
        
        except ImportError:
            return False, "Paho MQTT client not installed"
        
        except Exception as e:
            return False, f"Error connecting to MQTT broker at {host}:{port}: {str(e)}"
    
    @staticmethod
    def check_http_server(url: str, timeout: float = 5.0) -> Tuple[bool, str]:
        """
        Check if an HTTP server is accessible.
        
        Args:
            url: URL to check
            timeout: Request timeout in seconds
            
        Returns:
            (success, message) tuple
        """
        try:
            response = requests.get(url, timeout=timeout)
            
            if response.status_code < 400:
                return True, f"HTTP server at {url} is accessible (status {response.status_code})"
            else:
                return False, f"HTTP server at {url} returned error status {response.status_code}"
        
        except requests.RequestException as e:
            return False, f"Error connecting to HTTP server at {url}: {str(e)}"
    
    @staticmethod
    def check_dns_resolution(hostname: str) -> Tuple[bool, str]:
        """
        Check if a hostname can be resolved to an IP address.
        
        Args:
            hostname: Hostname to resolve
            
        Returns:
            (success, message) tuple
        """
        try:
            ip = socket.gethostbyname(hostname)
            return True, f"DNS resolution OK: {hostname} resolves to {ip}"
        
        except socket.gaierror as e:
            return False, f"Could not resolve hostname {hostname}: {str(e)}"
    
    @staticmethod
    def check_lan_connectivity(target_ip: str, timeout: float = 2.0) -> Tuple[bool, str]:
        """
        Check if a target on the local network is reachable.
        
        Args:
            target_ip: IP address of the target
            timeout: Ping timeout in seconds
            
        Returns:
            (success, message) tuple
        """
        try:
            # Try to ping the target
            if sys.platform == "win32":
                # Windows ping command
                ping_param = "-n"
                timeout_param = "-w"
                timeout_ms = int(timeout * 1000)
                command = ["ping", ping_param, "1", timeout_param, str(timeout_ms), target_ip]
            else:
                # Linux/Mac ping command
                ping_param = "-c"
                timeout_param = "-W"
                timeout_sec = int(timeout)
                command = ["ping", ping_param, "1", timeout_param, str(timeout_sec), target_ip]
            
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if result.returncode == 0:
                return True, f"LAN connectivity OK: {target_ip} is reachable"
            else:
                return False, f"LAN connectivity failed: {target_ip} is not reachable"
        
        except Exception as e:
            return False, f"Error checking LAN connectivity to {target_ip}: {str(e)}"
    
    @staticmethod
    def measure_network_latency(target: str, port: int = 80, samples: int = 5) -> Tuple[bool, str]:
        """
        Measure network latency to a target.
        
        Args:
            target: Hostname or IP address
            port: Port to connect to
            samples: Number of samples to take
            
        Returns:
            (success, message) tuple
        """
        try:
            latencies = []
            
            for _ in range(samples):
                start_time = time.time()
                
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2.0)
                    sock.connect((target, port))
                    sock.close()
                    
                    latency = (time.time() - start_time) * 1000  # Convert to milliseconds
                    latencies.append(latency)
                
                except Exception:
                    # Skip failed attempts
                    pass
                
                time.sleep(0.2)  # Short delay between samples
            
            if not latencies:
                return False, f"Could not connect to {target}:{port} for latency measurement"
            
            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            
            # Determine if latency is acceptable (under 100ms avg is good)
            success = avg_latency < 100
            
            return success, f"Network latency to {target}:{port}: avg={avg_latency:.1f}ms, min={min_latency:.1f}ms, max={max_latency:.1f}ms"
        
        except Exception as e:
            return False, f"Error measuring latency to {target}:{port}: {str(e)}"


class ApplicationTests:
    """
    Tests for application components and functionality.
    """
    
    @staticmethod
    def check_mqtt_topics(broker: str, topics: List[str], port: int = 1883, timeout: float = 5.0) -> Tuple[bool, str]:
        """
        Check if MQTT topics can be subscribed to.
        
        Args:
            broker: MQTT broker hostname or IP
            topics: List of topics to check
            port: MQTT broker port
            timeout: Connection timeout in seconds
            
        Returns:
            (success, message) tuple
        """
        try:
            import paho.mqtt.client as mqtt
            
            # This will hold the results
            results = {topic: False for topic in topics}
            connected = False
            
            def on_connect(client, userdata, flags, rc):
                nonlocal connected
                connected = (rc == 0)
                if connected:
                    for topic in topics:
                        client.subscribe(topic)
            
            def on_subscribe(client, userdata, mid, granted_qos):
                # This is called when a subscription is successful
                # We can't determine which topic was subscribed to from this callback,
                # so we'll consider the test successful once we're connected
                pass
            
            # Set up client
            client = mqtt.Client()
            client.on_connect = on_connect
            client.on_subscribe = on_subscribe
            client.connect_async(broker, port)
            
            # Start the loop
            client.loop_start()
            
            # Wait for the connection to be established
            start_time = time.time()
            while time.time() - start_time < timeout:
                if connected:
                    # Give some time for subscriptions to complete
                    time.sleep(1.0)
                    break
                time.sleep(0.1)
            
            # Stop the loop
            client.loop_stop()
            client.disconnect()
            
            if connected:
                return True, f"Successfully connected to MQTT broker and subscribed to topics"
            else:
                return False, f"Could not connect to MQTT broker at {broker}:{port}"
        
        except ImportError:
            return False, "Paho MQTT client not installed"
        
        except Exception as e:
            return False, f"Error checking MQTT topics: {str(e)}"
    
    @staticmethod
    def check_api_endpoints(base_url: str, endpoints: List[str], timeout: float = 5.0) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if API endpoints are accessible.
        
        Args:
            base_url: Base URL of the API
            endpoints: List of endpoint paths to check
            timeout: Request timeout in seconds
            
        Returns:
            (success, results) tuple where results is a dict of endpoint to (success, status, message) tuples
        """
        results = {}
        overall_success = True
        
        for endpoint in endpoints:
            url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            
            try:
                response = requests.get(url, timeout=timeout)
                success = response.status_code < 400
                
                results[endpoint] = {
                    "success": success,
                    "status_code": response.status_code,
                    "message": f"Status: {response.status_code}"
                }
                
                if not success:
                    overall_success = False
            
            except requests.RequestException as e:
                results[endpoint] = {
                    "success": False,
                    "status_code": None,
                    "message": f"Error: {str(e)}"
                }
                overall_success = False
        
        return overall_success, results
    
    @staticmethod
    def check_websocket_connection(websocket_url: str, timeout: float = 5.0) -> Tuple[bool, str]:
        """
        Check if a WebSocket server is accessible.
        
        Args:
            websocket_url: WebSocket URL to check
            timeout: Connection timeout in seconds
            
        Returns:
            (success, message) tuple
        """
        try:
            import websocket
            
            # Connect with a timeout
            ws = websocket.create_connection(websocket_url, timeout=timeout)
            
            # If we get here, connection was successful
            ws.close()
            return True, f"WebSocket server at {websocket_url} is accessible"
        
        except ImportError:
            return False, "websocket-client package not installed"
        
        except Exception as e:
            return False, f"Error connecting to WebSocket server at {websocket_url}: {str(e)}"


class TestRunner:
    """
    Runs a series of tests and reports results.
    """
    
    def __init__(self):
        self.tests = {}
        self.results = {}
    
    def add_test(self, category: str, name: str, test_func: Callable[[], Tuple[bool, Any]]) -> None:
        """
        Add a test function to the runner.
        
        Args:
            category: Test category (e.g., "System", "Network")
            name: Test name
            test_func: Function that performs the test and returns (success, message) tuple
        """
        if category not in self.tests:
            self.tests[category] = {}
        
        self.tests[category][name] = test_func
    
    def run_tests(self, categories: Optional[List[str]] = None, parallel: bool = True) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Run all tests or tests in specified categories.
        
        Args:
            categories: List of categories to run (None = all)
            parallel: Whether to run tests in parallel
            
        Returns:
            Dictionary of test results by category and name
        """
        self.results = {}
        
        # Filter categories if specified
        if categories:
            test_categories = {cat: tests for cat, tests in self.tests.items() if cat in categories}
        else:
            test_categories = self.tests
        
        if parallel:
            # Run tests in parallel using ThreadPoolExecutor
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Submit all tests
                future_to_test = {}
                
                for category, tests in test_categories.items():
                    if category not in self.results:
                        self.results[category] = {}
                    
                    for name, test_func in tests.items():
                        future = executor.submit(test_func)
                        future_to_test[future] = (category, name)
                
                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_test):
                    category, name = future_to_test[future]
                    try:
                        success, message = future.result()
                        self.results[category][name] = {
                            "success": success,
                            "message": message,
                            "timestamp": time.time()
                        }
                    except Exception as e:
                        self.results[category][name] = {
                            "success": False,
                            "message": f"Error: {str(e)}",
                            "timestamp": time.time()
                        }
        else:
            # Run tests sequentially
            for category, tests in test_categories.items():
                if category not in self.results:
                    self.results[category] = {}
                
                for name, test_func in tests.items():
                    try:
                        success, message = test_func()
                        self.results[category][name] = {
                            "success": success,
                            "message": message,
                            "timestamp": time.time()
                        }
                    except Exception as e:
                        self.results[category][name] = {
                            "success": False,
                            "message": f"Error: {str(e)}",
                            "timestamp": time.time()
                        }
        
        return self.results
    
    def print_results(self) -> None:
        """Print test results to the console."""
        if not self.results:
            print("No test results to display. Run tests first.")
            return
        
        # Calculate overall statistics
        total_tests = 0
        passed_tests = 0
        
        for category, tests in self.results.items():
            category_total = len(tests)
            category_passed = sum(1 for result in tests.values() if result["success"])
            
            total_tests += category_total
            passed_tests += category_passed
            
            # Print category header
            print(f"\n{category} Tests: {category_passed}/{category_total} passed")
            print("=" * 80)
            
            # Print individual test results
            for name, result in tests.items():
                status = "PASS" if result["success"] else "FAIL"
                status_color = "\033[92m" if result["success"] else "\033[91m"  # Green/Red
                reset_color = "\033[0m"
                
                print(f"{status_color}{status}{reset_color} - {name}: {result['message']}")
        
        # Print overall summary
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        print("\nSummary:")
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests} ({success_rate:.1f}%)")
        print(f"Failed: {total_tests - passed_tests} ({100 - success_rate:.1f}%)")
    
    def save_results(self, filename: str) -> bool:
        """
        Save test results to a JSON file.
        
        Args:
            filename: Path to save results to
            
        Returns:
            True if successful, False otherwise
        """
        if not self.results:
            logger.error("No test results to save. Run tests first.")
            return False
        
        try:
            # Convert timestamps to ISO format for better readability
            results_copy = {}
            for category, tests in self.results.items():
                results_copy[category] = {}
                for name, result in tests.items():
                    result_copy = result.copy()
                    result_copy["timestamp"] = time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(result["timestamp"])
                    )
                    results_copy[category][name] = result_copy
            
            with open(filename, 'w') as f:
                json.dump(results_copy, f, indent=2)
            
            logger.info(f"Test results saved to {filename}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving test results: {str(e)}")
            return False

# Create a test suite for the Conference Presentation System
def create_test_suite(config: Dict[str, Any]) -> TestRunner:
    """
    Create a test suite for the Conference Presentation System.
    
    Args:
        config: System configuration
        
    Returns:
        Configured TestRunner instance
    """
    runner = TestRunner()
    
    # System Tests
    runner.add_test("System", "CPU Check", lambda: SystemTests.check_cpu(min_cores=2))
    runner.add_test("System", "Memory Check", lambda: SystemTests.check_memory(min_gb=4.0))
    runner.add_test("System", "Disk Space Check", lambda: SystemTests.check_disk_space(min_gb=10.0))
    runner.add_test("System", "Display Resolution Check", lambda: SystemTests.check_display_resolution(min_width=1024, min_height=768))
    runner.add_test("System", "Python Version Check", lambda: SystemTests.check_python_version(min_major=3, min_minor=8))
    
    required_packages = [
        "fastapi", "uvicorn", "pyqt5", "paho", "psutil", "requests", "jinja2"
    ]
    runner.add_test("System", "Required Packages Check", lambda: SystemTests.check_required_packages(required_packages))
    
    # Network Tests
    mqtt_broker = config.get("mqtt_broker", "localhost")
    mqtt_port = config.get("mqtt_port", 1883)
    api_host = config.get("api_host", "localhost")
    api_port = config.get("api_port", 8000)
    
    runner.add_test("Network", "Internet Connection Check", NetworkTests.check_internet_connection)
    runner.add_test("Network", "MQTT Port Check", lambda: NetworkTests.check_port_open(mqtt_broker, mqtt_port))
    runner.add_test("Network", "API Port Check", lambda: NetworkTests.check_port_open(api_host, api_port))
    runner.add_test("Network", "MQTT Broker Check", lambda: NetworkTests.check_mqtt_broker(mqtt_broker, mqtt_port))
    
    # Add more tests for specific deployments
    api_base_url = f"http://{api_host}:{api_port}"
    runner.add_test("Network", "API Server Check", lambda: NetworkTests.check_http_server(api_base_url))
    
    if config.get("check_lan", False):
        # Add LAN connectivity checks
        main_ip = config.get("main_laptop_ip")
        backup_ip = config.get("backup_laptop_ip")
        
        if main_ip:
            runner.add_test("Network", "Main Laptop Connectivity", lambda: NetworkTests.check_lan_connectivity(main_ip))
        
        if backup_ip:
            runner.add_test("Network", "Backup Laptop Connectivity", lambda: NetworkTests.check_lan_connectivity(backup_ip))
    
    # Application Tests
    mqtt_topics = [
        "conference/timer/#",
        "conference/presenter/#",
        "conference/announcement/#",
        "conference/heartbeat/#",
        "conference/control/#"
    ]
    runner.add_test("Application", "MQTT Topics Check", lambda: ApplicationTests.check_mqtt_topics(mqtt_broker, mqtt_topics, mqtt_port))
    
    # API endpoints check
    api_endpoints = [
        "/",
        "/api/state",
        "/moderator",
        "/presenter",
        "/audience"
    ]
    
    def check_api():
        success, results = ApplicationTests.check_api_endpoints(api_base_url, api_endpoints)
        # Format the message
        message = "\n"
        for endpoint, result in results.items():
            status = "OK" if result["success"] else "FAIL"
            message += f"  {endpoint}: {status} ({result['message']})\n"
        return success, message
    
    runner.add_test("Application", "API Endpoints Check", check_api)
    
    # WebSocket check
    websocket_url = f"ws://{api_host}:{api_port}/ws"
    runner.add_test("Application", "WebSocket Check", lambda: ApplicationTests.check_websocket_connection(websocket_url))
    
    return runner

# Command-line script
def main():
    parser = argparse.ArgumentParser(description="Conference System Test Runner")
    parser.add_argument("--config", help="Path to system configuration file")
    parser.add_argument("--categories", help="Comma-separated list of test categories to run")
    parser.add_argument("--output", help="Output file for test results (JSON)")
    parser.add_argument("--sequential", action="store_true", help="Run tests sequentially instead of in parallel")
    
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    if args.config:
        try:
            with open(args.config, 'r') as f:
                if args.config.endswith('.json'):
                    config = json.load(f)
                elif args.config.endswith('.yaml') or args.config.endswith('.yml'):
                    import yaml
                    config = yaml.safe_load(f)
                else:
                    print(f"Unsupported configuration file format: {args.config}")
                    sys.exit(1)
            
            print(f"Loaded configuration from {args.config}")
        except Exception as e:
            print(f"Error loading configuration: {str(e)}")
            sys.exit(1)
    
    # Create and run test suite
    runner = create_test_suite(config)
    
    # Parse categories if specified
    categories = None
    if args.categories:
        categories = [cat.strip() for cat in args.categories.split(",")]
    
    # Run tests
    runner.run_tests(categories=categories, parallel=not args.sequential)
    
    # Print results
    runner.print_results()
    
    # Save results if output file specified
    if args.output:
        if runner.save_results(args.output):
            print(f"Test results saved to {args.output}")
        else:
            print(f"Error saving test results to {args.output}")

if __name__ == "__main__":
    main()