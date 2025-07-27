#!/usr/bin/env python3
"""
Gimbal Full Motion Test
=======================
Test complete range of motion for all axes and zoom.
Based strictly on protocol documentation.
"""

import socket
import time
import struct
from datetime import datetime
from config import GIMBAL_CONFIG


class MotionTester:
    def __init__(self):
        self.camera_ip = GIMBAL_CONFIG['camera_ip']
        self.control_port = GIMBAL_CONFIG['control_port']
        self.listen_port = GIMBAL_CONFIG['listen_port']
        
        # Create sockets
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock.bind(('0.0.0.0', self.listen_port))
        self.recv_sock.settimeout(0.5)
        
        # Motion limits from protocol (section 4.3.1)
        self.limits = {
            'yaw': {'min': -150.0, 'max': 150.0},
            'pitch': {'min': -90.0, 'max': 90.0},
            'roll': {'min': -90.0, 'max': 90.0}
        }
        
        # Log file
        self.log_file = open(f"motion_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", 'w')
        
    def log(self, message):
        """Log to console and file"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        self.log_file.write(log_line + '\n')
        self.log_file.flush()
        
    def send_command(self, cmd_bytes, description=""):
        """Send command and log"""
        self.log(f"CMD: {description} -> {cmd_bytes.hex()} ({cmd_bytes.decode('ascii', errors='replace')})")
        self.sock.sendto(cmd_bytes, (self.camera_ip, self.control_port))
        
    def get_attitude(self):
        """Get current gimbal attitude (GAC command from protocol)"""
        cmd = b"#TPPG2rGAC002D"
        self.sock.sendto(cmd, (self.camera_ip, self.control_port))
        
        try:
            data, _ = self.recv_sock.recvfrom(1024)
            resp_str = data.decode('ascii', errors='replace')
            
            if 'GAC' in resp_str:
                idx = resp_str.find('GAC') + 3
                if idx + 12 <= len(resp_str):
                    # Parse according to protocol format
                    yaw_hex = resp_str[idx:idx+4]
                    pitch_hex = resp_str[idx+4:idx+8]
                    roll_hex = resp_str[idx+8:idx+12]
                    
                    # Convert to signed int (protocol: 0.01 degree units)
                    yaw = int(yaw_hex, 16)
                    pitch = int(pitch_hex, 16)
                    roll = int(roll_hex, 16)
                    
                    if yaw > 0x7FFF: yaw -= 0x10000
                    if pitch > 0x7FFF: pitch -= 0x10000
                    if roll > 0x7FFF: roll -= 0x10000
                    
                    return {
                        'yaw': yaw / 100.0,
                        'pitch': pitch / 100.0,
                        'roll': roll / 100.0,
                        'raw': resp_str
                    }
        except socket.timeout:
            pass
        return None
    
    def get_zoom_position(self):
        """Get zoom position (ZOM command from protocol 3.1.2)"""
        cmd = b"#TPUM2rZOM0063"
        self.sock.sendto(cmd, (self.camera_ip, self.control_port))
        
        try:
            data, _ = self.recv_sock.recvfrom(1024)
            resp_str = data.decode('ascii', errors='replace')
            
            if 'ZOM' in resp_str:
                idx = resp_str.find('ZOM') + 3
                if idx + 4 <= len(resp_str):
                    zoom_hex = resp_str[idx:idx+4]
                    zoom = int(zoom_hex, 16)
                    if zoom > 0x7FFF: zoom -= 0x10000
                    return zoom
        except socket.timeout:
            pass
        return None
        
    def get_focus_position(self):
        """Get focus position (FOC command from protocol 3.2.2)"""
        cmd = b"#TPUM2rFOC0045"
        self.sock.sendto(cmd, (self.camera_ip, self.control_port))
        
        try:
            data, _ = self.recv_sock.recvfrom(1024)
            resp_str = data.decode('ascii', errors='replace')
            
            if 'FOC' in resp_str:
                idx = resp_str.find('FOC') + 3
                if idx + 4 <= len(resp_str):
                    focus_hex = resp_str[idx:idx+4]
                    focus = int(focus_hex, 16)
                    if focus > 0x7FFF: focus -= 0x10000
                    return focus
        except socket.timeout:
            pass
        return None
    
    def test_speed_mode(self):
        """Test gimbal speed mode control (protocol 4.2)"""
        self.log("\n" + "="*60)
        self.log("SPEED MODE TEST (Protocol Section 4.2)")
        self.log("="*60)
        
        # Test different speeds for each axis
        speed_tests = [
            ("Slow", 5.0),    # 5 deg/s
            ("Medium", 20.0), # 20 deg/s
            ("Fast", 50.0),   # 50 deg/s
            ("Max", 99.0)     # 99 deg/s (max per protocol)
        ]
        
        for speed_name, speed_val in speed_tests:
            self.log(f"\nTesting {speed_name} speed: {speed_val}°/s")
            
            # Test Yaw (GSY command)
            speed_int = int(speed_val * 10)  # Convert to 0.1deg/s units
            speed_bytes = struct.pack('>h', speed_int)  # Big-endian signed
            speed_hex = speed_bytes.hex().upper()
            
            # Build GSY command manually
            cmd = f"#TPUG2wGSY{speed_hex}"
            crc = sum(cmd.encode('ascii')) & 0xFF
            cmd += f"{crc:02X}"
            
            self.send_command(cmd.encode('ascii'), f"Set yaw speed to {speed_val}°/s")
            time.sleep(2.0)
            
            # Stop
            self.send_command(b"#TPUG2wPTZ006A", "STOP")
            time.sleep(0.5)
            
            # Get and log position
            attitude = self.get_attitude()
            if attitude:
                self.log(f"  Position after yaw test: Y={attitude['yaw']:.2f}° P={attitude['pitch']:.2f}° R={attitude['roll']:.2f}°")
    
    def test_angle_mode(self):
        """Test gimbal angle mode control (protocol 4.3)"""
        self.log("\n" + "="*60)
        self.log("ANGLE MODE TEST (Protocol Section 4.3)")
        self.log("="*60)
        
        # Test positions for each axis
        test_angles = [
            ("Center", 0.0),
            ("Quarter positive", 45.0),
            ("Quarter negative", -45.0),
            ("Half positive", 75.0),
            ("Half negative", -75.0)
        ]
        
        for angle_name, angle_val in test_angles:
            self.log(f"\nTesting angle: {angle_name} ({angle_val}°)")
            
            # Get initial position
            initial = self.get_attitude()
            if initial:
                self.log(f"  Initial: Y={initial['yaw']:.2f}° P={initial['pitch']:.2f}°")
            
            # Move to angle using GAY command (Gimbal Angle Yaw)
            angle_int = int(angle_val * 100)  # Convert to 0.01 degree units
            angle_bytes = struct.pack('>h', angle_int).hex().upper().zfill(4)
            speed_bytes = "1E"  # 30 (0.1deg/s) = 3 deg/s
            
            # Build command: #tpUG6wGAY<angle><speed>
            cmd_data = angle_bytes + speed_bytes
            cmd = f"#tpUG6wGAY{cmd_data}"
            crc = sum(cmd.encode('ascii')) & 0xFF
            cmd += f"{crc:02X}"
            
            self.send_command(cmd.encode('ascii'), f"Move yaw to {angle_val}°")
            time.sleep(5.0)  # Wait for movement
            
            # Get final position
            final = self.get_attitude()
            if final:
                self.log(f"  Final: Y={final['yaw']:.2f}° P={final['pitch']:.2f}°")
                self.log(f"  Yaw change: {final['yaw'] - initial['yaw']:.2f}°")
    
    def test_zoom_control(self):
        """Test zoom control (protocol 3.1)"""
        self.log("\n" + "="*60)
        self.log("ZOOM CONTROL TEST (Protocol Section 3.1)")
        self.log("="*60)
        
        # Get initial zoom
        initial_zoom = self.get_zoom_position()
        self.log(f"Initial zoom position: {initial_zoom}")
        
        # Test zoom commands
        zoom_tests = [
            ("Zoom IN", b"#TPUM2wZMC025E", 3.0),
            ("Stop zoom", b"#TPUM2wZMC005C", 0.5),
            ("Zoom OUT", b"#TPUM2wZMC015D", 3.0),
            ("Stop zoom", b"#TPUM2wZMC005C", 0.5),
        ]
        
        for desc, cmd, duration in zoom_tests:
            self.send_command(cmd, desc)
            time.sleep(duration)
            
            zoom_pos = self.get_zoom_position()
            if zoom_pos is not None:
                self.log(f"  Zoom position after {desc}: {zoom_pos}")
                
                # Also get magnification if available (ZMP command)
                self.sock.sendto(b"#TPMU2rZMP0065", (self.camera_ip, self.control_port))
                try:
                    data, _ = self.recv_sock.recvfrom(1024)
                    resp = data.decode('ascii', errors='replace')
                    if 'ZMP' in resp:
                        idx = resp.find('ZMP') + 3
                        if idx + 6 <= len(resp):
                            mag_hex = resp[idx:idx+2]
                            mag = int(mag_hex, 16) / 10.0
                            self.log(f"  Magnification: {mag}x")
                except:
                    pass
    
    def test_focus_control(self):
        """Test focus control (protocol 3.2)"""
        self.log("\n" + "="*60)
        self.log("FOCUS CONTROL TEST (Protocol Section 3.2)")
        self.log("="*60)
        
        # Get initial focus
        initial_focus = self.get_focus_position()
        self.log(f"Initial focus position: {initial_focus}")
        
        # Test focus modes
        focus_tests = [
            ("Auto focus", b"#TPUM2wFCC104C"),
            ("Manual focus", b"#TPUM2wFCC114D"),
            ("Focus +", b"#TPUM2wFCC013F"),
            ("Stop", b"#TPUM2wFCC003E"),
            ("Focus -", b"#TPUM2wFCC0240"),
            ("Stop", b"#TPUM2wFCC003E"),
        ]
        
        for desc, cmd in focus_tests:
            self.send_command(cmd, desc)
            time.sleep(2.0)
            
            focus_pos = self.get_focus_position()
            if focus_pos is not None:
                self.log(f"  Focus position after {desc}: {focus_pos}")
    
    def test_complete_motion_range(self):
        """Test complete range of motion"""
        self.log("\n" + "="*60)
        self.log("COMPLETE MOTION RANGE TEST")
        self.log("="*60)
        
        # First go to home position
        self.send_command(b"#TPUG2wPTZ056F", "Go HOME")
        time.sleep(3.0)
        
        home_pos = self.get_attitude()
        if home_pos:
            self.log(f"HOME position: Y={home_pos['yaw']:.2f}° P={home_pos['pitch']:.2f}° R={home_pos['roll']:.2f}°")
        
        # Test each direction
        directions = [
            ("UP", b"#TPUG2wPTZ016B", 3.0),
            ("DOWN", b"#TPUG2wPTZ026C", 6.0),  # Go past center
            ("CENTER", b"#TPUG2wPTZ026C", 3.0),  # Return to center
            ("LEFT", b"#TPUG2wPTZ036D", 3.0),
            ("RIGHT", b"#TPUG2wPTZ046E", 6.0),  # Go past center
            ("CENTER", b"#TPUG2wPTZ046E", 3.0),  # Return to center
        ]
        
        for direction, cmd, duration in directions:
            self.log(f"\nMoving {direction} for {duration}s...")
            self.send_command(cmd, f"Move {direction}")
            
            # Monitor position during movement
            start_time = time.time()
            while time.time() - start_time < duration:
                attitude = self.get_attitude()
                if attitude:
                    elapsed = time.time() - start_time
                    self.log(f"  [{elapsed:.1f}s] Y={attitude['yaw']:7.2f}° P={attitude['pitch']:7.2f}° R={attitude['roll']:7.2f}°")
                time.sleep(0.5)
            
            # Stop
            self.send_command(b"#TPUG2wPTZ006A", "STOP")
            time.sleep(0.5)
    
    def run_all_tests(self):
        """Run all motion tests"""
        self.log("Starting comprehensive gimbal motion tests")
        self.log(f"Camera: {self.camera_ip}:{self.control_port}")
        self.log(f"Protocol limits: Yaw±150° Pitch±90° Roll±90° Speed:0-99°/s")
        
        try:
            # Initial status
            self.log("\nINITIAL STATUS:")
            attitude = self.get_attitude()
            if attitude:
                self.log(f"Attitude: Y={attitude['yaw']:.2f}° P={attitude['pitch']:.2f}° R={attitude['roll']:.2f}°")
            
            zoom = self.get_zoom_position()
            if zoom is not None:
                self.log(f"Zoom: {zoom}")
                
            focus = self.get_focus_position()
            if focus is not None:
                self.log(f"Focus: {focus}")
            
            # Run tests
            self.test_complete_motion_range()
            self.test_speed_mode()
            self.test_angle_mode()
            self.test_zoom_control()
            self.test_focus_control()
            
            # Return to home
            self.log("\nReturning to HOME...")
            self.send_command(b"#TPUG2wPTZ056F", "Go HOME")
            time.sleep(3.0)
            
            # Final status
            self.log("\nFINAL STATUS:")
            attitude = self.get_attitude()
            if attitude:
                self.log(f"Attitude: Y={attitude['yaw']:.2f}° P={attitude['pitch']:.2f}° R={attitude['roll']:.2f}°")
            
        except Exception as e:
            self.log(f"ERROR: {e}")
            import traceback
            self.log(traceback.format_exc())
        
        finally:
            self.log(f"\nTest complete. Log saved to: {self.log_file.name}")
            self.log_file.close()
            self.sock.close()
            self.recv_sock.close()


def main():
    print("="*60)
    print("GIMBAL FULL MOTION TEST")
    print("="*60)
    print("This will test all axes through their full range.")
    print("Make sure area around gimbal is clear!")
    print()
    
    response = input("Ready to start? (y/n): ")
    if response.lower() != 'y':
        print("Aborted.")
        return
    
    tester = MotionTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()