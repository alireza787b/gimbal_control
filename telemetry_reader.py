#!/usr/bin/env python3
"""
Alternative Telemetry Reader
============================
Reads telemetry directly via protocol commands instead of SEI.
This works without ffmpeg dependency.
"""

import socket
import threading
import time
import struct
from datetime import datetime
from gimbalcmdparse import build_command
from config import GIMBAL_CONFIG


class TelemetryReader:
    """Read telemetry data using gimbal protocol commands"""
    
    def __init__(self, camera_ip: str):
        self.camera_ip = camera_ip
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock.bind(('0.0.0.0', GIMBAL_CONFIG['listen_port']))
        self.recv_sock.settimeout(0.5)
        
        self.running = False
        self.telemetry = {
            "attitude": {"yaw": 0.0, "pitch": 0.0, "roll": 0.0},
            "zoom": 0,
            "focus": 0,
            "recording": False,
            "temperature": {"high": 0.0, "low": 0.0, "center": 0.0},
            "last_update": None,
            "update_rate": 0.0
        }
        
    def send_command(self, identifier: str, address2: str, control: str, data: str):
        """Send command and get response"""
        cmd = build_command(
            frame_header='#TP' if len(data) == 2 else '#tp',
            address_bit1='P',
            address_bit2=address2,
            control_bit=control,
            identifier_bit=identifier,
            data=data,
            output_format='ASCII'
        )
        
        self.sock.sendto(cmd.encode(), (self.camera_ip, GIMBAL_CONFIG['control_port']))
        
        try:
            response, _ = self.recv_sock.recvfrom(1024)
            return response.decode('ascii', errors='ignore')
        except socket.timeout:
            return None
    
    def update_attitude(self):
        """Update gimbal attitude"""
        response = self.send_command("GAC", "G", "r", "00")
        if response and 'GAC' in response:
            try:
                idx = response.find('GAC') + 3
                if idx + 12 <= len(response):
                    yaw = int(response[idx:idx+4], 16)
                    pitch = int(response[idx+4:idx+8], 16)
                    roll = int(response[idx+8:idx+12], 16)
                    
                    # Handle signed values
                    if yaw > 0x7FFF: yaw -= 0x10000
                    if pitch > 0x7FFF: pitch -= 0x10000
                    if roll > 0x7FFF: roll -= 0x10000
                    
                    self.telemetry["attitude"]["yaw"] = yaw / 100.0
                    self.telemetry["attitude"]["pitch"] = pitch / 100.0
                    self.telemetry["attitude"]["roll"] = roll / 100.0
            except:
                pass
    
    def update_zoom(self):
        """Update zoom position"""
        response = self.send_command("ZOM", "M", "r", "00")
        if response and 'ZOM' in response:
            try:
                idx = response.find('ZOM') + 3
                if idx + 4 <= len(response):
                    zoom = int(response[idx:idx+4], 16)
                    if zoom > 0x7FFF: zoom -= 0x10000
                    self.telemetry["zoom"] = zoom
            except:
                pass
    
    def update_focus(self):
        """Update focus position"""
        response = self.send_command("FOC", "M", "r", "00")
        if response and 'FOC' in response:
            try:
                idx = response.find('FOC') + 3
                if idx + 4 <= len(response):
                    focus = int(response[idx:idx+4], 16)
                    if focus > 0x7FFF: focus -= 0x10000
                    self.telemetry["focus"] = focus
            except:
                pass
    
    def update_recording_status(self):
        """Check recording status"""
        response = self.send_command("REC", "D", "r", "00")
        if response and 'REC' in response:
            try:
                idx = response.find('REC') + 3
                if idx + 2 <= len(response):
                    status = response[idx:idx+2]
                    self.telemetry["recording"] = (status == "01")
            except:
                pass
    
    def telemetry_loop(self):
        """Main telemetry update loop"""
        last_time = time.time()
        
        while self.running:
            start_time = time.time()
            
            # Update all telemetry
            self.update_attitude()
            self.update_zoom()
            self.update_focus()
            self.update_recording_status()
            
            # Calculate update rate
            current_time = time.time()
            self.telemetry["update_rate"] = 1.0 / (current_time - last_time)
            self.telemetry["last_update"] = datetime.now()
            last_time = current_time
            
            # Sleep to maintain ~10Hz update rate
            elapsed = time.time() - start_time
            if elapsed < 0.1:
                time.sleep(0.1 - elapsed)
    
    def start(self):
        """Start telemetry reader"""
        self.running = True
        self.thread = threading.Thread(target=self.telemetry_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop telemetry reader"""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=1.0)
        self.sock.close()
        self.recv_sock.close()
    
    def get_telemetry(self):
        """Get current telemetry data"""
        return self.telemetry.copy()


def display_telemetry(reader):
    """Display telemetry in terminal"""
    import os
    
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        
        telemetry = reader.get_telemetry()
        
        print("="*60)
        print("GIMBAL TELEMETRY READER (Protocol-based)")
        print("="*60)
        
        if telemetry["last_update"]:
            print(f"Last Update: {telemetry['last_update'].strftime('%H:%M:%S.%f')[:-3]}")
            print(f"Update Rate: {telemetry['update_rate']:.1f} Hz")
        else:
            print("Waiting for telemetry...")
        
        print("\nGIMBAL ATTITUDE")
        print("-" * 40)
        att = telemetry["attitude"]
        print(f"Yaw:   {att['yaw']:7.2f}°")
        print(f"Pitch: {att['pitch']:7.2f}°")
        print(f"Roll:  {att['roll']:7.2f}°")
        
        print("\nCAMERA STATUS")
        print("-" * 40)
        print(f"Zoom Position:  {telemetry['zoom']}")
        print(f"Focus Position: {telemetry['focus']}")
        print(f"Recording:      {'Yes' if telemetry['recording'] else 'No'}")
        
        print("\nPress Ctrl+C to exit")
        
        time.sleep(0.1)


def main():
    """Main function"""
    print("Starting telemetry reader...")
    print("This reads telemetry using protocol commands (no ffmpeg required)")
    print("-" * 60)
    
    reader = TelemetryReader(GIMBAL_CONFIG['camera_ip'])
    reader.start()
    
    try:
        display_telemetry(reader)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        reader.stop()
        print("Telemetry reader stopped.")


if __name__ == "__main__":
    main()