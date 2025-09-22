# Gimbal Camera Control System

A comprehensive Python-based control system for SIP series gimbal cameras with open protocol support.

## 📋 Prerequisites

### System Requirements
- Python 3.7 or higher
- Network connection to gimbal camera
- UDP ports 9003 and 9004 available

### Python Dependencies
```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install opencv-python numpy
```

## 🚀 Quick Start Guide

### Step 1: Network Setup

1. **Connect the gimbal camera to your network**
   - Default camera IP: `192.168.144.108` (yours is at `192.168.0.118`)
   - Ensure camera is powered on and network LED is active

2. **Verify network connectivity**
   ```bash
   ping 192.168.0.118
   ```
   You should see successful ping responses.

3. **Check for port conflicts**
   ```bash
   # Linux/Mac
   sudo netstat -ulnp | grep -E '9003|9004'
   
   # Windows
   netstat -an | findstr "9003 9004"
   ```
   These ports should be free.

### Step 2: Configure the System

1. **Edit `config.py`** to match your setup:
   ```python
   GIMBAL_CONFIG = {
       "camera_ip": "192.168.0.118",  # Your camera's IP
       "control_port": 9003,
       "listen_port": 9004,
       # ... other settings
   }
   ```

2. **Test basic connectivity**
   ```bash
   python test_connection.py
   ```
   
   Expected output:
   ```
   === GIMBAL CONNECTION TEST ===
   Target: 192.168.0.118:9003
   ------------------------------
   ✅ SUCCESS! Received response...
   ```

### Step 3: Run the Full Demo

```bash
python gimbal_demo.py
```

This will:
1. Establish connection
2. Read gimbal telemetry (roll, pitch, yaw)
3. Test gimbal movement (up, down, left, right)
4. Test speed control
5. Test camera functions (capture, recording)
6. Display final statistics

## 📁 Project Structure

```
gimbal_control/
├── gimbal_demo.py         # Main demo script
├── gimbalcmdparse.py      # Command building/parsing utilities
├── config.py              # Configuration settings
├── test_connection.py     # Simple connectivity test
├── gimbal_demo.log        # Log file (created after first run)
└── README.md             # This file
```

## 🔧 Configuration Options

### Network Settings (config.py)
- `camera_ip`: IP address of your gimbal camera
- `control_port`: UDP port for sending commands (default: 9003)
- `listen_port`: UDP port for receiving responses (default: 9004)
- `timeout`: Command timeout in seconds

### Movement Settings
- Speed limits (0-99 degrees/second)
- Angle limits for each axis
- Test movement durations

### Demo Behavior
- Enable/disable specific tests
- Auto return to home position
- Statistics display

## 📡 Available Commands

### Basic Movement
```python
controller.control_gimbal("up")     # Move up
controller.control_gimbal("down")   # Move down
controller.control_gimbal("left")   # Move left
controller.control_gimbal("right")  # Move right
controller.control_gimbal("stop")   # Stop movement
controller.control_gimbal("home")   # Return to home
```

### Speed Control
```python
controller.set_gimbal_speed(yaw_speed=10.0, pitch_speed=10.0)
```

### Camera Functions
```python
controller.capture_image()          # Take a photo
controller.start_recording()        # Start video recording
controller.stop_recording()         # Stop video recording
controller.get_zoom_position()      # Get current zoom level
```

### Telemetry
```python
attitude = controller.get_gimbal_attitude()
# Returns: {"yaw": 45.0, "pitch": -10.0, "roll": 0.0}
```

## 🔍 Troubleshooting

### Connection Issues

1. **No response from gimbal**
   - Verify IP address is correct
   - Check network cable/connection
   - Ensure camera is powered on
   - Try disabling firewall temporarily

2. **Port binding errors**
   - Make sure no other application is using ports 9003/9004
   - Run with administrator/sudo privileges if needed

3. **Timeout errors**
   - Increase timeout value in config.py
   - Check network latency with ping

### Command Issues

1. **Invalid responses**
   - Check gimbal firmware version compatibility
   - Verify command format in protocol documentation

2. **Movement not working**
   - Ensure gimbal is not in locked mode
   - Check physical obstructions
   - Verify power supply is adequate

### ⚠️ Common Issues and Solutions

