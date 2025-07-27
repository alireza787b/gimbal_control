"""
Gimbal Configuration Settings
=============================
Central configuration file for gimbal control parameters.
Modify these settings according to your setup.
"""

# Network Configuration
GIMBAL_CONFIG = {
    # Camera network settings
    "camera_ip": "192.168.0.108",      # IP address of your gimbal camera
    "control_port": 9003,              # UDP port for sending commands
    "listen_port": 9004,               # UDP port for receiving responses
    "rtsp_port": 554,                  # RTSP streaming port
    
    # Communication settings
    "timeout": 2.0,                    # Command timeout in seconds
    "retry_count": 3,                  # Number of retries for failed commands
    "response_wait": 0.1,              # Time to wait between response checks
    
    # RTSP stream URLs
    "main_stream_url": "rtsp://{ip}:554/stream=0",    # Main video stream
    "sub_stream_url": "rtsp://{ip}:554/stream=1",     # Sub video stream
}

# Gimbal Movement Settings
MOVEMENT_CONFIG = {
    # Speed limits (degrees per second)
    "max_yaw_speed": 99.0,
    "max_pitch_speed": 99.0,
    "max_roll_speed": 99.0,
    
    # Angle limits (degrees)
    "yaw_min": -150.0,
    "yaw_max": 150.0,
    "pitch_min": -90.0,
    "pitch_max": 90.0,
    "roll_min": -90.0,
    "roll_max": 90.0,
    
    # Default speeds for demo
    "slow_speed": 5.0,      # Slow movement speed
    "normal_speed": 15.0,   # Normal movement speed
    "fast_speed": 30.0,     # Fast movement speed
    
    # Movement test durations (seconds)
    "test_move_duration": 1.0,
    "home_return_duration": 2.0,
}

# Camera Settings
CAMERA_CONFIG = {
    # Recording settings
    "default_resolution": "1920x1080",
    "default_bitrate": 4,  # Mbps
    
    # Zoom settings
    "zoom_min": -9999,
    "zoom_max": 9999,
    
    # Focus settings
    "focus_mode": "auto",  # "auto" or "manual"
}

# Logging Configuration
LOGGING_CONFIG = {
    "log_level": "INFO",                    # DEBUG, INFO, WARNING, ERROR
    "log_file": "gimbal_demo.log",          # Log file name
    "log_to_console": True,                 # Print logs to console
    "log_to_file": True,                    # Save logs to file
    "max_log_size": 10 * 1024 * 1024,      # 10MB max log size
    "log_backup_count": 5,                  # Number of backup logs to keep
}

# Demo Settings
DEMO_CONFIG = {
    # Tests to perform
    "test_connection": True,
    "test_telemetry": True,
    "test_movement": True,
    "test_speed_control": True,
    "test_camera_functions": True,
    "test_tracking": True,
    
    # Demo behavior
    "auto_return_home": True,           # Return to home position after tests
    "print_statistics": True,           # Print communication stats at end
    "save_telemetry_log": True,         # Save telemetry data to file
}

# Command Definitions (based on protocol documentation)
COMMANDS = {
    # Gimbal control commands
    "PTZ": {
        "stop": "00",
        "up": "01",
        "down": "02",
        "left": "03",
        "right": "04",
        "home": "05",
        "lock": "06",
        "follow": "07",
        "lock_follow_switch": "08",
        "calibrate": "09",
        "one_button_down": "0A"
    },
    
    # Recording control
    "REC": {
        "stop": "00",
        "start": "01",
        "toggle": "0A"
    },
    
    # Capture modes
    "CAP": {
        "visible_thermal": "01",
        "visible_only": "02",
        "thermal_only": "03",
        "all_with_temp": "05"
    },
    
    # Picture-in-Picture modes
    "PIP": {
        "main_only": "00",
        "main_sub": "01",
        "sub_main": "02",
        "sub_only": "03",
        "next": "0A",
        "previous": "0B"
    },
    
    # Focus control
    "FCC": {
        "stop": "00",
        "focus_plus": "01",
        "focus_minus": "02",
        "auto_focus": "10",
        "manual_focus": "11",
        "manual_save": "12",
        "auto_save": "13"
    },
    
    # Zoom control
    "ZMC": {
        "stop": "00",
        "zoom_out": "01",
        "zoom_in": "02"
    }
}

# Error Messages
ERROR_MESSAGES = {
    "connection_failed": "Failed to establish connection with gimbal",
    "timeout": "Command timeout - no response received",
    "invalid_response": "Invalid response format",
    "crc_error": "CRC checksum mismatch",
    "command_failed": "Command execution failed",
    "network_error": "Network communication error",
}

# Success Messages
SUCCESS_MESSAGES = {
    "connected": "Successfully connected to gimbal",
    "command_sent": "Command sent successfully",
    "telemetry_received": "Telemetry data received",
    "movement_complete": "Movement command completed",
    "recording_started": "Recording started",
    "recording_stopped": "Recording stopped",
    "image_captured": "Image captured successfully",
}


def get_rtsp_url(stream_type="main"):
    """
    Get RTSP stream URL
    
    Args:
        stream_type: "main" or "sub"
        
    Returns:
        Complete RTSP URL
    """
    if stream_type == "main":
        return GIMBAL_CONFIG["main_stream_url"].format(ip=GIMBAL_CONFIG["camera_ip"])
    else:
        return GIMBAL_CONFIG["sub_stream_url"].format(ip=GIMBAL_CONFIG["camera_ip"])


def validate_config():
    """Validate configuration settings"""
    # Check IP address format
    import re
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(ip_pattern, GIMBAL_CONFIG["camera_ip"]):
        raise ValueError(f"Invalid IP address: {GIMBAL_CONFIG['camera_ip']}")
    
    # Check port ranges
    for port_name in ["control_port", "listen_port", "rtsp_port"]:
        port = GIMBAL_CONFIG[port_name]
        if not (1 <= port <= 65535):
            raise ValueError(f"Invalid {port_name}: {port}")
    
    # Check speed limits
    for speed in ["max_yaw_speed", "max_pitch_speed", "max_roll_speed"]:
        if not (0 <= MOVEMENT_CONFIG[speed] <= 99):
            raise ValueError(f"Invalid {speed}: must be 0-99")
    
    return True


# Validate on import
try:
    validate_config()
except ValueError as e:
    print(f"Configuration Error: {e}")
    raise