# Conference Presentation System

A fully redundant, web-enabled, and failover-ready system for managing conference presentations with real-time monitoring and control.

## Created by Ambarish Dey

This project provides a comprehensive solution for professional conference management, featuring seamless failover capabilities, device redundancy, and multi-device control.

## System Overview

This system provides a comprehensive solution for managing presentations at conferences or events with fail-over capability and distributed control. It includes:

- **Main Laptop Application**: Connected to the projector, displaying presenter info, timer, and slides
- **Backup Laptop Application**: Continuously monitors the main system and takes over instantly if needed
- **Web Interfaces**: For moderators, presenters, and audience members
- **Real-time Communication**: Using WebSockets and MQTT for instant updates
- **Automatic Failover**: System detects issues and automatically switches to backup
- **PowerPoint Integration**: Control slides remotely
- **Customizable Timer**: Flexible countdown timers with visual alerts
- **Announcements**: Real-time messaging to all interfaces
- **Camera Integration**: Support for camera input with picture-in-picture display
- **Security Features**: JWT authentication, role-based access control, and secure communications

## Key Features

- **Failover Redundancy**: Seamless transition to backup system if the main system fails
- **Real-time Synchronization**: All components stay in sync via WebSockets and MQTT
- **Multi-device Control**: Presenters and moderators can control from any device
- **Secure Remote Access**: JWT authentication and role-based permissions
- **Customizable UI**: Themes, animations, and logo placement
- **Comprehensive Testing**: System, network, and component tests

## Installation

See [setup instructions](docs/setup.md) for detailed installation steps for Linux, Windows, and macOS.

Quick start:
```bash
# Linux
bash scripts/install_linux.sh

# Windows 
scripts\install_windows.bat

# macOS
bash scripts/install_macos.sh

Documentation

User Guide: How to use the system
Admin Guide: System administration
API Reference: API documentation
Contributing: How to contribute to this project


Configuration
The system uses a central configuration file (config.yaml) that can be customized for your specific needs. You can also configure the system through the web interface at /settings.
Key configuration options:

Network settings (MQTT broker, API server)
Device role (Main, Backup, Moderator)
UI customization (theme, logo, animations)
Security settings (authentication, access control)

Usage
For Moderators

Access the moderator interface at /moderator
Control the timer, slides, and presenter information
Send announcements to all connected clients
Monitor system health and status

For Presenters

Access the presenter interface at /presenter
Control slides using the navigation buttons
View the countdown timer
Request additional time if needed

For Audience

View the presentation screen, timer, and announcements
See current presenter information
Monitor system status

Technical Details

Backend: Python (FastAPI, PyQt5)
Frontend: HTML, JavaScript, Tailwind CSS
Communication: WebSockets, MQTT
Security: JWT authentication, HTTPS

License
This project is licensed under the MIT License.
Contact
Ambarish Dey - [ambarish.dey@example.com]

