#!/usr/bin/env python3
"""
Real-time Gimbal Status Monitor
================================
Continuously monitor gimbal telemetry and status.
"""

import socket
import threading
import time
import os
import sys
from datetime import datetime
from gimbalcmdparse import build_command
from config import GIMBAL_CONFIG


class GimbalMonitor:
    """Real-time gimbal status monitor"""
    
    def __init__(self, camera_ip: str):
        self.camera_ip = camera_ip
        self.running = False
        self.sock = None
        self.recv_sock = None
        
        # Current status
        self.status = {
            "connected": False,
            "last_update": None,
            "attitude": {"magnetic": None, "gyroscope": None},
            "zoom": 0,
            "recording": False,
            "response_time": 0.0,
            "errors": 0,
            "commands_sent": 0
        }
        
    def connect(self):
        """Initialize connection"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.recv_sock.bind(('0.0.0.0', GIMBAL_CONFIG['listen_port']))
            self.recv_sock.settimeout(0.1)
            self.status["connected"] = True
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
            
    def query_attitude(self):
        """Query gimbal attitude - both magnetic and gyroscope"""
        # Get magnetic attitude (GAC)
        cmd = build_command(
            frame_header='#TP',
            address_bit1='P',
            address_bit2='G',
            control_bit='r',
            identifier_bit='GAC',
            data='00',
            output_format='ASCII'
        )
        
        start_time = time.time()
        self.sock.sendto(cmd.encode(), (self.camera_ip, GIMBAL_CONFIG['control_port']))
        self.status["commands_sent"] += 1
        
        try:
            data, _ = self.recv_sock.recvfrom(1024)
            response_time = time.time() - start_time
            self.status["response_time"] = response_time * 1000  # Convert to ms
            
            # Parse magnetic attitude
            if b'GAC' in data and len(data) > 20:
                resp_str = data.decode('ascii', errors='ignore')
                idx = resp_str.find('GAC') + 3
                attitude_data = resp_str[idx:idx+12]
                
                yaw = int(attitude_data[0:4], 16)
                pitch = int(attitude_data[4:8], 16)
                roll = int(attitude_data[8:12], 16)
                
                # Handle signed values
                if yaw > 0x7FFF: yaw -= 0x10000
                if pitch > 0x7FFF: pitch -= 0x10000
                if roll > 0x7FFF: roll -= 0x10000
                
                self.status["attitude"]["magnetic"] = {
                    "yaw": yaw / 100.0,
                    "pitch": pitch / 100.0,
                    "roll": roll / 100.0
                }
                self.status["last_update"] = datetime.now()
                
        except socket.timeout:
            self.status["errors"] += 1
        
        # Get gyroscope attitude (GIC)
        cmd = build_command(
            frame_header='#TP',
            address_bit1='P',
            address_bit2='G',
            control_bit='r',
            identifier_bit='GIC',
            data='00',
            output_format='ASCII'
        )
        
        self.sock.sendto(cmd.encode(), (self.camera_ip, GIMBAL_CONFIG['control_port']))
        
        try:
            data, _ = self.recv_sock.recvfrom(1024)
            
            # Parse gyroscope attitude
            if b'GIC' in data and len(data) > 20:
                resp_str = data.decode('ascii', errors='ignore')
                idx = resp_str.find('GIC') + 3
                attitude_data = resp_str[idx:idx+12]
                
                yaw = int(attitude_data[0:4], 16)
                pitch = int(attitude_data[4:8], 16)
                roll = int(attitude_data[8:12], 16)
                
                # Handle signed values
                if yaw > 0x7FFF: yaw -= 0x10000
                if pitch > 0x7FFF: pitch -= 0x10000
                if roll > 0x7FFF: roll -= 0x10000
                
                self.status["attitude"]["gyroscope"] = {
                    "yaw": yaw / 100.0,
                    "pitch": pitch / 100.0,
                    "roll": roll / 100.0
                }
                
        except socket.timeout:
            pass
            
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def display_status(self):
        """Display current status"""
        self.clear_screen()
        
        print("╔════════════════════════════════════════════════════════╗")
        print("║           GIMBAL REAL-TIME STATUS MONITOR              ║")
        print("╚════════════════════════════════════════════════════════╝")
        print()
        
        # Connection status
        conn_status = "✅ CONNECTED" if self.status["connected"] else "❌ DISCONNECTED"
        print(f"Connection: {conn_status} to {self.camera_ip}")
        
        if self.status["last_update"]:
            print(f"Last Update: {self.status['last_update'].strftime('%H:%M:%S.%f')[:-3]}")
        
        print()
        print("═" * 58)
        print("GIMBAL ATTITUDE")
        print("═" * 58)
        
        # Magnetic attitude display
        if self.status["attitude"]["magnetic"]:
            att = self.status["attitude"]["magnetic"]
            print("MAGNETIC (Fixed to mount):")
            
            # Yaw indicator
            yaw_bar = self.create_angle_bar(att["yaw"], -150, 150)
            print(f"Yaw:   {att['yaw']:7.2f}° {yaw_bar}")
            
            # Pitch indicator
            pitch_bar = self.create_angle_bar(att["pitch"], -90, 90)
            print(f"Pitch: {att['pitch']:7.2f}° {pitch_bar}")
            
            # Roll indicator
            roll_bar = self.create_angle_bar(att["roll"], -90, 90)
            print(f"Roll:  {att['roll']:7.2f}° {roll_bar}")
        
        print()
        
        # Gyroscope attitude display
        if self.status["attitude"]["gyroscope"]:
            att = self.status["attitude"]["gyroscope"]
            print("GYROSCOPE (Absolute spatial):")
            
            # Yaw indicator
            yaw_bar = self.create_angle_bar(att["yaw"], -150, 150)
            print(f"Yaw:   {att['yaw']:7.2f}° {yaw_bar}")
            
            # Pitch indicator
            pitch_bar = self.create_angle_bar(att["pitch"], -90, 90)
            print(f"Pitch: {att['pitch']:7.2f}° {pitch_bar}")
            
            # Roll indicator
            roll_bar = self.create_angle_bar(att["roll"], -90, 90)
            print(f"Roll:  {att['roll']:7.2f}° {roll_bar}")
        
        # Show difference if both available
        if self.status["attitude"]["magnetic"] and self.status["attitude"]["gyroscope"]:
            mag = self.status["attitude"]["magnetic"]
            gyro = self.status["attitude"]["gyroscope"]
            print()
            print("DIFFERENCE (Gyro - Magnetic):")
            print(f"Yaw:   {gyro['yaw'] - mag['yaw']:7.2f}°")
            print(f"Pitch: {gyro['pitch'] - mag['pitch']:7.2f}°")
            print(f"Roll:  {gyro['roll'] - mag['roll']:7.2f}°")
        
        print()
        print("═" * 58)
        print("COMMUNICATION STATISTICS")
        print("═" * 58)
        print(f"Response Time: {self.status['response_time']:.1f} ms")
        print(f"Commands Sent: {self.status['commands_sent']}")
        print(f"Errors: {self.status['errors']}")
        
        if self.status['commands_sent'] > 0:
            success_rate = (1 - self.status['errors'] / self.status['commands_sent']) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        print()
        print("Press Ctrl+C to exit")
        
    def create_angle_bar(self, angle: float, min_angle: float, max_angle: float, width: int = 30):
        """Create visual angle indicator bar"""
        # Normalize angle to 0-1 range
        normalized = (angle - min_angle) / (max_angle - min_angle)
        normalized = max(0, min(1, normalized))
        
        # Calculate position
        pos = int(normalized * width)
        
        # Create bar
        bar = ['─'] * width
        bar[width // 2] = '┼'  # Center mark
        bar[pos] = '●'  # Current position
        
        return '[' + ''.join(bar) + ']'
        
    def monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self.query_attitude()
                self.display_status()
                time.sleep(0.1)  # 10Hz update rate
            except Exception as e:
                print(f"\nMonitor error: {e}")
                time.sleep(1)
                
    def start(self):
        """Start monitoring"""
        if not self.connect():
            return False
            
        self.running = True
        monitor_thread = threading.Thread(target=self.monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        return True
        
    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.sock:
            self.sock.close()
        if self.recv_sock:
            self.recv_sock.close()


def run_monitor():
    """Run the gimbal monitor"""
    monitor = GimbalMonitor(GIMBAL_CONFIG['camera_ip'])
    
    print("Starting gimbal monitor...")
    if not monitor.start():
        print("Failed to start monitor")
        return
        
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down monitor...")
        monitor.stop()
        print("Monitor stopped.")


def test_commands():
    """Test various gimbal commands"""
    print("\n=== GIMBAL COMMAND TEST MODE ===")
    print("Testing various commands...")
    print("-" * 30)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.bind(('0.0.0.0', GIMBAL_CONFIG['listen_port']))
    recv_sock.settimeout(1.0)
    
    commands = [
        ("Get Attitude", "G", "r", "GAC", "00"),
        ("Get Zoom Position", "M", "r", "ZOM", "00"),
        ("Get Focus Position", "M", "r", "FOC", "00"),
    ]
    
    for desc, addr, ctrl, ident, data in commands:
        print(f"\nTesting: {desc}")
        
        cmd = build_command(
            frame_header='#TP',
            address_bit1='P',
            address_bit2=addr,
            control_bit=ctrl,
            identifier_bit=ident,
            data=data,
            output_format='ASCII'
        )
        
        print(f"  Sending: {cmd}")
        sock.sendto(cmd.encode(), (GIMBAL_CONFIG['camera_ip'], GIMBAL_CONFIG['control_port']))
        
        try:
            response, _ = recv_sock.recvfrom(1024)
            print(f"  Response: {response.decode('ascii', errors='ignore')}")
            print("  ✓ Success")
        except socket.timeout:
            print("  ✗ Timeout")
            
    sock.close()
    recv_sock.close()
    print("\n" + "="*30 + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        test_commands()
    else:
        run_monitor()