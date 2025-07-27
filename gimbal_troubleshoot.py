#!/usr/bin/env python3
"""
Gimbal Troubleshooting Script
=============================
Comprehensive troubleshooting for gimbal control issues.
"""

import socket
import time
import subprocess
from datetime import datetime
from config import GIMBAL_CONFIG


class GimbalTroubleshooter:
    def __init__(self):
        self.camera_ip = GIMBAL_CONFIG['camera_ip']
        self.issues_found = []
        self.working_commands = []
        
    def log(self, message, level="INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        prefix = "✓" if level == "OK" else "✗" if level == "ERROR" else "•"
        print(f"[{timestamp}] {prefix} {message}")
        
    def test_basic_connectivity(self):
        """Test basic network connectivity"""
        print("\n" + "="*60)
        print("1. BASIC CONNECTIVITY TEST")
        print("="*60)
        
        # Test if IP is reachable (using ARP)
        try:
            # Try ARP command (works even if ICMP is blocked)
            result = subprocess.run(['arp', '-a'], capture_output=True, text=True)
            if self.camera_ip in result.stdout:
                self.log(f"Camera IP {self.camera_ip} found in ARP table", "OK")
            else:
                self.log(f"Camera IP {self.camera_ip} NOT in ARP table", "ERROR")
                self.issues_found.append("Camera not found in network")
        except:
            self.log("Could not check ARP table", "ERROR")
    
    def test_gimbal_modes(self):
        """Test different gimbal modes and states"""
        print("\n" + "="*60)
        print("2. GIMBAL MODE/STATE TEST")
        print("="*60)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.bind(('0.0.0.0', GIMBAL_CONFIG['listen_port']))
        recv_sock.settimeout(1.0)
        
        # Commands to test gimbal state
        state_commands = [
            # Try to unlock gimbal first
            ("Set follow mode", b"#TPUG2wPTZ076E"),
            ("Lock/Follow switch", b"#TPUG2wPTZ0870"),
            
            # Get current state
            ("Get attitude", b"#TPPG2rGAC002D"),
            ("Get gyro attitude", b"#TPUG2rGIC003A"),
            
            # Try attitude control modes
            ("Enable attitude sending", b"#TPUG2wGAA0136"),
            ("Enable gyro attitude sending", b"#TPUG2wGIA013E"),
        ]
        
        for desc, cmd in state_commands:
            self.log(f"Testing: {desc}")
            self.log(f"  Command: {cmd.decode('ascii', errors='replace')}")
            
            sock.sendto(cmd, (self.camera_ip, GIMBAL_CONFIG['control_port']))
            
            try:
                data, addr = recv_sock.recvfrom(1024)
                response = data.decode('ascii', errors='replace')
                self.log(f"  Response: {response}", "OK")
                self.working_commands.append((desc, cmd, response))
                
                # Check if it's an error response
                if 'ERE' in response:
                    self.log("  Error response detected!", "ERROR")
                    self.issues_found.append(f"Error response for {desc}")
                    
            except socket.timeout:
                self.log("  No response", "ERROR")
            
            time.sleep(0.5)
        
        sock.close()
        recv_sock.close()
    
    def test_initialization_sequence(self):
        """Test if gimbal needs initialization sequence"""
        print("\n" + "="*60)
        print("3. INITIALIZATION SEQUENCE TEST")
        print("="*60)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.bind(('0.0.0.0', GIMBAL_CONFIG['listen_port']))
        recv_sock.settimeout(1.0)
        
        # Try initialization sequences from different sources
        init_sequences = [
            # Sequence 1: Follow mode + calibration
            [
                ("Set follow mode", b"#TPUG2wPTZ076E"),
                ("Wait", None, 1.0),
                ("Get attitude", b"#TPPG2rGAC002D"),
            ],
            
            # Sequence 2: Unlock + home + ready
            [
                ("Unlock gimbal", b"#TPUG2wPTZ0870"),
                ("Go home", b"#TPUG2wPTZ056F"),
                ("Wait for home", None, 3.0),
                ("Get attitude", b"#TPPG2rGAC002D"),
            ],
            
            # Sequence 3: One button down + follow
            [
                ("One button down", b"#TPUG2wPTZ0A71"),
                ("Set follow mode", b"#TPUG2wPTZ076E"),
                ("Get attitude", b"#TPPG2rGAC002D"),
            ],
        ]
        
        for seq_num, sequence in enumerate(init_sequences):
            self.log(f"\nTrying initialization sequence {seq_num + 1}:")
            
            success = True
            for step in sequence:
                if len(step) == 3 and step[1] is None:
                    # Wait command
                    self.log(f"  Waiting {step[2]} seconds...")
                    time.sleep(step[2])
                else:
                    desc, cmd = step[0], step[1]
                    self.log(f"  {desc}")
                    
                    sock.sendto(cmd, (self.camera_ip, GIMBAL_CONFIG['control_port']))
                    
                    try:
                        data, _ = recv_sock.recvfrom(1024)
                        response = data.decode('ascii', errors='replace')
                        self.log(f"    Response: {response}", "OK")
                    except socket.timeout:
                        self.log("    No response", "ERROR")
                        success = False
                    
                    time.sleep(0.5)
            
            if success:
                # Test if movement works after init
                self.log("  Testing movement after init...")
                
                # Get initial position
                sock.sendto(b"#TPPG2rGAC002D", (self.camera_ip, GIMBAL_CONFIG['control_port']))
                try:
                    data, _ = recv_sock.recvfrom(1024)
                    initial_resp = data.decode('ascii', errors='replace')
                    
                    # Try movement
                    sock.sendto(b"#TPUG2wPTZ036D", (self.camera_ip, GIMBAL_CONFIG['control_port']))  # Left
                    time.sleep(1.0)
                    sock.sendto(b"#TPUG2wPTZ006A", (self.camera_ip, GIMBAL_CONFIG['control_port']))  # Stop
                    
                    # Get new position
                    time.sleep(0.5)
                    sock.sendto(b"#TPPG2rGAC002D", (self.camera_ip, GIMBAL_CONFIG['control_port']))
                    data, _ = recv_sock.recvfrom(1024)
                    final_resp = data.decode('ascii', errors='replace')
                    
                    if initial_resp != final_resp:
                        self.log("    Movement detected! Init sequence works!", "OK")
                        self.working_commands.append(("Init sequence", sequence, "Movement verified"))
                    else:
                        self.log("    No movement detected", "ERROR")
                        
                except socket.timeout:
                    self.log("    Could not verify movement", "ERROR")
        
        sock.close()
        recv_sock.close()
    
    def test_command_variations(self):
        """Test command format variations"""
        print("\n" + "="*60)
        print("4. COMMAND FORMAT VARIATIONS TEST")
        print("="*60)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.bind(('0.0.0.0', GIMBAL_CONFIG['listen_port']))
        recv_sock.settimeout(1.0)
        
        # Test different source addresses
        base_cmd = "2wPTZ006A"  # Stop command
        variations = [
            ("Network->Gimbal", f"#TPPG{base_cmd}"),
            ("UART->Gimbal", f"#TPUG{base_cmd}"),
            ("Gimbal->Gimbal", f"#TPGG{base_cmd}"),
            ("System->Gimbal", f"#TPDG{base_cmd}"),
        ]
        
        for desc, cmd_str in variations:
            # Calculate correct CRC
            crc = sum(cmd_str.encode('ascii')) & 0xFF
            full_cmd = cmd_str + f"{crc:02X}"
            
            self.log(f"Testing {desc}: {full_cmd}")
            
            sock.sendto(full_cmd.encode('ascii'), (self.camera_ip, GIMBAL_CONFIG['control_port']))
            
            try:
                data, _ = recv_sock.recvfrom(1024)
                response = data.decode('ascii', errors='replace')
                self.log(f"  Response: {response}", "OK")
                
                # Check if addresses were swapped (indicating acceptance)
                if len(response) > 5 and response[3:5] == full_cmd[4:2:-1]:
                    self.log("  Command accepted (addresses swapped)", "OK")
                    
            except socket.timeout:
                self.log("  No response", "ERROR")
            
            time.sleep(0.5)
        
        sock.close()
        recv_sock.close()
    
    def test_port_binding(self):
        """Test different source port bindings"""
        print("\n" + "="*60)
        print("5. SOURCE PORT BINDING TEST")
        print("="*60)
        
        # Test if gimbal expects commands from specific port
        test_ports = [9004, 9003, 0]  # 0 = let OS choose
        
        for src_port in test_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                
                if src_port != 0:
                    sock.bind(('', src_port))
                    actual_port = src_port
                else:
                    actual_port = sock.getsockname()[1]
                
                self.log(f"Testing from source port {actual_port}")
                
                sock.settimeout(1.0)
                sock.sendto(b"#TPPG2rGAC002D", (self.camera_ip, GIMBAL_CONFIG['control_port']))
                
                try:
                    data, addr = sock.recvfrom(1024)
                    self.log(f"  Got response from {addr}: {data.decode('ascii', errors='replace')}", "OK")
                    self.working_commands.append((f"Source port {actual_port}", None, "Got response"))
                except socket.timeout:
                    self.log("  No response", "ERROR")
                
                sock.close()
                
            except Exception as e:
                self.log(f"  Error with port {src_port}: {e}", "ERROR")
            
            time.sleep(0.5)
    
    def generate_report(self):
        """Generate troubleshooting report"""
        print("\n" + "="*60)
        print("TROUBLESHOOTING REPORT")
        print("="*60)
        
        print("\nISSUES FOUND:")
        if self.issues_found:
            for issue in self.issues_found:
                print(f"  • {issue}")
        else:
            print("  • No specific issues identified")
        
        print("\nWORKING COMMANDS/CONFIGURATIONS:")
        if self.working_commands:
            for desc, cmd, result in self.working_commands:
                print(f"  • {desc}")
                if cmd:
                    print(f"    Command: {cmd}")
                print(f"    Result: {result}")
        else:
            print("  • No working configurations found")
        
        print("\nRECOMMENDATIONS:")
        print("1. Ensure gimbal is powered on and not in standby mode")
        print("2. Check if gimbal is being controlled by another application")
        print("3. Try power cycling the gimbal")
        print("4. Verify gimbal firmware version supports this protocol")
        print("5. Check Windows Firewall - add exception for Python")
        print("6. Try using gimbal's official control software first")
        
        if not self.working_commands:
            print("\n⚠️  CRITICAL: No commands received responses!")
            print("   This suggests a fundamental communication issue.")
            print("   Please verify:")
            print("   - Camera IP address (current: " + self.camera_ip + ")")
            print("   - Camera is on the same network subnet")
            print("   - No VPN or network isolation active")


def main():
    print("="*60)
    print("GIMBAL TROUBLESHOOTING SCRIPT")
    print("="*60)
    print("\nThis will run comprehensive tests to identify issues.")
    print("Please ensure the gimbal is powered on.\n")
    
    input("Press Enter to start troubleshooting...")
    
    troubleshooter = GimbalTroubleshooter()
    
    # Run all tests
    troubleshooter.test_basic_connectivity()
    troubleshooter.test_gimbal_modes()
    troubleshooter.test_initialization_sequence()
    troubleshooter.test_command_variations()
    troubleshooter.test_port_binding()
    
    # Generate report
    troubleshooter.generate_report()
    
    print("\n" + "="*60)
    print("Troubleshooting complete.")
    print("Please share the above report with technical support if issues persist.")
    print("="*60)


if __name__ == "__main__":
    main()
    