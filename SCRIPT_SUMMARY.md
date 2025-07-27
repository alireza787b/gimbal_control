# Gimbal Control Scripts Summary

## New Scripts Created Based on Your Requirements

### 1. **gimbal_full_motion_test.py** - Complete Motion Range Test
This script tests all axes through their complete range with different speeds, exactly as you requested.

**Features:**
- Tests yaw (±150°), pitch (±90°), roll (±90°) full ranges
- Tests different speeds (5°/s to 99°/s max)
- Tests zoom in/out with position reporting
- Tests focus control (auto/manual)
- Logs all commands, responses, and positions to file
- Shows real-time position during movement

**Usage:**
```bash
python gimbal_full_motion_test.py
```

**What it reports:**
- Current angles during movement
- Zoom position values
- Focus position values
- Response times
- Complete command/response log

### 2. **tracking_status_monitor.py** - Tracking Status Monitor
Monitors tracking status and reports all tracking-related data as requested.

**Features:**
- Detects if tracking is active (from native app)
- Reports tracked object screen position (x, y, width, height)
- Reports gimbal angles during tracking
- Shows target distance (if laser ranging available)
- Shows target GPS coordinates (if calculated)
- Shows temperature at target (if thermal available)
- Real-time updates at 2Hz

**Usage:**
```bash
python tracking_status_monitor.py
# Select option 1 for continuous monitoring
```

**What it reports:**
- Tracking active/inactive status
- Target screen coordinates
- Gimbal angles (yaw, pitch, roll)
- Target world position (GPS, distance)
- Temperature at target
- Aircraft position

### 3. **rtsp_stream_viewer.py** - RTSP Video Stream Viewer
Views RTSP stream using OpenCV with GStreamer pipeline options.

**Features:**
- Supports both main and sub streams
- Tests multiple GStreamer pipelines
- Dual stream view (side-by-side)
- Stream with gimbal control (arrow keys)
- Snapshot saving (press 's')
- FPS and resolution display

**Usage:**
```bash
python rtsp_stream_viewer.py
# Select viewing option (1-4)
```

**Stream URLs:**
- Main: `rtsp://192.168.0.108:554/stream=0`
- Sub: `rtsp://192.168.0.108:554/stream=1`

### 4. **protocol_analyzer.py** - Protocol Communication Analyzer
Analyzes all protocol commands systematically.

**Features:**
- Tests ALL commands in the protocol
- Measures response times
- Identifies working vs non-working commands
- Tests async messages (auto-send features)
- Generates comprehensive report

**Usage:**
```bash
python protocol_analyzer.py
# Select option 4 for full analysis
```

**What it reports:**
- Success rate for each command
- Average response times
- Working commands with data
- Failed commands
- Async message patterns

### 5. **gimbal_application_test.py** - Real-World Application Tests
Tests practical gimbal applications as you requested.

**Tests included:**
1. **Surveillance Scan** - Automated scanning pattern
2. **Target Tracking Simulation** - Tracks moving target
3. **Zoom Tracking** - Auto-adjusts zoom based on distance
4. **Thermal Scan** - Scans for temperature anomalies
5. **Recording Modes** - Tests different recording scenarios
6. **Preset Positions** - Save/recall positions

**Usage:**
```bash
python gimbal_application_test.py
# Select test or run all
```

## How the Scripts Work Together

### For Understanding Protocol:
1. Run `protocol_validator.py` - Validates command format
2. Run `protocol_analyzer.py` - Tests all commands
3. Run `test_commands_detailed.py` - Logs detailed communication

### For Motion Testing:
1. Run `unlock_gimbal.py` - Ensure gimbal is unlocked
2. Run `gimbal_full_motion_test.py` - Test complete ranges
3. Check generated log file for all details

### For Tracking:
1. Start tracking in native camera app
2. Run `tracking_status_monitor.py` - Monitor all tracking data
3. Use `test_loc_command.py` to test LOC commands

### For Video:
1. Run `test_sei.py` - Check RTSP connectivity
2. Run `rtsp_stream_viewer.py` - View streams
3. Use option 4 for stream with control

## Key Protocol Insights

### Command Structure:
- Frame headers: `#TP` (fixed), `#tp` (variable), `#tP` (extended)
- Addresses: P=Network, G=Gimbal, M=Lens, D=System, E=Auxiliary
- Control: r=read, w=write
- CRC: Sum of all bytes & 0xFF

### Important Commands:
- **GAC**: Get attitude (returns yaw/pitch/roll)
- **PTZ**: Gimbal control (00=stop, 01=up, 02=down, 03=left, 04=right, 05=home)
- **ZMC**: Zoom control (00=stop, 01=out, 02=in)
- **LOC**: Object tracking (requires x,y,width,height in protocol format)
- **REC**: Recording (00=stop, 01=start, 0A=toggle)
- **CAP**: Capture (01=visible+thermal, 02=visible, 03=thermal)

### Response Format:
- Addresses swapped (PG becomes GP)
- Same identifier returned
- Data in response (if read command)
- CRC at end

## Troubleshooting Tips

1. **No movement but commands work:**
   - Gimbal might be in locked mode
   - Run `unlock_gimbal.py`

2. **Zoom values incorrect:**
   - Values are signed 16-bit (-32768 to 32767)
   - Negative values use two's complement

3. **Tracking not working:**
   - Must be initiated from camera app first
   - Monitor detects active tracking only

4. **Protocol questions:**
   - Check `Protocol.docx` sections referenced in code
   - Use `protocol_analyzer.py` to test specific commands

## Recommended Test Sequence

1. **Initial Setup:**
   ```bash
   python run_diagnostics.py
   python unlock_gimbal.py
   ```

2. **Motion Testing:**
   ```bash
   python gimbal_full_motion_test.py
   # Check motion_test_*.log for details
   ```

3. **Protocol Analysis:**
   ```bash
   python protocol_analyzer.py
   # Choose option 4 for full analysis
   ```

4. **Application Testing:**
   ```bash
   python gimbal_application_test.py
   # Try surveillance scan first
   ```

5. **Continuous Monitoring:**
   ```bash
   python monitor.py  # For attitude
   python tracking_status_monitor.py  # For tracking
   ```

All scripts strictly follow the protocol documentation and use only commands/formats from the provided examples. No assumptions were made beyond what's documented.