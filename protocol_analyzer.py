#!/usr/bin/env python3
"""
Protocol Communication Analyzer
===============================
Analyze protocol communication patterns and responses.
Based on SIP series protocol documentation.
"""

import socket
import time
import struct
import threading
from datetime import datetime
from collections import defaultdict
from config import GIMBAL_CONFIG


class ProtocolAnalyzer:
    def __init__(self):
        self.camera_ip = GIMBAL_CONFIG['camera_ip']
        self.control_port = GIMBAL_CONFIG['control_port']
        self.listen_port = GIMBAL_CONFIG['listen_port']
        
        # Statistics
        self.stats = defaultdict(lambda: {
            'sent': 0,
            'received': 0,
            'response_times': [],
            'errors': 0,
            'last_response': None
        })
        
        # Protocol mapping from documentation
        self.protocol_map = {
            # Gimbal commands (Section 4)
            'PTZ': 'Gimbal Control',
            'GAC': 'Get Attitude (Magnetic)',
            'GIC': 'Get Attitude (Gyro)',
            'GAA': 'Attitude Auto Send',
            'GIA': 'Gyro Attitude Auto Send',
            'GSY': 'Yaw Speed Control',
            'GSP': 'Pitch Speed Control',
            'GSR': 'Roll Speed Control',
            'GSM': 'Yaw+Pitch Speed',
            'GAY': 'Yaw Angle Control',
            'GAP': 'Pitch Angle Control',
            'GAR': 'Roll Angle Control',
            'GAM': 'Yaw+Pitch Angle',
            
            # Lens commands (Section 3)
            'ZMC': 'Zoom Control',
            'ZOM': 'Get Zoom Position',
            'FCC': 'Focus Control',
            'FOC': 'Get Focus Position',
            'ZFP': 'Set Zoom+Focus Position',
            'ZMP': 'Zoom Magnification',
            'IRC': 'Day/Night Switch',
            
            # System commands (Section 5)
            'REC': 'Recording Control',
            'CAP': 'Capture Photo',
            'VID': 'Video Resolution',
            'BIT': 'Bitrate Control',
            'SDC': 'SD Card Status',
            'ROT': 'Flip/Mirror',
            'PIP': 'Picture in Picture',
            'IMG': 'Pseudo Color',
            'DZM': 'Digital Zoom',
            'TMP': 'Temperature Measurement',
            'LOC': 'Object Tracking',
            'LRF': 'Laser Ranging',
            'GPS': 'GPS Data',
            'UAV': 'UAV Data',
            'VER': 'Version Info'
        }
        
        # Response patterns
        self.response_patterns = {}
        
    def create_test_command(self, identifier, address='G', data='00'):
        """Create a test command based on identifier"""
        # Build command according to protocol
        if len(data) == 2:
            frame = '#TP'
        else:
            frame = '#tp'
        
        cmd = f"{frame}P{address}2r{identifier}{data}"
        crc = sum(cmd.encode('ascii')) & 0xFF
        cmd += f"{crc:02X}"
        
        return cmd.encode('ascii')
    
    def analyze_response(self, response):
        """Analyze response structure"""
        try:
            resp_str = response.decode('ascii', errors='replace')
            
            analysis = {
                'raw': resp_str,
                'hex': response.hex(),
                'length': len(response),
                'valid': False,
                'error': False
            }
            
            # Check for error response (ERE)
            if 'ERE' in resp_str:
                analysis['error'] = True
                analysis['error_type'] = 'Invalid command'
                return analysis
            
            # Parse structure
            if len(resp_str) >= 10:
                analysis['frame'] = resp_str[0:3]
                analysis['addresses'] = resp_str[3:5]
                
                if analysis['frame'] == '#TP':
                    analysis['length_byte'] = resp_str[5]
                    analysis['control'] = resp_str[6]
                    analysis['identifier'] = resp_str[7:10]
                    analysis['data'] = resp_str[10:-2]
                elif analysis['frame'] == '#tp':
                    try:
                        data_len = int(resp_str[5], 16)
                        analysis['data_length'] = data_len
                        analysis['control'] = resp_str[6]
                        analysis['identifier'] = resp_str[7:10]
                        analysis['data'] = resp_str[10:10+data_len]
                    except:
                        pass
                
                analysis['crc'] = resp_str[-2:]
                analysis['valid'] = True
            
            return analysis
            
        except Exception as e:
            return {'error': str(e), 'raw': response.hex()}
    
    def test_all_commands(self):
        """Test all known commands systematically"""
        print("\n" + "="*60)
        print("TESTING ALL PROTOCOL COMMANDS")
        print("="*60)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.bind(('0.0.0.0', self.listen_port))
        recv_sock.settimeout(0.5)
        
        # Group commands by destination
        command_groups = {
            'Gimbal (G)': [
                ('GAC', 'G', '00'),  # Get attitude
                ('GIC', 'G', '00'),  # Get gyro attitude
                ('GAA', 'G', '00'),  # Get auto-send status
                ('GIA', 'G', '00'),  # Get gyro auto-send status
            ],
            'Lens (M)': [
                ('ZOM', 'M', '00'),  # Get zoom position
                ('FOC', 'M', '00'),  # Get focus position
                ('ZMP', 'M', '00'),  # Get zoom magnification
            ],
            'System (D)': [
                ('REC', 'D', '00'),  # Get recording status
                ('VID', 'D', '00'),  # Get video resolution
                ('BIT', 'D', '00'),  # Get bitrate
                ('SDC', 'D', '00'),  # Get SD card status
                ('ROT', 'D', '00'),  # Get rotation status
                ('PIP', 'D', '00'),  # Get PIP status
                ('VER', 'D', '00'),  # Get version
            ]
        }
        
        for group_name, commands in command_groups.items():
            print(f"\n{group_name}:")
            print("-" * 40)
            
            for identifier, address, data in commands:
                description = self.protocol_map.get(identifier, 'Unknown')
                cmd = self.create_test_command(identifier, address, data)
                
                # Send command
                start_time = time.time()
                sock.sendto(cmd, (self.camera_ip, self.control_port))
                self.stats[identifier]['sent'] += 1
                
                # Wait for response
                try:
                    response, _ = recv_sock.recvfrom(1024)
                    response_time = (time.time() - start_time) * 1000  # ms
                    
                    self.stats[identifier]['received'] += 1
                    self.stats[identifier]['response_times'].append(response_time)
                    
                    # Analyze response
                    analysis = self.analyze_response(response)
                    self.stats[identifier]['last_response'] = analysis
                    
                    # Print results
                    print(f"{identifier} ({description}):")
                    print(f"  Command: {cmd.decode('ascii')}")
                    print(f"  Response: {analysis['raw']}")
                    print(f"  Time: {response_time:.1f}ms")
                    
                    if analysis['error']:
                        print(f"  ERROR: {analysis.get('error_type', 'Unknown error')}")
                        self.stats[identifier]['errors'] += 1
                    elif analysis['valid'] and 'data' in analysis:
                        print(f"  Data: {analysis['data']}")
                    
                except socket.timeout:
                    print(f"{identifier} ({description}): NO RESPONSE")
                    self.stats[identifier]['errors'] += 1
                
                time.sleep(0.2)
        
        sock.close()
        recv_sock.close()
    
    def monitor_async_messages(self, duration=30):
        """Monitor for async messages from gimbal"""
        print(f"\nMonitoring for async messages for {duration} seconds...")
        print("Some commands cause gimbal to send periodic updates")
        print("-" * 60)
        
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.bind(('0.0.0.0', self.listen_port))
        recv_sock.settimeout(0.5)
        
        # Enable some auto-send features
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Enable attitude auto-send
        sock.sendto(b"#TPUG2wGAA0136", (self.camera_ip, self.control_port))
        print("Enabled attitude auto-send")
        
        async_messages = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            try:
                data, addr = recv_sock.recvfrom(1024)
                if addr[0] == self.camera_ip:
                    timestamp = time.time() - start_time
                    analysis = self.analyze_response(data)
                    
                    async_messages.append({
                        'time': timestamp,
                        'analysis': analysis
                    })
                    
                    print(f"[{timestamp:.1f}s] Async message: {analysis.get('identifier', '???')} - {analysis['raw']}")
                    
            except socket.timeout:
                continue
        
        # Disable auto-send
        sock.sendto(b"#TPUG2wGAA0035", (self.camera_ip, self.control_port))
        
        sock.close()
        recv_sock.close()
        
        # Analyze patterns
        print(f"\nReceived {len(async_messages)} async messages")
        if async_messages:
            identifiers = [msg['analysis'].get('identifier', '???') for msg in async_messages]
            unique_identifiers = set(identifiers)
            print(f"Message types: {', '.join(unique_identifiers)}")
            
            # Calculate intervals
            for ident in unique_identifiers:
                times = [msg['time'] for msg in async_messages if msg['analysis'].get('identifier') == ident]
                if len(times) > 1:
                    intervals = [times[i+1] - times[i] for i in range(len(times)-1)]
                    avg_interval = sum(intervals) / len(intervals)
                    print(f"{ident}: {len(times)} messages, avg interval: {avg_interval:.2f}s")
    
    def test_command_variations(self):
        """Test command format variations"""
        print("\n" + "="*60)
        print("TESTING COMMAND FORMAT VARIATIONS")
        print("="*60)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.bind(('0.0.0.0', self.listen_port))
        recv_sock.settimeout(0.5)
        
        # Test GAC with different formats
        test_cases = [
            ("Standard format", "#TPPG2rGAC002D"),
            ("Different source", "#TPUG2rGAC002B"),
            ("Direct query", "#TPGG2rGAC002A"),
        ]
        
        for desc, cmd_str in test_cases:
            print(f"\n{desc}: {cmd_str}")
            
            sock.sendto(cmd_str.encode('ascii'), (self.camera_ip, self.control_port))
            
            try:
                data, _ = recv_sock.recvfrom(1024)
                analysis = self.analyze_response(data)
                print(f"  Response: {analysis['raw']}")
                if analysis.get('valid'):
                    print(f"  Valid response from: {analysis['addresses']}")
            except socket.timeout:
                print("  No response")
        
        sock.close()
        recv_sock.close()
    
    def generate_report(self):
        """Generate analysis report"""
        print("\n" + "="*60)
        print("PROTOCOL ANALYSIS REPORT")
        print("="*60)
        
        # Summary statistics
        total_sent = sum(s['sent'] for s in self.stats.values())
        total_received = sum(s['received'] for s in self.stats.values())
        total_errors = sum(s['errors'] for s in self.stats.values())
        
        print(f"\nTotal commands sent: {total_sent}")
        print(f"Total responses received: {total_received}")
        print(f"Total errors: {total_errors}")
        print(f"Success rate: {(total_received/max(total_sent,1)*100):.1f}%")
        
        # Command breakdown
        print("\nCommand Analysis:")
        print("-" * 60)
        print(f"{'Command':<8} {'Description':<25} {'Sent':<6} {'Recv':<6} {'Errors':<7} {'Avg Time':<10}")
        print("-" * 60)
        
        for identifier, stats in sorted(self.stats.items()):
            desc = self.protocol_map.get(identifier, 'Unknown')[:24]
            avg_time = sum(stats['response_times']) / len(stats['response_times']) if stats['response_times'] else 0
            
            print(f"{identifier:<8} {desc:<25} {stats['sent']:<6} {stats['received']:<6} "
                  f"{stats['errors']:<7} {avg_time:<10.1f}ms")
        
        # Working commands
        print("\nWorking Commands:")
        for identifier, stats in self.stats.items():
            if stats['received'] > 0 and stats['last_response']:
                resp = stats['last_response']
                if resp.get('valid') and not resp.get('error'):
                    print(f"  {identifier}: {resp.get('data', 'No data')}")
        
        # Failed commands
        print("\nFailed Commands:")
        for identifier, stats in self.stats.items():
            if stats['sent'] > 0 and stats['received'] == 0:
                print(f"  {identifier}: No response")
            elif stats['errors'] > 0:
                print(f"  {identifier}: {stats['errors']} errors")


def main():
    print("="*60)
    print("PROTOCOL COMMUNICATION ANALYZER")
    print("="*60)
    
    analyzer = ProtocolAnalyzer()
    
    print("\nOptions:")
    print("1. Test all known commands")
    print("2. Monitor async messages")
    print("3. Test command variations")
    print("4. Full analysis (all tests)")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == '1':
        analyzer.test_all_commands()
        analyzer.generate_report()
    elif choice == '2':
        analyzer.monitor_async_messages()
    elif choice == '3':
        analyzer.test_command_variations()
    elif choice == '4':
        analyzer.test_all_commands()
        analyzer.test_command_variations()
        analyzer.monitor_async_messages(10)
        analyzer.generate_report()
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()