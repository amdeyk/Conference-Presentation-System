"""
Configuration management system for the Conference Presentation System.
Centralizes all configuration in a single place with validation and environment overrides.
"""

import os
import sys
import json
import yaml
import logging
import argparse
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, validator, root_validator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ConfigSystem")

# Define configuration schemas using Pydantic models
class NetworkConfig(BaseModel):
    mqtt_broker: str = "localhost"
    mqtt_port: int = 1883
    mqtt_topic_prefix: str = "conference/"
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    mqtt_use_tls: bool = False
    
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_base_url: Optional[str] = None
    
    webrtc_enabled: bool = True
    webrtc_ice_servers: List[Dict[str, Any]] = [{"urls": "stun:stun.l.google.com:19302"}]
    
    @validator('mqtt_port', 'api_port')
    def validate_ports(cls, v):
        if v < 0 or v > 65535:
            raise ValueError(f"Port must be between 0 and 65535, got {v}")
        return v

class DeviceConfig(BaseModel):
    device_id: Optional[str] = None
    device_role: str = "MAIN"  # MAIN, BACKUP, or MODERATOR
    device_name: str = "Conference System"
    backup_check_interval: int = 10  # seconds
    health_check_interval: int = 30  # seconds
    failover_timeout: int = 15  # seconds
    powerpoint_enabled: bool = True
    camera_enabled: bool = False
    camera_source: Optional[str] = None
    
    @validator('device_role')
    def validate_role(cls, v):
        valid_roles = ["MAIN", "BACKUP", "MODERATOR"]
        if v not in valid_roles:
            raise ValueError(f"Role must be one of {valid_roles}, got {v}")
        return v

class UIConfig(BaseModel):
    theme: str = "default"
    logo_path: Optional[str] = None
    logo_position: str = "top-right"  # top-left, top-right, bottom-left, bottom-right
    logo_size: int = 100  # pixels
    animation_enabled: bool = True
    custom_css_path: Optional[str] = None
    font_family: str = "Arial, sans-serif"
    
    # UI colors
    primary_color: str = "#3B82F6"  # blue
    secondary_color: str = "#10B981"  # green
    background_color: str = "#F3F4F6"  # light gray
    text_color: str = "#1F2937"  # dark gray
    accent_color: str = "#F59E0B"  # amber
    
    @validator('logo_position')
    def validate_logo_position(cls, v):
        valid_positions = ["top-left", "top-right", "bottom-left", "bottom-right", "custom"]
        if v not in valid_positions:
            raise ValueError(f"Logo position must be one of {valid_positions}, got {v}")
        return v
    
    @validator('primary_color', 'secondary_color', 'background_color', 'text_color', 'accent_color')
    def validate_color(cls, v):
        if not v.startswith('#') or not all(c in '0123456789ABCDEFabcdef' for c in v[1:]):
            raise ValueError(f"Color must be a valid hex color code, got {v}")
        return v

class SecurityConfig(BaseModel):
    auth_enabled: bool = True
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    password_salt: Optional[str] = None
    allow_anonymous_viewers: bool = False
    cors_origins: List[str] = ["*"]
    
    # For production, generate these with secrets.token_hex(32)
    @validator('jwt_secret_key', 'password_salt')
    def default_secrets(cls, v, values, **kwargs):
        if v is None:
            import secrets
            return secrets.token_hex(32)
        return v

class AppConfig(BaseModel):
    network: NetworkConfig = NetworkConfig()
    device: DeviceConfig = DeviceConfig()
    ui: UIConfig = UIConfig()
    security: SecurityConfig = SecurityConfig()
    debug_mode: bool = False
    
    # Additional validation across sections
    @root_validator
    def check_dependencies(cls, values):
        # Example validation: if camera is enabled, camera_source should be set
        if values.get('device').camera_enabled and not values.get('device').camera_source:
            logger.warning("Camera is enabled but no source is specified. Using default.")
            values['device'].camera_source = "0"  # Default camera index
        
        return values