#### Issue: Commands sent but gimbal doesn't move
**Solution:**
1. Run `python gimbal_simple_test.py` first - this tests basic communication
2. Run `python gimbal_troubleshoot.py` for comprehensive diagnostics
3. Check if gimbal is in locked mode - try these unlock commands:
   ```python
   # Set follow mode
   send_command("#TPUG2wPTZ076E")
   # Or try lock/follow switch
   send_command("#TPUG2wPTZ0870")
   ```

#### Issue: Network test fails but communication works
**Solution:**
- Some cameras block ICMP ping but allow UDP traffic
- If `test_connection.py` works, ignore ping failures

#### Issue: Tracking command fails
**Solution:**
- Use the fixed tracking demo that outputs hex format
- Test with `python test_loc_command.py`

#### Issue: Windows console encoding errors
**Solution:**
1. Run `python windows_console_fix.py` first
2. Or set console to UTF-8: `chcp 65001`

#### Issue: No telemetry data in SEI
**Solution:**
1. Install ffmpeg: https://ffmpeg.org/download.html
2. Use `python telemetry_reader.py` for telemetry without ffmpeg
3. Verify RTSP stream works: `vlc rtsp://192.168.0.108:554/stream=0`

### 📋 Diagnostic Steps

1. **First Time Setup:**
   ```bash
   # 1. Run diagnostics
   python run_diagnostics.py
   
   # 2. Test basic connection
   python gimbal_simple_test.py
   
   # 3. If issues persist
   python gimbal_troubleshoot.py
   ```

2. **Generate Debug Log:**
   ```bash
   python test_commands_detailed.py
   ```
   Send the generated log file to developers for analysis.

3. **Network Monitoring:**
   ```bash
   python network_monitor.py
   ```
   Shows all UDP traffic to identify communication issues.

### 🛡️ Firewall Configuration

For Windows Firewall:
1. Open Windows Defender Firewall
2. Click "Allow an app"
3. Add Python.exe from your venv
4. Allow both Private and Public networks
5. Specifically allow UDP ports 9003-9004

### 📊 Understanding the Output

### Telemetry Data
- **Yaw**: Horizontal rotation (-150° to +150°)
- **Pitch**: Vertical tilt (-90° to +90°)
- **Roll**: Side tilt (-90° to +90°)

### Communication Statistics
- **Commands Sent**: Total commands transmitted
- **Responses Received**: Successful responses
- **Success Rate**: Percentage of successful communications

## 🔄 RTSP Video Streaming

The gimbal supports RTSP streaming:
- Main stream: `rtsp://192.168.0.118:554/stream=0`
- Sub stream: `rtsp://192.168.0.118:554/stream=1`

Test with VLC:
```bash
vlc rtsp://192.168.0.118:554/stream=0
```

## 📝 Logging

All operations are logged to `gimbal_demo.log` with timestamps and detail levels:
- INFO: Normal operations
- WARNING: Potential issues
- ERROR: Failures
- DEBUG: Detailed protocol data (enable in config.py)

## 🛠️ Advanced Usage

### Custom Commands
```python
from gimbalcmdparse import build_command

# Build custom command
cmd = build_command(
    frame_header='#TP',
    address_bit1='P',     # Network source
    address_bit2='G',     # Gimbal destination
    control_bit='w',      # Write command
    identifier_bit='PTZ',  # Command type
    data='01',            # Command data
    output_format='ASCII'
)
```

### Continuous Telemetry Monitoring
```python
while True:
    attitude = controller.get_gimbal_attitude()
    if attitude:
        print(f"Y:{attitude['yaw']:6.2f} P:{attitude['pitch']:6.2f} R:{attitude['roll']:6.2f}")
    time.sleep(0.1)
```

## ⚠️ Important Notes

1. **Power Requirements**: Ensure adequate power supply for gimbal motors
2. **Network Stability**: Use wired connection for best reliability
3. **Movement Limits**: Respect physical angle limits to avoid damage
4. **Firmware Compatibility**: This code follows SIP series protocol v1.1.3

## 📚 Additional Resources

- Protocol Documentation: See `Protocol.docx` for complete command reference
- Example Commands: Check individual `*_cmd.py` files for specific operations
- SEI Data Parsing: Use `pythonSampleCode_ParseSEI.py` for video metadata

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section
2. Review log files for detailed error messages
3. Consult the protocol documentation
4. Verify network and hardware setup

---

Happy Gimbal Controlling! 🎥