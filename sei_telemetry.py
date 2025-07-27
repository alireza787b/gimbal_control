#!/usr/bin/env python3
"""
SEI Telemetry Data Parser
=========================
Parse telemetry data embedded in video stream SEI NAL units.
Based on the provided SEI parsing example.
"""

import threading
import subprocess
import struct
import cv2
import time
import json
from datetime import datetime
from config import GIMBAL_CONFIG, get_rtsp_url


# SEI data structure format (from C struct)
SEI_STRUCT_FORMAT = (
    '<ddfHBBBBfiii ddhhh'
    'iHHHHHHHIII'
)

# Field names corresponding to struct format
SEI_FIELDS = [
    "plane_lon", "plane_lat", "plane_alt",
    "gps_year", "gps_month", "gps_day", "gps_hour", "gps_minute", "gps_second",
    "gimbal_yaw", "gimbal_roll", "gimbal_pitch",
    "target_lon", "target_lat",
    "target_x", "target_y", "target_size",
    "distance",
    "highTemperature_x", "highTemperature_y", "highTemperature",
    "lowTemperature_x", "lowTemperature_y", "lowTemperature",
    "centerTemperature",
    "opticalZoom", "digitalZoom",
    "frame_id"
]

# Expected struct size
EXPECTED_STRUCT_SIZE = struct.calcsize(SEI_STRUCT_FORMAT)

# SEI UUID identifier
SEI_UUID = bytes([
    0xA1, 0xB2, 0xC3, 0xD4, 0xE5, 0xF6, 0xA7, 0xB8,
    0xC9, 0xDA, 0xEB, 0xFC, 0x1A, 0x2B, 0x3C, 0x4D
])

# Global storage for latest SEI data
latest_sei = {}
sei_lock = threading.Lock()
telemetry_log = []


def parse_sei_payload(sei_payload: bytes) -> dict:
    """Parse SEI payload into structured data"""
    if len(sei_payload) < EXPECTED_STRUCT_SIZE:
        return None
    
    try:
        unpacked = struct.unpack(SEI_STRUCT_FORMAT, sei_payload[:EXPECTED_STRUCT_SIZE])
        data = dict(zip(SEI_FIELDS, unpacked))
        
        # Convert units for display
        data["gimbal_yaw_deg"] = data["gimbal_yaw"] / 100.0
        data["gimbal_pitch_deg"] = data["gimbal_pitch"] / 100.0
        data["gimbal_roll_deg"] = data["gimbal_roll"] / 100.0
        data["distance_m"] = data["distance"] / 10.0
        data["highTemp_C"] = data["highTemperature"] / 10.0
        data["lowTemp_C"] = data["lowTemperature"] / 10.0
        data["centerTemp_C"] = data["centerTemperature"] / 10.0
        
        return data
    except Exception as e:
        print(f"Error parsing SEI payload: {e}")
        return None


def parse_sei_nal(payload: bytes) -> bytes:
    """Extract SEI payload from NAL unit"""
    i = 0
    
    # Parse payload type
    payload_type = 0
    while i < len(payload) and payload[i] == 0xFF:
        payload_type += 0xFF
        i += 1
    if i < len(payload):
        payload_type += payload[i]
        i += 1
    
    # Parse payload size
    payload_size = 0
    while i < len(payload) and payload[i] == 0xFF:
        payload_size += 0xFF
        i += 1
    if i < len(payload):
        payload_size += payload[i]
        i += 1
    
    # Check for user data unregistered (type 5)
    if payload_type != 5:
        return None
    
    # Check UUID
    if i + 16 > len(payload):
        return None
    uuid = payload[i:i+16]
    i += 16
    
    if uuid != SEI_UUID:
        return None
    
    # Return SEI payload
    return payload[i:]