class ConfigManager:
    """
    Manages application configuration with support for:
    - Default configuration
    - Configuration file (YAML or JSON)
    - Environment variables
    - Command-line arguments
    """
    
    def __init__(self):
        self.config = AppConfig()
        self.config_file_path = None
    
    def load_config_file(self, file_path: str) -> bool:
        """Load configuration from a YAML or JSON file."""
        try:
            with open(file_path, 'r') as f:
                if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                    config_data = yaml.safe_load(f)
                elif file_path.endswith('.json'):
                    config_data = json.load(f)
                else:
                    logger.error(f"Unsupported file format: {file_path}")
                    return False
            
            # Update configuration with file data
            self._update_config_from_dict(config_data)
            self.config_file_path = file_path
            logger.info(f"Loaded configuration from {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error loading configuration file: {str(e)}")
            return False
    
    def load_environment_variables(self) -> None:
        """
        Load configuration from environment variables.
        Environment variables should be in the format:
        CONF_SECTION_KEY=value
        
        For example:
        CONF_NETWORK_MQTT_BROKER=mqtt.example.com
        """
        prefix = "CONF_"
        
        for name, value in os.environ.items():
            if name.startswith(prefix):
                parts = name[len(prefix):].lower().split('_', 1)
                if len(parts) != 2:
                    continue
                
                section, key = parts
                self._set_config_value(section, key, value)
    
    def load_command_line_args(self) -> None:
        """Load configuration from command-line arguments."""
        parser = argparse.ArgumentParser(description='Conference Presentation System')
        
        # Config file argument
        parser.add_argument('--config', help='Path to configuration file (.yaml or .json)')
        
        # Add arguments for each config section
        self._add_network_args(parser)
        self._add_device_args(parser)
        self._add_ui_args(parser)
        self._add_security_args(parser)
        
        # Debug mode
        parser.add_argument('--debug', action='store_true', help='Enable debug mode')
        
        # Parse arguments
        args = parser.parse_args()
        
        # Load config file if specified
        if args.config:
            self.load_config_file(args.config)
        
        # Update config with command-line args
        self._update_config_from_args(args)
    
    def _add_network_args(self, parser):
        group = parser.add_argument_group('Network')
        group.add_argument('--mqtt-broker', help='MQTT broker hostname')
        group.add_argument('--mqtt-port', type=int, help='MQTT broker port')
        group.add_argument('--mqtt-prefix', help='MQTT topic prefix')
        group.add_argument('--api-host', help='API server host')
        group.add_argument('--api-port', type=int, help='API server port')
        group.add_argument('--webrtc', choices=['enabled', 'disabled'], help='Enable/disable WebRTC')
    
    def _add_device_args(self, parser):
        group = parser.add_argument_group('Device')
        group.add_argument('--role', choices=['MAIN', 'BACKUP', 'MODERATOR'], help='Device role')
        group.add_argument('--device-name', help='Device name')
        group.add_argument('--powerpoint', choices=['enabled', 'disabled'], help='Enable/disable PowerPoint')
        group.add_argument('--camera', choices=['enabled', 'disabled'], help='Enable/disable camera')
        group.add_argument('--camera-source', help='Camera source (index or URL)')
    
    def _add_ui_args(self, parser):
        group = parser.add_argument_group('UI')
        group.add_argument('--theme', help='UI theme')
        group.add_argument('--logo', help='Path to logo image')
        group.add_argument('--logo-position', choices=['top-left', 'top-right', 'bottom-left', 'bottom-right', 'custom'], 
                           help='Logo position')
        group.add_argument('--animations', choices=['enabled', 'disabled'], help='Enable/disable animations')
    
    def _add_security_args(self, parser):
        group = parser.add_argument_group('Security')
        group.add_argument('--auth', choices=['enabled', 'disabled'], help='Enable/disable authentication')
        group.add_argument('--jwt-secret', help='JWT secret key')
        group.add_argument('--anonymous-viewers', choices=['enabled', 'disabled'], 
                           help='Allow anonymous viewers')
    
    def _update_config_from_args(self, args):
        """Update configuration from command-line arguments."""
        # Network section
        if args.mqtt_broker:
            self.config.network.mqtt_broker = args.mqtt_broker
        if args.mqtt_port:
            self.config.network.mqtt_port = args.mqtt_port
        if args.mqtt_prefix:
            self.config.network.mqtt_topic_prefix = args.mqtt_prefix
        if args.api_host:
            self.config.network.api_host = args.api_host
        if args.api_port:
            self.config.network.api_port = args.api_port
        if args.webrtc:
            self.config.network.webrtc_enabled = args.webrtc == 'enabled'
        
        # Device section
        if args.role:
            self.config.device.device_role = args.role
        if args.device_name:
            self.config.device.device_name = args.device_name
        if args.powerpoint:
            self.config.device.powerpoint_enabled = args.powerpoint == 'enabled'
        if args.camera:
            self.config.device.camera_enabled = args.camera == 'enabled'
        if args.camera_source:
            self.config.device.camera_source = args.camera_source
        
        # UI section
        if args.theme:
            self.config.ui.theme = args.theme
        if args.logo:
            self.config.ui.logo_path = args.logo
        if args.logo_position:
            self.config.ui.logo_position = args.logo_position
        if args.animations:
            self.config.ui.animation_enabled = args.animations == 'enabled'
        
        # Security section
        if args.auth:
            self.config.security.auth_enabled = args.auth == 'enabled'
        if args.jwt_secret:
            self.config.security.jwt_secret_key = args.jwt_secret
        if args.anonymous_viewers:
            self.config.security.allow_anonymous_viewers = args.anonymous_viewers == 'enabled'
        
        # Debug mode
        if args.debug:
            self.config.debug_mode = True
    
    def _update_config_from_dict(self, config_data: dict) -> None:
        """Update configuration from a dictionary."""
        # Update network section
        if 'network' in config_data:
            for key, value in config_data['network'].items():
                if hasattr(self.config.network, key):
                    setattr(self.config.network, key, value)
        
        # Update device section
        if 'device' in config_data:
            for key, value in config_data['device'].items():
                if hasattr(self.config.device, key):
                    setattr(self.config.device, key, value)
        
        # Update UI section
        if 'ui' in config_data:
            for key, value in config_data['ui'].items():
                if hasattr(self.config.ui, key):
                    setattr(self.config.ui, key, value)
        
        # Update security section
        if 'security' in config_data:
            for key, value in config_data['security'].items():
                if hasattr(self.config.security, key):
                    setattr(self.config.security, key, value)
        
        # Update debug mode
        if 'debug_mode' in config_data:
            self.config.debug_mode = config_data['debug_mode']
    
    def _set_config_value(self, section: str, key: str, value: str) -> None:
        """Set a configuration value from an environment variable."""
        try:
            if section == 'network':
                if hasattr(self.config.network, key):
                    # Convert value to appropriate type
                    if key in ['mqtt_port', 'api_port']:
                        value = int(value)
                    elif key in ['webrtc_enabled', 'mqtt_use_tls']:
                        value = value.lower() in ['true', 'yes', '1']
                    
                    setattr(self.config.network, key, value)
            
            elif section == 'device':
                if hasattr(self.config.device, key):
                    # Convert value to appropriate type
                    if key in ['backup_check_interval', 'health_check_interval', 'failover_timeout']:
                        value = int(value)
                    elif key in ['powerpoint_enabled', 'camera_enabled']:
                        value = value.lower() in ['true', 'yes', '1']
                    
                    setattr(self.config.device, key, value)
            
            elif section == 'ui':
                if hasattr(self.config.ui, key):
                    # Convert value to appropriate type
                    if key in ['logo_size']:
                        value = int(value)
                    elif key in ['animation_enabled']:
                        value = value.lower() in ['true', 'yes', '1']
                    
                    setattr(self.config.ui, key, value)
            
            elif section == 'security':
                if hasattr(self.config.security, key):
                    # Convert value to appropriate type
                    if key in ['access_token_expire_minutes', 'refresh_token_expire_days']:
                        value = int(value)
                    elif key in ['auth_enabled', 'allow_anonymous_viewers']:
                        value = value.lower() in ['true', 'yes', '1']
                    
                    setattr(self.config.security, key, value)
            
            elif section == 'app' and key == 'debug_mode':
                self.config.debug_mode = value.lower() in ['true', 'yes', '1']
        
        except Exception as e:
            logger.error(f"Error setting config value {section}.{key}: {str(e)}")
    
    def save_config(self, file_path: Optional[str] = None) -> bool:
        """Save the current configuration to a file."""
        if file_path is None:
            if self.config_file_path is None:
                logger.error("No configuration file path specified")
                return False
            file_path = self.config_file_path
        
        try:
            # Convert config to dictionary
            config_dict = self.config.dict()
            
            with open(file_path, 'w') as f:
                if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                    yaml.dump(config_dict, f, default_flow_style=False)
                elif file_path.endswith('.json'):
                    json.dump(config_dict, f, indent=2)
                else:
                    logger.error(f"Unsupported file format: {file_path}")
                    return False
            
            logger.info(f"Saved configuration to {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving configuration file: {str(e)}")
            return False
    
    def get_config(self) -> AppConfig:
        """Get the current configuration."""
        return self.config
    
    def generate_default_config(self, file_path: str) -> bool:
        """Generate a default configuration file."""
        try:
            # Create default config
            default_config = AppConfig()
            
            # Convert to dictionary
            config_dict = default_config.dict()
            
            with open(file_path, 'w') as f:
                if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                    yaml.dump(config_dict, f, default_flow_style=False)
                elif file_path.endswith('.json'):
                    json.dump(config_dict, f, indent=2)
                else:
                    logger.error(f"Unsupported file format: {file_path}")
                    return False
            
            logger.info(f"Generated default configuration at {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error generating default configuration: {str(e)}")
            return False


