#!/usr/bin/env python3
"""
Gimbal Tracking Angle Monitor
=============================
Monitors gimbal angles relative to robot body during tracking.
When tracking is active, these angles represent the target position
since the gimbal keeps the target centered in view.
"""

import socket
import time
import struct
import threading
from datetime import datetime
from gimbalcmdparse import build_command
from config import GIMBAL_CONFIG
import os


class TrackingAngleMonitor:
    def __init__(self):
        self.camera_ip = GIMBAL_CONFIG['camera_ip']
        self.control_port = GIMBAL_CONFIG['control_port']
        self.listen_port = GIMBAL_CONFIG['listen_port']
        
        # Communication sockets
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock.bind(('0.0.0.0', self.listen_port))
        self.recv_sock.settimeout(0.1)
        
        # State tracking
        self.monitoring = False
        self.tracking_status = {'mode': 0, 'status': 0}
        self.last_angles = None
        self.last_gps = None
        
    def get_tracking_status(self):
        """Get tracking status using TRC command (protocol section 2)"""
        try:
            # Build TRC read command
            cmd = build_command(
                frame_header='#TP',
                address_bit1='P',
                address_bit2='D',
                control_bit='r',
                identifier_bit='TRC',
                data='00',
                data_mode='ASCII',
                output_format='ASCII'
            )
            
            self.sock.sendto(cmd.encode('ascii'), (self.camera_ip, self.control_port))
            
            # Wait for response
            data, _ = self.recv_sock.recvfrom(1024)
            resp = data.decode('ascii', errors='replace')
            
            if 'TRC' in resp:
                # Parse R1R2 from response
                idx = resp.find('TRC') + 3
                if idx + 2 <= len(resp):
                    r1 = resp[idx]     # Tracking mode
                    r2 = resp[idx+1]   # Tracking status
                    
                    mode = int(r1) if r1.isdigit() else 0
                    status = int(r2) if r2.isdigit() else 0
                    
                    self.tracking_status = {
                        'mode': mode,
                        'status': status,
                        'mode_desc': self._get_mode_desc(mode),
                        'status_desc': self._get_status_desc(status)
                    }
                    
                    return self.tracking_status
                    
        except Exception as e:
            pass
        
        return None
    
    def _get_mode_desc(self, mode):
        """Get mode description"""
        modes = {
            0: "Reserved"
        }
        return modes.get(mode, f"Unknown ({mode})")
    
    def _get_status_desc(self, status):
        """Get status description from protocol"""
        statuses = {
            0: "Tracking not enabled",
            1: "Target to be selected",
            2: "Tracker in tracking state",
            3: "Tracking temporarily lost"
        }
        return statuses.get(status, f"Unknown ({status})")
    
    def get_gimbal_angles(self):
        """Get magnetic angles (relative to mount) - Protocol 4.3.3"""
        try:
            # Build GAC command
            cmd = build_command(
                frame_header='#TP',
                address_bit1='P',
                address_bit2='G',
                control_bit='r',
                identifier_bit='GAC',
                data='00',
                data_mode='ASCII',
                output_format='ASCII'
            )
            
            self.sock.sendto(cmd.encode('ascii'), (self.camera_ip, self.control_port))
            
            # Parse response
            data, _ = self.recv_sock.recvfrom(1024)
            resp = data.decode('ascii', errors='replace')
            
            if 'GAC' in resp:
                idx = resp.find('GAC') + 3
                if idx + 12 <= len(resp):
                    # Extract angle values (4 chars each)
                    yaw_hex = resp[idx:idx+4]
                    pitch_hex = resp[idx+4:idx+8]
                    roll_hex = resp[idx+8:idx+12]
                    
                    # Convert from hex string to signed integers
                    yaw = int(yaw_hex, 16)
                    pitch = int(pitch_hex, 16)
                    roll = int(roll_hex, 16)
                    
                    # Handle signed values (16-bit)
                    if yaw > 0x7FFF: yaw -= 0x10000
                    if pitch > 0x7FFF: pitch -= 0x10000
                    if roll > 0x7FFF: roll -= 0x10000
                    
                    # Convert to degrees (0.01 degree units)
                    angles = {
                        'yaw': yaw / 100.0,
                        'pitch': pitch / 100.0,
                        'roll': roll / 100.0,
                        'timestamp': time.time()
                    }
                    
                    self.last_angles = angles
                    return angles
                    
        except Exception as e:
            pass
        
        return None
    
    def check_gps_capability(self):
        """Check if GPS data is available - Protocol 5.8"""
        # Try to read GPS data to see if module has GPS
        # Note: The protocol shows GPS commands exist but doesn't specify
        # if all modules have GPS hardware
        pass
    
    def enable_attitude_auto_send(self):
        """Enable automatic attitude sending - Protocol 4.3.4"""
        try:
            cmd = build_command(
                frame_header='#TP',
                address_bit1='P',
                address_bit2='G',
                control_bit='w',
                identifier_bit='GAA',
                data='01',  # Enable
                data_mode='ASCII',
                output_format='ASCII'
            )
            
            self.sock.sendto(cmd.encode('ascii'), (self.camera_ip, self.control_port))
            print("✓ Enabled automatic attitude reporting")
            return True
            
        except Exception as e:
            print(f"✗ Failed to enable auto attitude: {e}")
            return False
    
    def monitor_tracking_angles(self, update_rate=10):
        """Monitor gimbal angles during tracking"""
        print("\033[2J\033[H")  # Clear screen
        print("\033[?25l")      # Hide cursor
        
        self.monitoring = True
        update_interval = 1.0 / update_rate
        last_update = 0
        
        # Enable automatic attitude sending
        self.enable_attitude_auto_send()
        
        print("\033[1;36m" + "="*70 + "\033[0m")
        print("\033[1;33mGIMBAL TRACKING ANGLE MONITOR\033[0m")
        print("\033[1;36m" + "="*70 + "\033[0m")
        print("When tracking is active, gimbal angles = target position relative to mount")
        print("Press Ctrl+C to stop\n")
        
        try:
            while self.monitoring:
                current_time = time.time()
                
                if current_time - last_update >= update_interval:
                    last_update = current_time
                    
                    # Get tracking status
                    tracking_status = self.get_tracking_status()
                    
                    # Get gimbal angles
                    angles = self.get_gimbal_angles()
                    
                    # Update display
                    self._update_display(tracking_status, angles)
                
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped")
        finally:
            print("\033[?25h")  # Show cursor
            self.monitoring = False
    
    def _update_display(self, tracking_status, angles):
        """Update the display with current data"""
        # Move cursor to position
        print("\033[8;0H")  # Row 8, column 0
        
        # Tracking Status Section
        print("\033[1;34m📊 TRACKING STATUS\033[0m")
        print("-" * 40)
        
        if tracking_status:
            status_color = "\033[1;32m" if tracking_status['status'] == 2 else "\033[1;33m"
            print(f"Status: {status_color}{tracking_status['status_desc']}\033[0m")
            
            # Visual indicator
            if tracking_status['status'] == 2:
                print("State:  \033[1;32m● TRACKING ACTIVE\033[0m")
            elif tracking_status['status'] == 1:
                print("State:  \033[1;33m◐ WAITING FOR TARGET\033[0m")
            elif tracking_status['status'] == 3:
                print("State:  \033[1;31m◯ TEMPORARILY LOST\033[0m")
            else:
                print("State:  \033[1;90m○ INACTIVE\033[0m")
        else:
            print("Status: \033[1;31mNo response\033[0m")
        
        print()
        
        # Gimbal Angles Section
        print("\033[1;34m🎯 GIMBAL ANGLES (Target Position)\033[0m")
        print("-" * 40)
        
        if angles:
            # Color code based on tracking status
            if tracking_status and tracking_status['status'] == 2:
                print("\033[1;32m[TRACKING - Angles represent target position]\033[0m")
            else:
                print("\033[1;90m[NOT TRACKING - Angles show gimbal orientation]\033[0m")
            
            print(f"\nYaw:   \033[1;37m{angles['yaw']:8.2f}°\033[0m  ", end="")
            self._draw_angle_bar(angles['yaw'], -150, 150)
            
            print(f"\nPitch: \033[1;37m{angles['pitch']:8.2f}°\033[0m  ", end="")
            self._draw_angle_bar(angles['pitch'], -90, 90)
            
            print(f"\nRoll:  \033[1;37m{angles['roll']:8.2f}°\033[0m  ", end="")
            self._draw_angle_bar(angles['roll'], -90, 90)
            
            # Calculate target bearing if tracking
            if tracking_status and tracking_status['status'] == 2:
                bearing = (angles['yaw'] + 360) % 360
                elevation = angles['pitch']
                
                print(f"\n\n\033[1;35mTarget Bearing:\033[0m {bearing:.1f}° (from North)")
                print(f"\033[1;35mTarget Elevation:\033[0m {elevation:.1f}°")
                
                # Simple compass direction
                compass = self._get_compass_direction(bearing)
                print(f"\033[1;35mDirection:\033[0m {compass}")
        else:
            print("\033[1;31mNo angle data available\033[0m")
        
        # Clear remaining lines
        print("\033[J", end="")
    
    def _draw_angle_bar(self, angle, min_val, max_val):
        """Draw a visual angle indicator bar"""
        bar_width = 30
        normalized = (angle - min_val) / (max_val - min_val)
        normalized = max(0, min(1, normalized))  # Clamp to 0-1
        
        pos = int(normalized * bar_width)
        
        bar = "["
        for i in range(bar_width):
            if i == pos:
                bar += "●"
            elif i == bar_width // 2:
                bar += "|"
            else:
                bar += "-"
        bar += "]"
        
        print(bar, end="")
    
    def _get_compass_direction(self, bearing):
        """Convert bearing to compass direction"""
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                     "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        index = int((bearing + 11.25) / 22.5) % 16
        return directions[index]
    
    def test_tracking_sequence(self):
        """Test sequence: Start tracking and monitor angles"""
        print("\033[1;33mTEST: Starting tracking at center...\033[0m")
        
        # Start tracking at center
        self.start_tracking_center()
        time.sleep(2)
        
        # Monitor angles
        self.monitor_tracking_angles()
    
    def start_tracking_center(self):
        """Start tracking at screen center"""
        try:
            # First enable tracking mode
            cmd = build_command(
                frame_header='#TP',
                address_bit1='P',
                address_bit2='D',
                control_bit='w',
                identifier_bit='TRC',
                data='02',  # Enter detection mode
                data_mode='ASCII',
                output_format='ASCII'
            )
            
            self.sock.sendto(cmd.encode('ascii'), (self.camera_ip, self.control_port))
            time.sleep(0.5)
            
            # Then send LOC command to track center
            vals = (0, 0, 100, 100, 8)  # Center position, 100x100 box, blur click enabled
            data_bytes = b''.join(struct.pack('>h', v) for v in vals)
            data_hex = ' '.join(f'{b:02X}' for b in data_bytes)
            
            cmd = build_command(
                frame_header='#tp',
                address_bit1='P',
                address_bit2='D',
                control_bit='w',
                identifier_bit='LOC',
                data=data_hex,
                data_mode='Hex',
                input_space_separate=True,
                output_format='Hex',
                output_space_separate=False
            )
            
            cmd_bytes = bytes.fromhex(cmd)
            self.sock.sendto(cmd_bytes, (self.camera_ip, self.control_port))
            
            print("✓ Sent tracking command for center position")
            return True
            
        except Exception as e:
            print(f"✗ Failed to start tracking: {e}")
            return False