def sei_reader(rtsp_url: str, codec: str = "h264"):
    """Background thread to read SEI data from RTSP stream"""
    if codec == "h264":
        bsf_filter = "h264_mp4toannexb"
        output_fmt = "h264"
        sei_nalu_types = [6]
    elif codec == "h265":
        bsf_filter = "hevc_mp4toannexb"
        output_fmt = "hevc"
        sei_nalu_types = [39, 40]
    else:
        raise ValueError(f"Unsupported codec: {codec}")
    
    cmd = [
        "ffmpeg", "-rtsp_transport", "udp", "-i", rtsp_url,
        "-an", "-c:v", "copy",
        "-bsf:v", bsf_filter,
        "-f", output_fmt, "-"
    ]
    
    print(f"Starting SEI reader for {rtsp_url}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    buf = b""
    
    try:
        while True:
            chunk = proc.stdout.read(4096)
            if not chunk:
                break
            
            buf += chunk
            
            # Look for NAL units
            while True:
                i = buf.find(b"\x00\x00\x00\x01")
                if i < 0:
                    break
                
                j = buf.find(b"\x00\x00\x00\x01", i+4)
                if j < 0:
                    break
                
                nal = buf[i+4:j]
                buf = buf[j:]
                
                if len(nal) < 3:
                    continue
                
                # Parse NAL type
                if codec == "h264":
                    nal_type = nal[0] & 0x1F
                    payload = nal[1:]
                else:
                    nal_type = (nal[0] >> 1) & 0x3F
                    payload = nal[2:]
                
                # Check if SEI NAL
                if nal_type in sei_nalu_types:
                    sei_payload = parse_sei_nal(payload)
                    if sei_payload:
                        data = parse_sei_payload(sei_payload)
                        if data:
                            with sei_lock:
                                latest_sei.clear()
                                latest_sei.update(data)
                                latest_sei["timestamp"] = time.time()
                                
                                # Log telemetry
                                if len(telemetry_log) > 1000:
                                    telemetry_log.pop(0)
                                telemetry_log.append(data.copy())
                                
    finally:
        proc.kill()
        print("SEI reader stopped")


def display_telemetry():
    """Display telemetry data in terminal"""
    import os
    
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("╔════════════════════════════════════════════════════════╗")
        print("║              SEI TELEMETRY DATA DISPLAY                ║")
        print("╚════════════════════════════════════════════════════════╝")
        print()
        
        with sei_lock:
            if not latest_sei:
                print("Waiting for telemetry data...")
            else:
                # GPS Data
                print("GPS INFORMATION")
                print("─" * 58)
                print(f"Aircraft Position: {latest_sei.get('plane_lat', 0):.6f}°, "
                      f"{latest_sei.get('plane_lon', 0):.6f}°")
                print(f"Altitude: {latest_sei.get('plane_alt', 0):.1f} m")
                
                gps_time = f"{latest_sei.get('gps_year', 0)}-"
                gps_time += f"{latest_sei.get('gps_month', 0):02d}-"
                gps_time += f"{latest_sei.get('gps_day', 0):02d} "
                gps_time += f"{latest_sei.get('gps_hour', 0):02d}:"
                gps_time += f"{latest_sei.get('gps_minute', 0):02d}:"
                gps_time += f"{latest_sei.get('gps_second', 0):.1f}"
                print(f"GPS Time: {gps_time}")
                
                # Gimbal Attitude
                print("\nGIMBAL ATTITUDE")
                print("─" * 58)
                print(f"Yaw:   {latest_sei.get('gimbal_yaw_deg', 0):7.2f}°")
                print(f"Pitch: {latest_sei.get('gimbal_pitch_deg', 0):7.2f}°")
                print(f"Roll:  {latest_sei.get('gimbal_roll_deg', 0):7.2f}°")
                
                # Target Information
                if latest_sei.get('target_lon', 0) != 0:
                    print("\nTARGET INFORMATION")
                    print("─" * 58)
                    print(f"Target Position: {latest_sei.get('target_lat', 0):.6f}°, "
                          f"{latest_sei.get('target_lon', 0):.6f}°")
                    print(f"Target Screen: ({latest_sei.get('target_x', 0)}, "
                          f"{latest_sei.get('target_y', 0)})")
                    print(f"Distance: {latest_sei.get('distance_m', 0):.1f} m")
                
                # Temperature Data
                if latest_sei.get('highTemperature', 0) > 0:
                    print("\nTEMPERATURE DATA")
                    print("─" * 58)
                    print(f"High: {latest_sei.get('highTemp_C', 0):.1f}°C at "
                          f"({latest_sei.get('highTemperature_x', 0)}, "
                          f"{latest_sei.get('highTemperature_y', 0)})")
                    print(f"Low: {latest_sei.get('lowTemp_C', 0):.1f}°C at "
                          f"({latest_sei.get('lowTemperature_x', 0)}, "
                          f"{latest_sei.get('lowTemperature_y', 0)})")
                    print(f"Center: {latest_sei.get('centerTemp_C', 0):.1f}°C")
                
                # Camera Settings
                print("\nCAMERA SETTINGS")
                print("─" * 58)
                print(f"Optical Zoom: {latest_sei.get('opticalZoom', 0)}x")
                print(f"Digital Zoom: {latest_sei.get('digitalZoom', 0)}x")
                print(f"Frame ID: {latest_sei.get('frame_id', 0)}")
                
                # Update rate
                if 'timestamp' in latest_sei:
                    age = time.time() - latest_sei['timestamp']
                    print(f"\nLast update: {age:.1f}s ago")
        
        print("\nPress Ctrl+C to exit")
        time.sleep(0.1)


def save_telemetry_log(filename: str = "telemetry_log.json"):
    """Save telemetry log to file"""
    with sei_lock:
        with open(filename, 'w') as f:
            json.dump(telemetry_log, f, indent=2)
    print(f"Telemetry log saved to {filename}")


def main():
    """Main function"""
    import sys
    
    # Get RTSP URL
    rtsp_url = get_rtsp_url("main")
    codec = "h264"  # or "h265" depending on your camera
    
    print(f"Connecting to {rtsp_url}")
    print("This will parse telemetry data embedded in the video stream")
    print("-" * 60)
    
    # Start SEI reader thread
    reader_thread = threading.Thread(
        target=sei_reader, 
        args=(rtsp_url, codec),
        daemon=True
    )
    reader_thread.start()
    
    # Display mode or overlay mode
    if len(sys.argv) > 1 and sys.argv[1] == '--overlay':
        # Video overlay mode
        print("Starting video overlay mode...")
        time.sleep(2)  # Wait for SEI data
        
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            print("Cannot open RTSP stream")
            return
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Overlay telemetry data
            with sei_lock:
                y = 30
                cv2.putText(frame, "SEI TELEMETRY DATA", (10, y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                y += 30
                
                if latest_sei:
                    # Show key telemetry
                    text_items = [
                        f"Gimbal: Y:{latest_sei.get('gimbal_yaw_deg', 0):.1f} "
                        f"P:{latest_sei.get('gimbal_pitch_deg', 0):.1f} "
                        f"R:{latest_sei.get('gimbal_roll_deg', 0):.1f}",
                        f"GPS: {latest_sei.get('plane_lat', 0):.6f}, "
                        f"{latest_sei.get('plane_lon', 0):.6f}",
                        f"Alt: {latest_sei.get('plane_alt', 0):.1f}m",
                        f"Zoom: {latest_sei.get('opticalZoom', 0)}x"
                    ]
                    
                    for text in text_items:
                        cv2.putText(frame, text, (10, y),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
                        y += 25
            
            cv2.imshow("Gimbal Video + Telemetry", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
    else:
        # Terminal display mode
        try:
            display_telemetry()
        except KeyboardInterrupt:
            print("\n\nSaving telemetry log...")
            save_telemetry_log()
            print("Done.")


if __name__ == "__main__":
    main()