#!/usr/bin/env python3
"""
Detailed Command Testing
========================
Test gimbal commands with detailed logging and verification.
Based on protocol documentation and sample commands.
"""

import socket
import time
import struct
from datetime import datetime
from config import GIMBAL_CONFIG


class DetailedCommandTester:
    def __init__(self):
        self.camera_ip = GIMBAL_CONFIG['camera_ip']
        self.control_port = GIMBAL_CONFIG['control_port']
        self.listen_port = GIMBAL_CONFIG['listen_port']
        
        # Create sockets
        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock.bind(('0.0.0.0', self.listen_port))
        self.recv_sock.settimeout(2.0)
        
        self.log_file = open(f"command_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", 'w')
        
    def log(self, message):
        """Log to console and file"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        self.log_file.write(log_entry + '\n')
        self.log_file.flush()
        
    def send_raw_command(self, cmd_bytes, description=""):
        """Send raw command bytes and log everything"""
        self.log(f"\n{'='*60}")
        self.log(f"TEST: {description}")
        self.log(f"{'='*60}")
        
        # Log command details
        self.log(f"Command bytes (hex): {cmd_bytes.hex()}")
        self.log(f"Command length: {len(cmd_bytes)} bytes")
        
        # Try to decode as ASCII for readability
        try:
            ascii_repr = cmd_bytes.decode('ascii', errors='replace')
            self.log(f"ASCII representation: {ascii_repr}")
        except:
            pass
            
        # Send command
        self.send_sock.sendto(cmd_bytes, (self.camera_ip, self.control_port))
        self.log(f"Sent to {self.camera_ip}:{self.control_port}")
        
        # Wait for response
        try:
            response, addr = self.recv_sock.recvfrom(1024)
            self.log(f"\nResponse from {addr}:")
            self.log(f"Response bytes (hex): {response.hex()}")
            self.log(f"Response length: {len(response)} bytes")
            
            # Decode response
            try:
                resp_ascii = response.decode('ascii', errors='replace')
                self.log(f"Response ASCII: {resp_ascii}")
                
                # Parse response structure
                if len(resp_ascii) > 10:
                    self.log("\nResponse breakdown:")
                    self.log(f"  Frame header: {resp_ascii[0:3]}")
                    self.log(f"  Addresses: {resp_ascii[3:5]}")
                    if '#tp' in resp_ascii:
                        length_char = resp_ascii[5]
                        self.log(f"  Data length: {length_char} ({int(length_char, 16)} bytes)")
                        self.log(f"  Control bit: {resp_ascii[6]}")
                        self.log(f"  Identifier: {resp_ascii[7:10]}")
                        data_len = int(length_char, 16) if length_char in '0123456789ABCDEF' else 0
                        if data_len > 0:
                            self.log(f"  Data: {resp_ascii[10:10+data_len]}")
                    self.log(f"  CRC: {resp_ascii[-2:]}")
                    
                return response, resp_ascii
            except Exception as e:
                self.log(f"Error parsing response: {e}")
                return response, None
                
        except socket.timeout:
            self.log("No response received (timeout)")
            return None, None
    
    def test_exact_sample_commands(self):
        """Test exact commands from the sample code"""
        self.log("\n" + "="*80)
        self.log("TESTING EXACT SAMPLE COMMANDS FROM DOCUMENTATION")
        self.log("="*80)
        
        # Commands from GimbalUdpControlDemo.py comments
        sample_commands = [
            ("Capture photo", b"#TPUD2wCAP013E"),
            ("Toggle recording", b"#TPUD2wREC0A54"),
            ("Gimbal up", b"#TPUG2wPTZ016B"),
            ("Gimbal down", b"#TPUG2wPTZ026C"),
            ("Gimbal left", b"#TPUG2wPTZ036D"),
            ("Gimbal right", b"#TPUG2wPTZ046E"),
            ("Gimbal stop", b"#TPUG2wPTZ006A"),
            ("Gimbal home", b"#TPUG2wPTZ056F"),
        ]
        
        for desc, cmd in sample_commands:
            self.send_raw_command(cmd, f"Sample command: {desc}")
            time.sleep(0.5)
    
    def test_attitude_reading(self):
        """Test attitude reading with verification"""
        self.log("\n" + "="*80)
        self.log("ATTITUDE READING TEST WITH VERIFICATION")
        self.log("="*80)
        
        # Read attitude multiple times
        attitudes = []
        for i in range(3):
            cmd = b"#TPPG2rGAC002D"  # From test_connection.py success
            response, resp_ascii = self.send_raw_command(cmd, f"Get Attitude #{i+1}")
            
            if resp_ascii and 'GAC' in resp_ascii:
                try:
                    idx = resp_ascii.find('GAC') + 3
                    if idx + 12 <= len(resp_ascii):
                        yaw_hex = resp_ascii[idx:idx+4]
                        pitch_hex = resp_ascii[idx+4:idx+8]
                        roll_hex = resp_ascii[idx+8:idx+12]
                        
                        yaw = int(yaw_hex, 16)
                        pitch = int(pitch_hex, 16)
                        roll = int(roll_hex, 16)
                        
                        # Handle signed values
                        if yaw > 0x7FFF: yaw -= 0x10000
                        if pitch > 0x7FFF: pitch -= 0x10000
                        if roll > 0x7FFF: roll -= 0x10000
                        
                        attitude = {
                            'yaw': yaw / 100.0,
                            'pitch': pitch / 100.0,
                            'roll': roll / 100.0
                        }
                        attitudes.append(attitude)
                        
                        self.log(f"\nParsed attitude:")
                        self.log(f"  Yaw:   {attitude['yaw']:7.2f}° (hex: {yaw_hex})")
                        self.log(f"  Pitch: {attitude['pitch']:7.2f}° (hex: {pitch_hex})")
                        self.log(f"  Roll:  {attitude['roll']:7.2f}° (hex: {roll_hex})")
                except Exception as e:
                    self.log(f"Error parsing attitude: {e}")
            
            time.sleep(1)
        
        # Check if attitude values change
        if len(attitudes) >= 2:
            self.log("\nAttitude stability check:")
            for i in range(1, len(attitudes)):
                yaw_diff = abs(attitudes[i]['yaw'] - attitudes[i-1]['yaw'])
                pitch_diff = abs(attitudes[i]['pitch'] - attitudes[i-1]['pitch'])
                roll_diff = abs(attitudes[i]['roll'] - attitudes[i-1]['roll'])
                self.log(f"  Reading {i} to {i+1} differences: "
                        f"Yaw={yaw_diff:.2f}° Pitch={pitch_diff:.2f}° Roll={roll_diff:.2f}°")
    
    def test_movement_with_verification(self):
        """Test movement commands with attitude verification"""
        self.log("\n" + "="*80)
        self.log("MOVEMENT TEST WITH VERIFICATION")
        self.log("="*80)
        
        # Get initial attitude
        cmd = b"#TPPG2rGAC002D"
        response, resp_ascii = self.send_raw_command(cmd, "Get initial attitude")
        initial_yaw = None
        
        if resp_ascii and 'GAC' in resp_ascii:
            try:
                idx = resp_ascii.find('GAC') + 3
                yaw_hex = resp_ascii[idx:idx+4]
                initial_yaw = int(yaw_hex, 16)
                if initial_yaw > 0x7FFF: initial_yaw -= 0x10000
                initial_yaw = initial_yaw / 100.0
                self.log(f"Initial yaw: {initial_yaw:.2f}°")
            except:
                pass
        
        # Move left
        self.send_raw_command(b"#TPUG2wPTZ036D", "Move LEFT")
        time.sleep(2)  # Let it move
        
        # Stop
        self.send_raw_command(b"#TPUG2wPTZ006A", "STOP movement")
        time.sleep(0.5)
        
        # Get new attitude
        response, resp_ascii = self.send_raw_command(cmd, "Get attitude after movement")
        
        if resp_ascii and 'GAC' in resp_ascii and initial_yaw is not None:
            try:
                idx = resp_ascii.find('GAC') + 3
                yaw_hex = resp_ascii[idx:idx+4]
                new_yaw = int(yaw_hex, 16)
                if new_yaw > 0x7FFF: new_yaw -= 0x10000
                new_yaw = new_yaw / 100.0
                
                yaw_change = new_yaw - initial_yaw
                self.log(f"New yaw: {new_yaw:.2f}°")
                self.log(f"Yaw change: {yaw_change:.2f}°")
                
                if abs(yaw_change) > 0.5:
                    self.log("[OK] Movement verified - gimbal moved!")
                else:
                    self.log("[!] No significant movement detected")
            except:
                pass
    
    def test_zoom_commands(self):
        """Test zoom commands with position verification"""
        self.log("\n" + "="*80)
        self.log("ZOOM TEST WITH VERIFICATION")
        self.log("="*80)
        
        # Get initial zoom position
        cmd = b"#TPUM2rZOM0063"
        response, resp_ascii = self.send_raw_command(cmd, "Get initial zoom position")
        initial_zoom = None
        
        if resp_ascii and 'ZOM' in resp_ascii:
            try:
                idx = resp_ascii.find('ZOM') + 3
                if idx + 4 <= len(resp_ascii):
                    zoom_hex = resp_ascii[idx:idx+4]
                    initial_zoom = int(zoom_hex, 16)
                    if initial_zoom > 0x7FFF: initial_zoom -= 0x10000
                    self.log(f"Initial zoom position: {initial_zoom} (hex: {zoom_hex})")
            except:
                pass
        
        # Zoom in
        self.send_raw_command(b"#TPUM2wZMC025E", "ZOOM IN")
        time.sleep(2)
        
        # Stop zoom
        self.send_raw_command(b"#TPUM2wZMC005C", "STOP ZOOM")
        time.sleep(0.5)
        
        # Get new zoom position
        response, resp_ascii = self.send_raw_command(cmd, "Get zoom position after zoom in")
        
        if resp_ascii and 'ZOM' in resp_ascii and initial_zoom is not None:
            try:
                idx = resp_ascii.find('ZOM') + 3
                if idx + 4 <= len(resp_ascii):
                    zoom_hex = resp_ascii[idx:idx+4]
                    new_zoom = int(zoom_hex, 16)
                    if new_zoom > 0x7FFF: new_zoom -= 0x10000
                    
                    zoom_change = new_zoom - initial_zoom
                    self.log(f"New zoom position: {new_zoom} (hex: {zoom_hex})")
                    self.log(f"Zoom change: {zoom_change}")
                    
                    if zoom_change != 0:
                        self.log("[OK] Zoom command verified - zoom position changed!")
                    else:
                        self.log("[!] No zoom change detected")
            except:
                pass
    
    def test_recording_status(self):
        """Test recording commands with status verification"""
        self.log("\n" + "="*80)
        self.log("RECORDING TEST WITH VERIFICATION")
        self.log("="*80)
        
        # Get recording status
        cmd = b"#TPUD2rREC003E"
        response, resp_ascii = self.send_raw_command(cmd, "Get recording status")
        
        # Start recording
        self.send_raw_command(b"#TPUD2wREC0145", "START recording")
        time.sleep(2)
        
        # Get status again
        response, resp_ascii = self.send_raw_command(cmd, "Get recording status after start")
        
        # Stop recording
        self.send_raw_command(b"#TPUD2wREC0044", "STOP recording")
        time.sleep(1)
        
        # Get final status
        response, resp_ascii = self.send_raw_command(cmd, "Get final recording status")
    
    def run_all_tests(self):
        """Run all tests"""
        self.log(f"Starting detailed command tests at {datetime.now()}")
        self.log(f"Camera IP: {self.camera_ip}")
        self.log(f"Control Port: {self.control_port}")
        self.log(f"Listen Port: {self.listen_port}")
        
        try:
            # Test exact sample commands first
            self.test_exact_sample_commands()
            
            # Test attitude reading
            self.test_attitude_reading()
            
            # Test movement with verification
            self.test_movement_with_verification()
            
            # Test zoom
            self.test_zoom_commands()
            
            # Test recording
            self.test_recording_status()
            
        except Exception as e:
            self.log(f"\nError during tests: {e}")
            import traceback
            self.log(traceback.format_exc())
        
        finally:
            self.log(f"\nTests completed. Log saved to: {self.log_file.name}")
            self.log_file.close()
            self.send_sock.close()
            self.recv_sock.close()


def main():
    print("="*80)
    print("DETAILED GIMBAL COMMAND TESTING")
    print("="*80)
    print("\nThis will test various commands and log all communication details.")
    print("A detailed log file will be created for debugging.\n")
    
    input("Press Enter to start tests...")
    
    tester = DetailedCommandTester()
    tester.run_all_tests()
    
    print("\n" + "="*80)
    
    print("IMPORTANT: Please send the generated log file to developers if issues persist.")
    print("="*80)


if __name__ == "__main__":
    main()
    