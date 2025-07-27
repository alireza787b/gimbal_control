#!/usr/bin/env python3
"""
Network Traffic Monitor for Gimbal Communication
================================================
Monitor UDP traffic between PC and gimbal camera.
"""

import socket
import threading
import time
from datetime import datetime
from config import GIMBAL_CONFIG


class NetworkMonitor:
    def __init__(self):
        self.running = False
        self.camera_ip = GIMBAL_CONFIG['camera_ip']
        self.control_port = GIMBAL_CONFIG['control_port']
        self.listen_port = GIMBAL_CONFIG['listen_port']
        
        # Statistics
        self.stats = {
            'sent': 0,
            'received': 0,
            'timeouts': 0,
            'last_sent': None,
            'last_received': None,
            'commands': [],
            'responses': []
        }
        
    def monitor_traffic(self):
        """Monitor network traffic"""
        print(f"\nMonitoring traffic:")
        print(f"  Camera: {self.camera_ip}:{self.control_port}")
        print(f"  Listen: 0.0.0.0:{self.listen_port}")
        print("-" * 60)
        
        # Create receive socket
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.bind(('0.0.0.0', self.listen_port))
        recv_sock.settimeout(0.1)
        
        while self.running:
            try:
                data, addr = recv_sock.recvfrom(1024)
                timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                
                # Log received data
                print(f"\n[{timestamp}] RECEIVED from {addr}")
                print(f"  Hex: {data.hex()}")
                print(f"  ASCII: {data.decode('ascii', errors='replace')}")
                
                # Analyze if it's from camera
                if addr[0] == self.camera_ip:
                    self.stats['received'] += 1
                    self.stats['last_received'] = timestamp
                    self.stats['responses'].append({
                        'time': timestamp,
                        'data': data.hex(),
                        'ascii': data.decode('ascii', errors='replace')
                    })
                    
                    # Quick parse
                    if len(data) > 10:
                        ascii_data = data.decode('ascii', errors='replace')
                        print(f"  Frame: {ascii_data[0:3]}")
                        print(f"  Identifier: {ascii_data[7:10] if len(ascii_data) > 10 else '???'}")
                        
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Monitor error: {e}")
        
        recv_sock.close()
    
    def send_test_command(self):
        """Send a test command and monitor response"""
        print("\n" + "="*60)
        print("SENDING TEST COMMAND")
        print("="*60)
        
        # Use the known working command
        cmd = b"#TPPG2rGAC002D"
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        print(f"[{timestamp}] SENDING to {self.camera_ip}:{self.control_port}")
        print(f"  Command: {cmd.decode('ascii')}")
        print(f"  Hex: {cmd.hex()}")
        
        sock.sendto(cmd, (self.camera_ip, self.control_port))
        self.stats['sent'] += 1
        self.stats['last_sent'] = timestamp
        
        sock.close()
        
        # Wait and check for response
        time.sleep(2)
        
        if self.stats['last_received'] and self.stats['last_received'] > self.stats['last_sent']:
            print("\n[OK] Response received!")
        else:
            print("\n[X] No response received")
            self.stats['timeouts'] += 1
    
    def test_alternative_ports(self):
        """Test if gimbal responds on other ports"""
        print("\n" + "="*60)
        print("TESTING ALTERNATIVE PORTS")
        print("="*60)
        
        cmd = b"#TPPG2rGAC002D"
        test_ports = [9003, 9004, 8080, 554, 80, 1234, 5678]
        
        for port in test_ports:
            print(f"\nTesting port {port}...")
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)
            
            try:
                sock.sendto(cmd, (self.camera_ip, port))
                
                # Try to receive response
                try:
                    data, addr = sock.recvfrom(1024)
                    print(f"  [!] Got response from {addr}: {data.hex()}")
                except socket.timeout:
                    print(f"  No response")
                    
            except Exception as e:
                print(f"  Error: {e}")
            
            sock.close()
    
    def run_diagnostics(self):
        """Run network diagnostics"""
        print("\n" + "="*60)
        print("NETWORK DIAGNOSTICS")
        print("="*60)
        
        # Start monitor thread
        self.running = True
        monitor_thread = threading.Thread(target=self.monitor_traffic, daemon=True)
        monitor_thread.start()
        
        time.sleep(1)
        
        # Send test commands
        for i in range(3):
            self.send_test_command()
            time.sleep(2)
        
        # Test alternative ports
        self.test_alternative_ports()
        
        # Stop monitoring
        self.running = False
        time.sleep(1)
        
        # Print statistics
        print("\n" + "="*60)
        print("STATISTICS")
        print("="*60)
        print(f"Commands sent: {self.stats['sent']}")
        print(f"Responses received: {self.stats['received']}")
        print(f"Timeouts: {self.stats['timeouts']}")
        
        if self.stats['responses']:
            print("\nLast responses:")
            for resp in self.stats['responses'][-3:]:
                print(f"  [{resp['time']}] {resp['ascii']}")


def test_raw_socket():
    """Test with raw socket binding"""
    print("\n" + "="*60)
    print("RAW SOCKET TEST")
    print("="*60)
    
    try:
        # Try binding to specific interface
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Get local IP that can reach the camera
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_sock.connect((GIMBAL_CONFIG['camera_ip'], 80))
        local_ip = test_sock.getsockname()[0]
        test_sock.close()
        
        print(f"Local IP that can reach camera: {local_ip}")
        
        # Bind to specific interface
        sock.bind((local_ip, 0))  # Let OS choose port
        local_port = sock.getsockname()[1]
        print(f"Bound to {local_ip}:{local_port}")
        
        # Send command
        cmd = b"#TPPG2rGAC002D"
        print(f"\nSending: {cmd.decode('ascii')}")
        sock.sendto(cmd, (GIMBAL_CONFIG['camera_ip'], GIMBAL_CONFIG['control_port']))
        
        # Set timeout and try to receive
        sock.settimeout(3.0)
        try:
            data, addr = sock.recvfrom(1024)
            print(f"[OK] Received from {addr}: {data.decode('ascii', errors='replace')}")
        except socket.timeout:
            print("[X] No response (timeout)")
        
        sock.close()
        
    except Exception as e:
        print(f"Error: {e}")


def main():
    print("="*60)
    print("GIMBAL NETWORK MONITOR")
    print("="*60)
    
    # Run diagnostics
    monitor = NetworkMonitor()
    monitor.run_diagnostics()
    
    # Test raw socket
    test_raw_socket()
    
    print("\n" + "="*60)
    print("RECOMMENDATIONS")
    print("="*60)
    print("\nBased on the test results:")
    print("1. If no responses at all:")
    print("   - Check Windows Firewall settings")
    print("   - Try disabling antivirus temporarily")
    print("   - Verify camera IP is correct (192.168.0.108)")
    print("   - Check if camera is in correct mode")
    print("\n2. If responses received but commands don't execute:")
    print("   - Gimbal might be in locked mode")
    print("   - Try power cycling the gimbal")
    print("   - Check if gimbal is being controlled by another app")
    print("\n3. Try using the camera's own control software first")
    print("   to ensure it's working properly")


if __name__ == "__main__":
    main()