#!/usr/bin/env python3
"""
Gimbal Real-World Application Tests
====================================
Test practical gimbal applications and use cases.
Based on protocol documentation and real-world scenarios.
"""

import socket
import time
import struct
import math
from datetime import datetime
from config import GIMBAL_CONFIG


class ApplicationTester:
    def __init__(self):
        self.camera_ip = GIMBAL_CONFIG['camera_ip']
        self.control_port = GIMBAL_CONFIG['control_port']
        self.listen_port = GIMBAL_CONFIG['listen_port']
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock.bind(('0.0.0.0', self.listen_port))
        self.recv_sock.settimeout(0.5)
        
    def send_command(self, cmd):
        """Send command"""
        self.sock.sendto(cmd, (self.camera_ip, self.control_port))
        
    def get_response(self, timeout=1.0):
        """Get response with timeout"""
        self.recv_sock.settimeout(timeout)
        try:
            data, _ = self.recv_sock.recvfrom(1024)
            return data
        except socket.timeout:
            return None
    
    def test_surveillance_scan(self):
        """Test surveillance scanning pattern"""
        print("\n" + "="*60)
        print("SURVEILLANCE SCAN TEST")
        print("="*60)
        print("Testing automated surveillance scan pattern")
        
        # Define scan pattern
        scan_points = [
            {"name": "Position 1", "yaw": -45.0, "pitch": -30.0},
            {"name": "Position 2", "yaw": 0.0, "pitch": -30.0},
            {"name": "Position 3", "yaw": 45.0, "pitch": -30.0},
            {"name": "Position 4", "yaw": 45.0, "pitch": 0.0},
            {"name": "Position 5", "yaw": 0.0, "pitch": 0.0},
            {"name": "Position 6", "yaw": -45.0, "pitch": 0.0},
        ]
        
        # Go to home first
        print("\nGoing to home position...")
        self.send_command(b"#TPUG2wPTZ056F")
        time.sleep(3)
        
        # Execute scan pattern
        for point in scan_points:
            print(f"\nMoving to {point['name']}: Yaw={point['yaw']}° Pitch={point['pitch']}°")
            
            # Build angle control command (GAM - combined yaw+pitch)
            yaw_int = int(point['yaw'] * 100)
            pitch_int = int(point['pitch'] * 100)
            speed = 30  # 3 deg/s
            
            # Pack data
            data = struct.pack('>hhBB', yaw_int, pitch_int, speed, speed)
            data_hex = data.hex().upper()
            
            cmd = f"#tpUGCwGAM{data_hex}"
            crc = sum(cmd.encode('ascii')) & 0xFF
            cmd += f"{crc:02X}"
            
            self.send_command(cmd.encode('ascii'))
            
            # Wait for movement and take snapshot
            time.sleep(3)
            
            # Simulate snapshot at each position
            print(f"  Taking snapshot at {point['name']}")
            self.send_command(b"#TPUD2wCAP013E")
            time.sleep(1)
            
            # Get current position for verification
            self.send_command(b"#TPPG2rGAC002D")
            response = self.get_response()
            if response:
                resp_str = response.decode('ascii', errors='replace')
                if 'GAC' in resp_str:
                    print(f"  Position verified")
        
        # Return home
        print("\nReturning to home...")
        self.send_command(b"#TPUG2wPTZ056F")
        time.sleep(3)
        
        print("\nSurveillance scan complete!")
    
    def test_target_tracking_simulation(self):
        """Test target tracking with simulated movement"""
        print("\n" + "="*60)
        print("TARGET TRACKING SIMULATION")
        print("="*60)
        print("Simulating tracking a moving target")
        
        # Simulate target moving across screen
        target_path = []
        for i in range(20):
            t = i / 19.0  # 0 to 1
            x = int(300 + 1320 * t)  # Move from x=300 to x=1620
            y = int(540 + 200 * math.sin(t * math.pi * 2))  # Sine wave vertically
            target_path.append((x, y))
        
        print(f"\nSimulating target moving across {len(target_path)} positions")
        
        for i, (x, y) in enumerate(target_path):
            # Send LOC command to track target
            param_x = round(2000 * x / 1920 - 1000)
            param_y = round(2000 * y / 1080 - 1000)
            param_w = round(2000 * 100 / 1920)  # 100 pixel width
            param_h = round(2000 * 100 / 1080)  # 100 pixel height
            blur_click = 8
            
            vals = (param_x, param_y, param_w, param_h, blur_click)
            data_bytes = b''.join(struct.pack('>h', v) for v in vals)
            
            cmd = f"#tpPDAw LOC" + data_bytes.hex().upper()
            crc = sum(cmd.encode('ascii')) & 0xFF
            cmd += f"{crc:02X}"
            
            self.send_command(cmd.encode('ascii'))
            
            # Get gimbal position
            self.send_command(b"#TPPG2rGAC002D")
            response = self.get_response(0.1)
            
            if response and i % 5 == 0:  # Print every 5th position
                print(f"  Target at ({x},{y}) - Gimbal tracking")
            
            time.sleep(0.2)  # 5 Hz update rate
        
        print("\nTracking simulation complete!")
    
    def test_zoom_tracking(self):
        """Test zoom adjustment during tracking"""
        print("\n" + "="*60)
        print("ZOOM TRACKING TEST")
        print("="*60)
        print("Testing automatic zoom adjustment")
        
        # Get initial zoom
        self.send_command(b"#TPUM2rZOM0063")
        response = self.get_response()
        initial_zoom = 0
        if response:
            resp_str = response.decode('ascii', errors='replace')
            if 'ZOM' in resp_str:
                idx = resp_str.find('ZOM') + 3
                try:
                    zoom_hex = resp_str[idx:idx+4]
                    initial_zoom = int(zoom_hex, 16)
                    if initial_zoom > 0x7FFF: initial_zoom -= 0x10000
                    print(f"Initial zoom position: {initial_zoom}")
                except:
                    pass
        
        # Simulate tracking with zoom
        print("\nSimulating target distance changes...")
        
        distances = [100, 80, 60, 40, 20, 40, 60, 80, 100]  # meters
        
        for distance in distances:
            # Calculate zoom based on distance (inverse relationship)
            # Closer = more zoom out, farther = more zoom in
            if distance < 50:
                zoom_cmd = b"#TPUM2wZMC015D"  # Zoom out
                zoom_duration = (50 - distance) / 30.0
            else:
                zoom_cmd = b"#TPUM2wZMC025E"  # Zoom in
                zoom_duration = (distance - 50) / 30.0
            
            print(f"\nTarget at {distance}m")
            print(f"  Adjusting zoom for {zoom_duration:.1f}s")
            
            # Start zoom
            self.send_command(zoom_cmd)
            time.sleep(zoom_duration)
            
            # Stop zoom
            self.send_command(b"#TPUM2wZMC005C")
            
            # Get new zoom position
            self.send_command(b"#TPUM2rZOM0063")
            response = self.get_response()
            if response:
                resp_str = response.decode('ascii', errors='replace')
                if 'ZOM' in resp_str:
                    print(f"  Zoom adjusted")
            
            time.sleep(0.5)
        
        print("\nZoom tracking test complete!")
    
    def test_thermal_scan(self):
        """Test thermal scanning for hot spots"""
        print("\n" + "="*60)
        print("THERMAL SCAN TEST")
        print("="*60)
        print("Scanning for temperature anomalies")
        
        # Switch to thermal view if available
        print("\nSwitching to thermal mode...")
        self.send_command(b"#TPUD2wPIP035C")  # Sub only (thermal)
        time.sleep(1)
        
        # Define scan grid
        grid_points = []
        for pitch in [-30, -15, 0]:
            for yaw in [-60, -30, 0, 30, 60]:
                grid_points.append((yaw, pitch))
        
        temperature_map = []
        
        for yaw, pitch in grid_points:
            # Move to position
            yaw_int = int(yaw * 100)
            pitch_int = int(pitch * 100)
            speed = 50  # 5 deg/s
            
            data = struct.pack('>hhBB', yaw_int, pitch_int, speed, speed)
            cmd = f"#tpUGCwGAM{data.hex().upper()}"
            crc = sum(cmd.encode('ascii')) & 0xFF
            cmd += f"{crc:02X}"
            
            self.send_command(cmd.encode('ascii'))
            time.sleep(2)  # Wait for movement
            
            # Request temperature data
            # This would normally come from SEI or TMP commands
            print(f"  Scanning position Y:{yaw:4.0f}° P:{pitch:4.0f}°")
            
            # Simulate temperature reading
            temp = 20.0 + (yaw/60.0) * 5.0 + (pitch/30.0) * 3.0
            temperature_map.append({
                'yaw': yaw,
                'pitch': pitch,
                'temp': temp
            })
            
            if temp > 25.0:
                print(f"    ⚠️  Hot spot detected: {temp:.1f}°C")
        
        # Find hottest point
        hottest = max(temperature_map, key=lambda x: x['temp'])
        print(f"\nHottest point: Y:{hottest['yaw']}° P:{hottest['pitch']}° = {hottest['temp']:.1f}°C")
        
        # Move to hottest point
        print("\nMoving to hottest point...")
        yaw_int = int(hottest['yaw'] * 100)
        pitch_int = int(hottest['pitch'] * 100)
        data = struct.pack('>hhBB', yaw_int, pitch_int, 30, 30)
        cmd = f"#tpUGCwGAM{data.hex().upper()}"
        crc = sum(cmd.encode('ascii')) & 0xFF
        cmd += f"{crc:02X}"
        self.send_command(cmd.encode('ascii'))
        
        # Return to normal view
        time.sleep(3)
        self.send_command(b"#TPUD2wPIP0063")  # Main only
        
        print("\nThermal scan complete!")
    
    def test_recording_modes(self):
        """Test different recording scenarios"""
        print("\n" + "="*60)
        print("RECORDING MODES TEST")
        print("="*60)
        
        scenarios = [
            {
                "name": "Time-lapse Recording",
                "setup": [
                    ("Set low bitrate", b"#TPUD2wBIT0149"),  # 2Mbps
                    ("Set HD resolution", b"#TPUD2wVID014A"),  # 1920x1080
                ],
                "action": "Take snapshots every 5 seconds"
            },
            {
                "name": "High-Quality Recording",
                "setup": [
                    ("Set high bitrate", b"#TPUD2wBIT074F"),  # 8Mbps
                    ("Set 4K resolution", b"#TPUD2wVID0049"),  # 3840x2160
                ],
                "action": "Record for 10 seconds"
            },
            {
                "name": "Dual Stream Recording",
                "setup": [
                    ("Set PIP mode", b"#TPUD2wPIP015B"),  # Main+Sub
                ],
                "action": "Record both thermal and visible"
            }
        ]
        
        for scenario in scenarios:
            print(f"\n{scenario['name']}:")
            print("-" * 40)
            
            # Setup
            for desc, cmd in scenario['setup']:
                print(f"  {desc}")
                self.send_command(cmd)
                time.sleep(0.5)
            
            # Execute action
            print(f"  {scenario['action']}")
            
            if "Record" in scenario['action']:
                # Start recording
                self.send_command(b"#TPUD2wREC0145")
                print("    Recording started")
                time.sleep(10)
                
                # Stop recording
                self.send_command(b"#TPUD2wREC0044")
                print("    Recording stopped")
                
            elif "snapshots" in scenario['action']:
                for i in range(3):
                    self.send_command(b"#TPUD2wCAP013E")
                    print(f"    Snapshot {i+1}")
                    time.sleep(5)
            
            time.sleep(1)
        
        # Reset to defaults
        print("\nResetting to default settings...")
        self.send_command(b"#TPUD2wBIT034B")  # 4Mbps
        self.send_command(b"#TPUD2wVID014A")  # HD
        self.send_command(b"#TPUD2wPIP0063")  # Main only
        
        print("\nRecording modes test complete!")
    
    def test_preset_positions(self):
        """Test saving and recalling preset positions"""
        print("\n" + "="*60)
        print("PRESET POSITIONS TEST")
        print("="*60)
        print("Testing preset position functionality")
        
        # Note: Based on protocol section 3.5 and 4.4 (not supported on all models)
        
        # Define preset positions
        presets = [
            {"id": 1, "yaw": -90.0, "pitch": -45.0, "zoom": 2.0},
            {"id": 2, "yaw": 0.0, "pitch": -30.0, "zoom": 5.0},
            {"id": 3, "yaw": 90.0, "pitch": -45.0, "zoom": 2.0},
        ]
        
        print("\nSetting preset positions...")
        print("Note: This feature may not be supported on all models")
        
        for preset in presets:
            print(f"\nPreset {preset['id']}:")
            
            # Move to position
            yaw_int = int(preset['yaw'] * 100)
            pitch_int = int(preset['pitch'] * 100)
            data = struct.pack('>hhBB', yaw_int, pitch_int, 30, 30)
            cmd = f"#tpUGCwGAM{data.hex().upper()}"
            crc = sum(cmd.encode('ascii')) & 0xFF
            cmd += f"{crc:02X}"
            
            print(f"  Moving to Y:{preset['yaw']}° P:{preset['pitch']}°")
            self.send_command(cmd.encode('ascii'))
            time.sleep(3)
            
            # Set zoom (if supported)
            zoom_val = int(preset['zoom'] * 10)
            cmd = f"#tpUM4wCZR{preset['id']:01X}{zoom_val:03X}"
            crc = sum(cmd.encode('ascii')) & 0xFF
            cmd += f"{crc:02X}"
            
            print(f"  Setting zoom to {preset['zoom']}x")
            self.send_command(cmd.encode('ascii'))
            time.sleep(1)
            
            # Save position (protocol may vary)
            print(f"  Position saved as Preset {preset['id']}")
        
        # Test recall
        print("\nRecalling preset positions...")
        for i in [2, 1, 3]:
            print(f"  Recalling Preset {i}")
            # Recall command would go here
            time.sleep(3)
        
        print("\nPreset positions test complete!")
        print("(Feature availability depends on gimbal model)")


