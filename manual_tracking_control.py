#!/usr/bin/env python3
"""
Professional Gimbal Tracking Control System
==========================================
Real-time object tracking with attitude monitoring.
"""

import socket
import time
import struct
import threading
import queue
from datetime import datetime
from gimbalcmdparse import build_command
from config import GIMBAL_CONFIG
import sys
import os
import traceback


class RealTimeTrackingControl:
    def __init__(self):
        self.camera_ip = GIMBAL_CONFIG['camera_ip']
        self.control_port = GIMBAL_CONFIG['control_port']
        self.listen_port = GIMBAL_CONFIG['listen_port']
        
        # Communication sockets
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock.bind(('0.0.0.0', self.listen_port))
        self.recv_sock.settimeout(0.1)  # Short timeout for responsive monitoring
        
        # Tracking state
        self.tracking_active = False
        self.tracking_params = None
        self.last_attitudes = {'magnetic': None, 'gyroscope': None}
        
        # Threading for real-time monitoring
        self.monitor_queue = queue.Queue()
        self.monitor_thread = None
        self.monitoring = False
        
    def start_tracking(self, x: int, y: int, width: int = 100, height: int = 100,
                      preview_width: int = 1920, preview_height: int = 1080):
        """
        Start tracking at specified coordinates using LOC command.
        
        Args:
            x: X coordinate in preview (0-1920)
            y: Y coordinate in preview (0-1080)
            width: Tracking box width in pixels
            height: Tracking box height in pixels
            preview_width: Preview resolution width (default 1920)
            preview_height: Preview resolution height (default 1080)
        """
        try:
            # Validate input coordinates
            if not (0 <= x <= preview_width and 0 <= y <= preview_height):
                raise ValueError(f"Coordinates ({x},{y}) out of range")
            
            # Ensure non-zero preview dimensions
            if preview_width <= 0 or preview_height <= 0:
                raise ValueError(f"Invalid preview dimensions: {preview_width}x{preview_height}")
            
            # Calculate protocol values according to LOC_cmd.py formula
            param_x = round(2000 * x / float(preview_width) - 1000)
            param_y = round(2000 * y / float(preview_height) - 1000)
            param_w = round(2000 * width / float(preview_width))
            param_h = round(2000 * height / float(preview_height))
            blur_click = 8  # Enable blur click for better tracking
            
            # Store tracking parameters
            self.tracking_params = {
                'screen_x': x,
                'screen_y': y,
                'screen_width': width,
                'screen_height': height,
                'param_x': param_x,
                'param_y': param_y,
                'param_w': param_w,
                'param_h': param_h,
                'timestamp': datetime.now()
            }
            
            # Pack values as big-endian signed 16-bit integers
            vals = (param_x, param_y, param_w, param_h, blur_click)
            data_bytes = b''.join(struct.pack('>h', v) for v in vals)
            data_hex = ' '.join(f'{b:02X}' for b in data_bytes)
            
            # Build LOC command using the proven build_command function
            cmd = build_command(
                frame_header='#tp',
                address_bit1='P',      # Network source
                address_bit2='D',      # System/Image destination
                control_bit='w',       # Write command
                identifier_bit='LOC',  # Location/tracking command
                data=data_hex,
                data_mode='Hex',
                input_space_separate=True,
                output_format='Hex',
                output_space_separate=False
            )
            
            # Send command
            cmd_bytes = bytes.fromhex(cmd)
            self.sock.sendto(cmd_bytes, (self.camera_ip, self.control_port))
            
            self.tracking_active = True
            self.monitor_queue.put(('TRACK_START', self.tracking_params))
            
            print(f"\n\033[1;32m✓ Tracking command sent successfully\033[0m")
            print(f"  Position: ({x}, {y})")
            print(f"  Size: {width} × {height}")
            print(f"  Command: {cmd}")
            
            return True
            
        except Exception as e:
            print(f"\n\033[1;31m✗ Error starting tracking: {e}\033[0m")
            traceback.print_exc()
            return False
    
    def stop_tracking(self):
        """Stop tracking by sending zero-size LOC command"""
        try:
            # Send LOC with all zeros to stop
            vals = (0, 0, 0, 0, 0)
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
            
            self.tracking_active = False
            self.tracking_params = None
            self.monitor_queue.put(('TRACK_STOP', None))
            
        except Exception as e:
            print(f"\n\033[1;31m✗ Error stopping tracking: {e}\033[0m")
    
    def get_attitudes(self):
        """Get both magnetic and gyroscope attitudes efficiently"""
        attitudes = {}
        
        try:
            # Get magnetic attitude (GAC)
            cmd_gac = build_command(
                frame_header='#TP',
                address_bit1='P',
                address_bit2='G',
                control_bit='r',
                identifier_bit='GAC',
                data='00',
                data_mode='ASCII',
                output_format='ASCII'
            )
            
            self.sock.sendto(cmd_gac.encode('ascii'), (self.camera_ip, self.control_port))
            
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
                        
                        # Convert to signed values
                        if yaw > 0x7FFF: yaw -= 0x10000
                        if pitch > 0x7FFF: pitch -= 0x10000
                        if roll > 0x7FFF: roll -= 0x10000
                        
                        attitudes['magnetic'] = {
                            'yaw': yaw / 100.0,
                            'pitch': pitch / 100.0,
                            'roll': roll / 100.0,
                            'timestamp': time.time()
                        }
            except socket.timeout:
                pass
            
            # Get gyroscope attitude (GIC)
            cmd_gic = build_command(
                frame_header='#TP',
                address_bit1='P',
                address_bit2='G',
                control_bit='r',
                identifier_bit='GIC',
                data='00',
                data_mode='ASCII',
                output_format='ASCII'
            )
            
            self.sock.sendto(cmd_gic.encode('ascii'), (self.camera_ip, self.control_port))
            
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
                        
                        # Convert to signed values
                        if yaw > 0x7FFF: yaw -= 0x10000
                        if pitch > 0x7FFF: pitch -= 0x10000
                        if roll > 0x7FFF: roll -= 0x10000
                        
                        attitudes['gyroscope'] = {
                            'yaw': yaw / 100.0,
                            'pitch': pitch / 100.0,
                            'roll': roll / 100.0,
                            'timestamp': time.time()
                        }
            except socket.timeout:
                pass
                
        except Exception as e:
            self.monitor_queue.put(('ERROR', f"Attitude read error: {str(e)}"))
        
        return attitudes
    
    def monitor_worker(self):
        """Background thread for continuous attitude monitoring"""
        while self.monitoring:
            try:
                attitudes = self.get_attitudes()
                
                # Update last known attitudes
                if 'magnetic' in attitudes:
                    self.last_attitudes['magnetic'] = attitudes['magnetic']
                if 'gyroscope' in attitudes:
                    self.last_attitudes['gyroscope'] = attitudes['gyroscope']
                
                # Queue update for display
                self.monitor_queue.put(('ATTITUDE_UPDATE', attitudes))
                
                time.sleep(0.05)  # 20Hz update rate
                
            except Exception as e:
                self.monitor_queue.put(('ERROR', str(e)))
                time.sleep(0.1)  # Slow down on errors
    
    def start_monitoring(self):
        """Start real-time monitoring thread"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self.monitor_worker, daemon=True)
            self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring thread"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
    
    def display_realtime_status(self, duration=30):
        """Display real-time tracking and attitude information"""
        self.start_monitoring()
        
        # Clear screen and hide cursor
        os.system('clear' if os.name != 'nt' else 'cls')
        print('\033[?25l', end='')  # Hide cursor
        
        start_time = time.time()
        update_count = 0
        last_display_time = 0
        display_interval = 0.1  # 10Hz display update
        
        try:
            while time.time() - start_time < duration:
                current_time = time.time()
                
                # Process monitor queue
                while not self.monitor_queue.empty():
                    try:
                        msg_type, data = self.monitor_queue.get_nowait()
                        
                        if msg_type == 'ERROR':
                            # Don't break the display, just note the error
                            pass
                            
                    except queue.Empty:
                        break
                
                # Update display at specified interval
                if current_time - last_display_time >= display_interval:
                    last_display_time = current_time
                    update_count += 1
                    elapsed = current_time - start_time
                    
                    # Move cursor to home position
                    print('\033[H', end='')
                    
                    # Header
                    print(f"\033[1;36m{'='*80}\033[0m")
                    print(f"\033[1;33mREAL-TIME GIMBAL TRACKING MONITOR\033[0m")
                    print(f"\033[1;36m{'='*80}\033[0m")
                    
                    # Calculate update rate safely
                    update_rate = update_count / elapsed if elapsed > 0 else 0
                    print(f"Elapsed: \033[1;32m{elapsed:.1f}s\033[0m | Updates: \033[1;32m{update_count}\033[0m | "
                          f"Rate: \033[1;32m{update_rate:.1f} Hz\033[0m")
                    print()
                    
                    # Tracking Box Information
                    print(f"\033[1;34m📍 TRACKING BOX STATUS\033[0m")
                    print("-" * 40)
                    
                    if self.tracking_active and self.tracking_params:
                        params = self.tracking_params
                        print(f"Status: \033[1;32m● ACTIVE\033[0m")
                        print(f"Position: ({params['screen_x']}, {params['screen_y']}) pixels")
                        print(f"Size: {params['screen_width']} × {params['screen_height']} pixels")
                        print(f"Protocol Values: X={params['param_x']}, Y={params['param_y']}, "
                              f"W={params['param_w']}, H={params['param_h']}")
                        
                        # Visual representation of tracking box position
                        # Create a simple ASCII visualization (20x10 grid)
                        grid_w, grid_h = 40, 10
                        box_x = int(params['screen_x'] * grid_w / 1920)
                        box_y = int(params['screen_y'] * grid_h / 1080)
                        
                        print("\nTracking Position Visualization:")
                        for y in range(grid_h):
                            line = ""
                            for x in range(grid_w):
                                if x == box_x and y == box_y:
                                    line += "\033[1;31m◉\033[0m"  # Red marker
                                elif x == 0 or x == grid_w-1 or y == 0 or y == grid_h-1:
                                    line += "█"  # Border
                                else:
                                    line += "·"
                            print(line)
                    else:
                        print(f"Status: \033[1;31m○ INACTIVE\033[0m")
                        print("Position: N/A")
                        print("Size: N/A")
                    
                    print()
                    
                    # Gimbal Attitude Information
                    print(f"\033[1;34m🎯 GIMBAL ATTITUDE DATA\033[0m")
                    print("-" * 40)
                    
                    # Magnetic Attitude (relative to mount)
                    if self.last_attitudes['magnetic']:
                        mag = self.last_attitudes['magnetic']
                        age = current_time - mag['timestamp']
                        print(f"\033[1;35mMAGNETIC (Mount-relative):\033[0m")
                        print(f"  Yaw:   \033[1;37m{mag['yaw']:8.2f}°\033[0m  ▸")
                        print(f"  Pitch: \033[1;37m{mag['pitch']:8.2f}°\033[0m  ▸")
                        print(f"  Roll:  \033[1;37m{mag['roll']:8.2f}°\033[0m  ▸")
                        print(f"  Age:   {age:.3f}s")
                    else:
                        print("\033[1;35mMAGNETIC:\033[0m \033[1;31mNo data\033[0m")
                    
                    print()
                    
                    # Gyroscope Attitude (absolute spatial)
                    if self.last_attitudes['gyroscope']:
                        gyro = self.last_attitudes['gyroscope']
                        age = current_time - gyro['timestamp']
                        print(f"\033[1;35mGYROSCOPE (Absolute spatial):\033[0m")
                        print(f"  Yaw:   \033[1;37m{gyro['yaw']:8.2f}°\033[0m  ▸")
                        print(f"  Pitch: \033[1;37m{gyro['pitch']:8.2f}°\033[0m  ▸")
                        print(f"  Roll:  \033[1;37m{gyro['roll']:8.2f}°\033[0m  ▸")
                        print(f"  Age:   {age:.3f}s")
                    else:
                        print("\033[1;35mGYROSCOPE:\033[0m \033[1;31mNo data\033[0m")
                    
                    print()
                    
                    # Difference calculation
                    if self.last_attitudes['magnetic'] and self.last_attitudes['gyroscope']:
                        mag = self.last_attitudes['magnetic']
                        gyro = self.last_attitudes['gyroscope']
                        print(f"\033[1;35mDIFFERENCE (Gyro - Magnetic):\033[0m")
                        print(f"  ΔYaw:   \033[1;33m{gyro['yaw'] - mag['yaw']:8.2f}°\033[0m")
                        print(f"  ΔPitch: \033[1;33m{gyro['pitch'] - mag['pitch']:8.2f}°\033[0m")
                        print(f"  ΔRoll:  \033[1;33m{gyro['roll'] - mag['roll']:8.2f}°\033[0m")
                    
                    # Clear remaining lines
                    print("\033[J", end='')
                    
                time.sleep(0.01)  # Small sleep to prevent CPU hogging
                
        except KeyboardInterrupt:
            print("\n\n\033[1;33mMonitoring interrupted by user\033[0m")
        except Exception as e:
            print(f"\n\n\033[1;31mError during monitoring: {e}\033[0m")
            traceback.print_exc()
        finally:
            # Show cursor again
            print('\033[?25h', end='')
            self.stop_monitoring()
    
    def interactive_tracking(self):
        """Enhanced interactive tracking mode"""
        print("\033[1;36m" + "="*60 + "\033[0m")
        print("\033[1;33mINTERACTIVE TRACKING CONTROL\033[0m")
        print("\033[1;36m" + "="*60 + "\033[0m")
        print("Commands:")
        print("  \033[1;32mx,y\033[0m         Track at coordinates (e.g., 960,540)")
        print("  \033[1;32mx,y,w,h\033[0m     Track with custom size (e.g., 960,540,200,200)")
        print("  \033[1;32mstop\033[0m        Stop tracking")
        print("  \033[1;32mcenter\033[0m      Track center of screen")
        print("  \033[1;32mstatus\033[0m      Show current status")
        print("  \033[1;32mmonitor\033[0m     Start real-time monitoring")
        print("  \033[1;32mquit\033[0m        Exit")
        print("-" * 60)
        
        while True:
            try:
                user_input = input("\n\033[1;34mTrack>\033[0m ").strip().lower()
                
                if user_input == 'quit':
                    if self.tracking_active:
                        self.stop_tracking()
                    break
                    
                elif user_input == 'stop':
                    self.stop_tracking()
                    print("\033[1;32m✓ Tracking stopped\033[0m")
                    
                elif user_input == 'center':
                    if self.start_tracking(960, 540, 150, 150):
                        self.display_realtime_status(15)
                    
                elif user_input == 'monitor':
                    if self.tracking_active:
                        self.display_realtime_status(30)
                    else:
                        print("\033[1;31m✗ No active tracking. Start tracking first.\033[0m")
                        
                elif user_input == 'status':
                    attitudes = self.get_attitudes()
                    print("\n\033[1;34mCurrent Status:\033[0m")
                    if 'magnetic' in attitudes:
                        mag = attitudes['magnetic']
                        print(f"Magnetic: Y:{mag['yaw']:.1f}° P:{mag['pitch']:.1f}° R:{mag['roll']:.1f}°")
                    if 'gyroscope' in attitudes:
                        gyro = attitudes['gyroscope']
                        print(f"Gyroscope: Y:{gyro['yaw']:.1f}° P:{gyro['pitch']:.1f}° R:{gyro['roll']:.1f}°")
                    if self.tracking_active and self.tracking_params:
                        print(f"Tracking: ({self.tracking_params['screen_x']}, "
                              f"{self.tracking_params['screen_y']})")
                    else:
                        print("Tracking: Inactive")
                        
                else:
                    # Parse coordinates
                    parts = user_input.split(',')
                    if len(parts) >= 2:
                        try:
                            x = int(parts[0])
                            y = int(parts[1])
                            w = int(parts[2]) if len(parts) > 2 else 100
                            h = int(parts[3]) if len(parts) > 3 else 100
                            
                            if 0 <= x <= 1920 and 0 <= y <= 1080:
                                if self.start_tracking(x, y, w, h):
                                    self.display_realtime_status(15)
                            else:
                                print("\033[1;31m✗ Coordinates out of range (0-1920, 0-1080)\033[0m")
                        except ValueError:
                            print("\033[1;31m✗ Invalid format. Use: x,y or x,y,w,h\033[0m")
                    else:
                        print("\033[1;31m✗ Unknown command\033[0m")
                        
            except KeyboardInterrupt:
                print("\n\n\033[1;33mExiting interactive mode...\033[0m")
                break
            except Exception as e:
                print(f"\033[1;31m✗ Error: {e}\033[0m")
                traceback.print_exc()
        
        # Cleanup
        if self.tracking_active:
            self.stop_tracking()
        self.stop_monitoring()


def main():
    """Main entry point with enhanced menu"""
    print("\033[1;36m" + "="*60 + "\033[0m")
    print("\033[1;33mPROFESSIONAL GIMBAL TRACKING CONTROL\033[0m")
    print("\033[1;36m" + "="*60 + "\033[0m")
    print("Real-time object tracking with attitude monitoring")
    print()
    
    controller = RealTimeTrackingControl()
    
    print("Options:")
    print("  \033[1;32m1.\033[0m Quick center tracking demo")
    print("  \033[1;32m2.\033[0m Interactive tracking mode")
    print("  \033[1;32m3.\033[0m Custom coordinate test")
    print("  \033[1;32m4.\033[0m Exit")
    
    choice = input("\n\033[1;34mSelect option (1-4):\033[0m ").strip()
    
    try:
        if choice == '1':
            # Quick demo
            print("\n\033[1;33mStarting center tracking demo...\033[0m")
            if controller.start_tracking(960, 540, 150, 150):
                controller.display_realtime_status(20)
                controller.stop_tracking()
            
        elif choice == '2':
            # Interactive mode
            controller.interactive_tracking()
            
        elif choice == '3':
            # Custom test
            print("\n\033[1;34mEnter tracking parameters:\033[0m")
            try:
                x = int(input("X coordinate (0-1920): "))
                y = int(input("Y coordinate (0-1080): "))
                w = int(input("Width (default 100): ") or "100")
                h = int(input("Height (default 100): ") or "100")
                duration = int(input("Monitor duration in seconds (default 20): ") or "20")
                
                if controller.start_tracking(x, y, w, h):
                    controller.display_realtime_status(duration)
                    controller.stop_tracking()
            except ValueError:
                print("\033[1;31m✗ Invalid input\033[0m")
            
        elif choice == '4':
            print("\033[1;33mExiting...\033[0m")
        else:
            print("\033[1;31mInvalid choice\033[0m")
            
    except KeyboardInterrupt:
        print("\n\n\033[1;33mProgram interrupted\033[0m")
    except Exception as e:
        print(f"\n\033[1;31mError: {e}\033[0m")
        traceback.print_exc()
    finally:
        # Cleanup
        controller.stop_monitoring()
        print("\n\033[1;36m" + "="*60 + "\033[0m")
        print("\033[1;33mGimbal tracking control terminated\033[0m")
        print("\033[1;36m" + "="*60 + "\033[0m")


if __name__ == "__main__":
    main()