def main():
    """Main entry point"""
    print("\033[1;36m" + "="*70 + "\033[0m")
    print("\033[1;33mGIMBAL TRACKING ANGLE MONITOR\033[0m")
    print("\033[1;36m" + "="*70 + "\033[0m")
    print("\nThis tool monitors gimbal angles relative to the robot body.")
    print("When tracking is active, these angles indicate the target position.")
    print("\nBased on support response: 'The tracking target is basically in")
    print("the center of the image, the angle of the camera is the angle")
    print("of the tracking target.'")
    
    monitor = TrackingAngleMonitor()
    
    print("\n\033[1;34mOptions:\033[0m")
    print("1. Monitor angles only (use with app tracking)")
    print("2. Start center tracking and monitor")
    print("3. Check GPS capability")
    print("4. Exit")
    
    choice = input("\n\033[1;34mSelect option (1-4):\033[0m ").strip()
    
    if choice == '1':
        print("\n\033[1;33mMonitoring angles...\033[0m")
        print("Start tracking from the native app to see target angles.")
        time.sleep(2)
        monitor.monitor_tracking_angles()
        
    elif choice == '2':
        monitor.test_tracking_sequence()
        
    elif choice == '3':
        print("\n\033[1;33mChecking GPS capability...\033[0m")
        print("Note: GPS commands exist in protocol (section 5.8)")
        print("but availability depends on hardware model.")
        # Could implement GPS check here
        
    elif choice == '4':
        print("\033[1;33mExiting...\033[0m")
    else:
        print("\033[1;31mInvalid choice\033[0m")


if __name__ == "__main__":
    main()