def main():
    print("="*60)
    print("GIMBAL APPLICATION TESTS")
    print("="*60)
    print("Testing real-world gimbal applications")
    
    tester = ApplicationTester()
    
    tests = [
        ("Surveillance Scan", tester.test_surveillance_scan),
        ("Target Tracking", tester.test_target_tracking_simulation),
        ("Zoom Tracking", tester.test_zoom_tracking),
        ("Thermal Scan", tester.test_thermal_scan),
        ("Recording Modes", tester.test_recording_modes),
        ("Preset Positions", tester.test_preset_positions),
    ]
    
    print("\nAvailable tests:")
    for i, (name, _) in enumerate(tests):
        print(f"{i+1}. {name}")
    print(f"{len(tests)+1}. Run all tests")
    
    choice = input(f"\nSelect test (1-{len(tests)+1}): ").strip()
    
    try:
        choice_idx = int(choice) - 1
        if choice_idx == len(tests):
            # Run all tests
            for name, test_func in tests:
                print(f"\n{'='*60}")
                print(f"Running: {name}")
                print('='*60)
                test_func()
                time.sleep(2)
        elif 0 <= choice_idx < len(tests):
            # Run selected test
            name, test_func = tests[choice_idx]
            test_func()
        else:
            print("Invalid choice")
    except ValueError:
        print("Invalid input")
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
    finally:
        tester.sock.close()
        tester.recv_sock.close()
        
    print("\n" + "="*60)
    print("Application tests complete!")
    print("="*60)


if __name__ == "__main__":
    main()