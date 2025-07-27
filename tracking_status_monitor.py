#!/usr/bin/env python3
"""
Tracking Status Monitor
=======================
Monitor tracking status and tracked object information.
Based on protocol LOC command and GPS/ranging data.
"""

# WORKING!!!

import socket
import time
import struct
from datetime import datetime
from config import GIMBAL_CONFIG


class TrackingMonitor:
    def __init__(self):
        self.camera_ip = GIMBAL_CONFIG['camera_ip']
        self.control_port = GIMBAL_CONFIG['control_port']
        self.listen_port = GIMBAL_CONFIG['listen_port']
        
        # Sockets
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock.bind(('0.0.0.0', self.listen_port))
        self.recv_sock.settimeout(0.5)
        
        # Tracking data
        self.tracking_data = {
            'is_tracking': False,
            'target_screen': {'x': 0, 'y': 0, 'width': 0, 'height': 0},
            'target_world': {'lon': 0.0, 'lat': 0.0, 'distance': 0.0},
            'gimbal_angles': {'magnetic': None, 'gyroscope': None},
            'aircraft_position': {'lon': 0.0, 'lat': 0.0, 'alt': 0.0},
            'last_update': None
        }
        
        self.previous_angles = {}
        
    def send_command(self, cmd_bytes):
        """Send command"""
        self.sock.sendto(cmd_bytes, (self.camera_ip, self.control_port))
        
    def get_attitude(self):
        """Get gimbal attitude - both magnetic and gyroscope"""
        attitudes = {}
        
        # Get magnetic attitude (GAC - protocol 4.3.3)
        self.send_command(b"#TPPG2rGAC002D")
        
        try:
            data, _ = self.recv_sock.recvfrom(1024)
            resp_str = data.decode('ascii', errors='replace')
            
            if 'GAC' in resp_str:
                idx = resp_str.find('GAC') + 3
                if idx + 12 <= len(resp_str):
                    yaw_hex = resp_str[idx:idx+4]
                    pitch_hex = resp_str[idx+4:idx+8]
                    roll_hex = resp_str[idx+8:idx+12]
                    
                    yaw = int(yaw_hex, 16)
                    pitch = int(pitch_hex, 16)
                    roll = int(roll_hex, 16)
                    
                    if yaw > 0x7FFF: yaw -= 0x10000
                    if pitch > 0x7FFF: pitch -= 0x10000
                    if roll > 0x7FFF: roll -= 0x10000
                    
                    attitudes['magnetic'] = {
                        'yaw': yaw / 100.0,
                        'pitch': pitch / 100.0,
                        'roll': roll / 100.0
                    }
        except:
            pass
        
        # Get gyroscope attitude (GIC - protocol 4.3.5)
        self.send_command(b"#TPUG2rGIC003A")
        
        try:
            data, _ = self.recv_sock.recvfrom(1024)
            resp_str = data.decode('ascii', errors='replace')
            
            if 'GIC' in resp_str:
                idx = resp_str.find('GIC') + 3
                if idx + 12 <= len(resp_str):
                    yaw_hex = resp_str[idx:idx+4]
                    pitch_hex = resp_str[idx+4:idx+8]
                    roll_hex = resp_str[idx+8:idx+12]
                    
                    yaw = int(yaw_hex, 16)
                    pitch = int(pitch_hex, 16)
                    roll = int(roll_hex, 16)
                    
                    if yaw > 0x7FFF: yaw -= 0x10000
                    if pitch > 0x7FFF: pitch -= 0x10000
                    if roll > 0x7FFF: roll -= 0x10000
                    
                    attitudes['gyroscope'] = {
                        'yaw': yaw / 100.0,
                        'pitch': pitch / 100.0,
                        'roll': roll / 100.0
                    }
        except:
            pass
            
        return attitudes
    
    def check_ranging_data(self):
        """Check if laser ranging data available (protocol 5.9)"""
        # Try to get ranging data
        # Note: Ranging data is auto-sent after measurement per protocol
        try:
            # Check for any pending ranging data
            self.recv_sock.settimeout(0.1)
            data, _ = self.recv_sock.recvfrom(1024)
            resp_str = data.decode('ascii', errors='replace')
            
            if 'LRF' in resp_str and 'w' in resp_str:
                # Found ranging data
                idx = resp_str.find('LRF') + 3
                if idx + 7 <= len(resp_str):
                    range_str = resp_str[idx:idx+7]  # X1X2X3X4X5.X6 format
                    if range_str[:3] != 'ERR':
                        try:
                            distance = float(range_str)
                            self.tracking_data['target_world']['distance'] = distance
                            return distance
                        except:
                            pass
        except socket.timeout:
            pass
        return None
    
    def check_temperature_at_target(self):
        """Check temperature at tracked position (protocol 5.12)"""
        # Only check if we have a tracked position
        if not self.tracking_data['is_tracking']:
            return None
            
        target = self.tracking_data['target_screen']
        if target['x'] == 0 and target['y'] == 0:
            return None
        
        # Build temperature query command for target position
        # Using protocol 5.12.3 format for point temperature
        x = target['x']
        y = target['y']
        
        # Convert to thermal camera coordinates (320x256 per protocol)
        thermal_x = int(x * 320 / 1920)
        thermal_y = int(y * 256 / 1080)
        
        # Build command: #tpPDArTMPXXXYYY WW HH
        cmd_str = f"#tpPD6rTMP{thermal_x:03d}{thermal_y:03d}0000"
        crc = sum(cmd_str.encode('ascii')) & 0xFF
        cmd_str += f"{crc:02X}"
        
        self.send_command(cmd_str.encode('ascii'))
        
        try:
            data, _ = self.recv_sock.recvfrom(1024)
            resp_str = data.decode('ascii', errors='replace')
            
            if 'TMP' in resp_str:
                # Parse temperature response
                idx = resp_str.find('TMP') + 3
                if idx + 10 <= len(resp_str):
                    # Skip coordinates, get temperature (last 4 chars)
                    temp_hex = resp_str[idx+10:idx+14]
                    try:
                        temp_raw = int(temp_hex, 16)
                        if temp_raw > 0x7FFF: temp_raw -= 0x10000
                        temp_c = temp_raw / 100.0  # 0.01°C units
                        return temp_c
                    except:
                        pass
        except socket.timeout:
            pass
        return None
    
    def parse_gps_data(self):
        """Parse GPS data if being sent (protocol 5.8)"""
        # GPS data might be sent automatically or we need to query
        # Check for any GPS data in receive buffer
        try:
            self.recv_sock.settimeout(0.1)
            data, _ = self.recv_sock.recvfrom(1024)
            resp_str = data.decode('ascii', errors='replace')
            
            # Check for longitude (LON)
            if 'LON' in resp_str and 'w' in resp_str:
                idx = resp_str.find('LON') + 3
                if idx + 11 <= len(resp_str):
                    ew = resp_str[idx]  # E or W
                    lon_str = resp_str[idx+1:idx+11]  # ddd.dddddd
                    try:
                        lon = float(lon_str)
                        if ew == 'W':
                            lon = -lon
                        
                        # Check if it's target or aircraft position
                        # Target position is calculated, aircraft is raw GPS
                        if 'target' in resp_str.lower():
                            self.tracking_data['target_world']['lon'] = lon
                        else:
                            self.tracking_data['aircraft_position']['lon'] = lon
                    except:
                        pass
            
            # Check for latitude (LAT)
            if 'LAT' in resp_str and 'w' in resp_str:
                idx = resp_str.find('LAT') + 3
                if idx + 10 <= len(resp_str):
                    ns = resp_str[idx]  # N or S
                    lat_str = resp_str[idx+1:idx+10]  # dd.dddddd
                    try:
                        lat = float(lat_str)
                        if ns == 'S':
                            lat = -lat
                        
                        if 'target' in resp_str.lower():
                            self.tracking_data['target_world']['lat'] = lat
                        else:
                            self.tracking_data['aircraft_position']['lat'] = lat
                    except:
                        pass
                        
        except socket.timeout:
            pass
    
    def check_tracking_status(self):
        """Check if tracking is active and get target info"""
        # First get gimbal attitudes (both types)
        attitudes = self.get_attitude()
        if attitudes:
            self.tracking_data['gimbal_angles'] = attitudes
        
        # Check for movement patterns that indicate tracking
        # If gimbal is moving smoothly, it might be tracking
        if hasattr(self, 'previous_angles') and 'gyroscope' in attitudes:
            current = attitudes['gyroscope']
            previous = self.previous_angles.get('gyroscope', current)
            
            # Calculate angular velocity
            yaw_vel = abs(current['yaw'] - previous['yaw'])
            pitch_vel = abs(current['pitch'] - previous['pitch'])
            
            # If gimbal is moving, might be tracking
            if yaw_vel > 0.1 or pitch_vel > 0.1:
                self.tracking_data['is_tracking'] = True
                self.tracking_data['angular_velocity'] = {
                    'yaw': yaw_vel,
                    'pitch': pitch_vel
                }
        
        self.previous_angles = attitudes.copy() if attitudes else {}
        
        # Check for ranging data (indicates active tracking with laser)
        distance = self.check_ranging_data()
        if distance is not None:
            self.tracking_data['is_tracking'] = True
            self.tracking_data['target_world']['distance'] = distance
        
        # Check for GPS data
        self.parse_gps_data()
        
        # Check temperature at target
        if self.tracking_data['is_tracking']:
            temp = self.check_temperature_at_target()
            if temp is not None:
                self.tracking_data['target_world']['temperature'] = temp
        
        # Update timestamp
        self.tracking_data['last_update'] = datetime.now()
        
        return self.tracking_data
    
    def display_tracking_info(self):
        """Display tracking information"""
        print("\n" + "="*60)
        print("TRACKING STATUS MONITOR")
        print("="*60)
        print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
        
        data = self.tracking_data
        
        if data['is_tracking']:
            print("\n[TRACKING ACTIVE]")
            
            # Angular velocity if available
            if 'angular_velocity' in data:
                vel = data['angular_velocity']
                print(f"Angular velocity: Yaw={vel['yaw']:.2f}°/update Pitch={vel['pitch']:.2f}°/update")
            
            # Target screen position
            target = data['target_screen']
            if target['x'] > 0 or target['y'] > 0:
                print(f"\nTarget Screen Position:")
                print(f"  Position: ({target['x']}, {target['y']})")
                print(f"  Size: {target['width']}x{target['height']}")
            
            # Gimbal angles - both types
            angles = data['gimbal_angles']
            if 'magnetic' in angles:
                mag = angles['magnetic']
                print(f"\nMagnetic Angles (Fixed to mount):")
                print(f"  Yaw:   {mag['yaw']:7.2f}°")
                print(f"  Pitch: {mag['pitch']:7.2f}°")
                print(f"  Roll:  {mag['roll']:7.2f}°")
            
            if 'gyroscope' in angles:
                gyro = angles['gyroscope']
                print(f"\nGyroscope Angles (Absolute spatial):")
                print(f"  Yaw:   {gyro['yaw']:7.2f}°")
                print(f"  Pitch: {gyro['pitch']:7.2f}°")
                print(f"  Roll:  {gyro['roll']:7.2f}°")
            
            # Show difference between angle types
            if 'magnetic' in angles and 'gyroscope' in angles:
                mag = angles['magnetic']
                gyro = angles['gyroscope']
                print(f"\nAngle Difference (Gyro - Magnetic):")
                print(f"  Yaw:   {gyro['yaw'] - mag['yaw']:7.2f}°")
                print(f"  Pitch: {gyro['pitch'] - mag['pitch']:7.2f}°")
                print(f"  Roll:  {gyro['roll'] - mag['roll']:7.2f}°")
            
            # Target world position
            world = data['target_world']
            if world['distance'] > 0:
                print(f"\nTarget World Info:")
                print(f"  Distance: {world['distance']:.1f} m")
                
                if world['lat'] != 0 or world['lon'] != 0:
                    print(f"  GPS: {world['lat']:.6f}°, {world['lon']:.6f}°")
                
                if 'temperature' in world:
                    print(f"  Temperature: {world['temperature']:.1f}°C")
            
            # Aircraft position
            aircraft = data['aircraft_position']
            if aircraft['lat'] != 0 or aircraft['lon'] != 0:
                print(f"\nAircraft Position:")
                print(f"  GPS: {aircraft['lat']:.6f}°, {aircraft['lon']:.6f}°")
                print(f"  Altitude: {aircraft['alt']:.1f} m")
                
        else:
            print("\n[NO ACTIVE TRACKING]")
            print("Tip: Use manual_tracking_control.py to start tracking")
            
            # Still show gimbal angles
            angles = data['gimbal_angles']
            if 'magnetic' in angles:
                mag = angles['magnetic']
                print(f"\nMagnetic Angles (Fixed to mount):")
                print(f"  Yaw:   {mag['yaw']:7.2f}°")
                print(f"  Pitch: {mag['pitch']:7.2f}°")
                print(f"  Roll:  {mag['roll']:7.2f}°")
            
            if 'gyroscope' in angles:
                gyro = angles['gyroscope']
                print(f"\nGyroscope Angles (Absolute spatial):")
                print(f"  Yaw:   {gyro['yaw']:7.2f}°")
                print(f"  Pitch: {gyro['pitch']:7.2f}°")
                print(f"  Roll:  {gyro['roll']:7.2f}°")
    
    def monitor_continuously(self):
        """Monitor tracking status continuously"""
        print("Starting tracking monitor...")
        print("Press Ctrl+C to stop")
        print("\nNote: Tracking must be initiated from camera's native app")
        print("This monitor will detect and report active tracking\n")
        
        try:
            while True:
                self.check_tracking_status()
                
                # Clear screen and display
                import os
                os.system('cls' if os.name == 'nt' else 'clear')
                self.display_tracking_info()
                
                time.sleep(0.5)  # Update at 2Hz
                
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped.")
        finally:
            self.sock.close()
            self.recv_sock.close()
    
    def test_tracking_simulation(self):
        """Simulate tracking by sending LOC command"""
        print("\nStarting manual tracking...")
        
        # Send LOC command to track center of screen
        x, y = 960, 540
        width, height = 100, 100
        
        # Calculate protocol values (from LOC_cmd.py)
        param_x = round(2000 * x / 1920 - 1000)
        param_y = round(2000 * y / 1080 - 1000)
        param_w = round(2000 * width / 1920)
        param_h = round(2000 * height / 1080)
        blur_click = 8
        
        # Pack data
        vals = (param_x, param_y, param_w, param_h, blur_click)
        data_bytes = b''.join(struct.pack('>h', v) for v in vals)
        data_hex = data_bytes.hex().upper()
        
        # Build command
        data_len = len(data_bytes)
        cmd = f"#tpPD{data_len:X}wLOC" + data_hex
        crc = sum(cmd.encode('ascii')) & 0xFF
        cmd += f"{crc:02X}"
        
        print(f"Sending LOC command: {cmd}")
        print(f"Target: ({x},{y}) Size: {width}x{height}")
        self.send_command(cmd.encode('ascii'))
        
        # Update tracking data
        self.tracking_data['is_tracking'] = True
        self.tracking_data['target_screen'] = {'x': x, 'y': y, 'width': width, 'height': height}
        
        print("Manual tracking started at center of screen.")
        print("Note: The gimbal should now be tracking this position.")


def main():
    print("="*60)
    print("TRACKING STATUS MONITOR")
    print("="*60)
    print("\nOptions:")
    print("1. Monitor tracking status continuously")
    print("2. Start manual tracking (center)")
    print("3. Single status check")
    print("4. Start manual tracking then monitor")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    monitor = TrackingMonitor()
    
    if choice == '1':
        monitor.monitor_continuously()
    elif choice == '2':
        monitor.test_tracking_simulation()
        time.sleep(2)
        monitor.check_tracking_status()
        monitor.display_tracking_info()
    elif choice == '3':
        monitor.check_tracking_status()
        monitor.display_tracking_info()
    elif choice == '4':
        monitor.test_tracking_simulation()
        time.sleep(1)
        monitor.monitor_continuously()
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()