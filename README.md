# Conference Presentation Management System

A fully redundant, web-enabled, and failover-ready system for managing conference presentations with real-time monitoring and control.

## System Overview

This system provides a comprehensive solution for managing presentations at conferences or events with fail-over capability and distributed control. It includes:

- **Main Laptop Application**: Connected to the projector, displaying presenter info, timer, and slides
- **Backup Laptop Application**: Continuously monitors the main system and takes over instantly if needed
- **Web Interfaces**: For moderators, presenters, and audience members
- **Real-time Communication**: Using WebSockets and MQTT for instant updates
- **Automatic Failover**: System detects issues