# Command-line tool for configuration management
def main():
    """Command-line tool for managing configuration."""
    parser = argparse.ArgumentParser(description='Conference System Configuration Manager')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Generate default config
    generate_parser = subparsers.add_parser('generate', help='Generate default configuration')
    generate_parser.add_argument('output', help='Output file path (.yaml or .json)')
    
    # Validate config file
    validate_parser = subparsers.add_parser('validate', help='Validate configuration file')
    validate_parser.add_argument('config_file', help='Configuration file to validate')
    
    # Convert config format
    convert_parser = subparsers.add_parser('convert', help='Convert configuration file format')
    convert_parser.add_argument('input', help='Input configuration file')
    convert_parser.add_argument('output', help='Output configuration file')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Create config manager
    config_manager = ConfigManager()
    
    # Execute command
    if args.command == 'generate':
        if config_manager.generate_default_config(args.output):
            print(f"Generated default configuration at {args.output}")
        else:
            print("Failed to generate default configuration")
            sys.exit(1)
    
    elif args.command == 'validate':
        if config_manager.load_config_file(args.config_file):
            print(f"Configuration file {args.config_file} is valid")
        else:
            print(f"Configuration file {args.config_file} is invalid")
            sys.exit(1)
    
    elif args.command == 'convert':
        if config_manager.load_config_file(args.input):
            if config_manager.save_config(args.output):
                print(f"Converted configuration from {args.input} to {args.output}")
            else:
                print(f"Failed to save configuration to {args.output}")
                sys.exit(1)
        else:
            print(f"Failed to load configuration from {args.input}")
            sys.exit(1)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()