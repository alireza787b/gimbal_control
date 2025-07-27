#!/usr/bin/env python3
"""
Simple Gimbal Connection Test
=============================
Quick test script to verify basic gimbal connectivity.
"""

import socket
import time
from gimbalcmdparse import build_command
from config import GIMBAL_CONFIG

def test_basic_connection():
    """Run a basic connection test"""
    print("\n=== GIMBAL CONNECTION TEST ===")
    print(f"Target: {GIMBAL_CONFIG['camera_ip']}:{GIMBAL_CONFIG['control_port']}")
    print("-" * 30)
    
    try:
        # Create sockets
        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.bind(('0.0.0.0', GIMBAL_CONFIG['listen_port']))
        recv_sock.settimeout(2.0)
        
        # Build a simple read attitude command
        cmd = build_command(
            frame_header='#TP',
            address_bit1='P',    # Network source
            address_bit2='G',    # Gimbal destination
            control_bit='r',     # Read command
            identifier_bit='GAC', # Get Attitude Command
            data='00',
            data_mode='ASCII',
            output_format='ASCII'
        )
        
        print(f"Sending: {cmd}")
        print(f"Hex: {cmd.encode().hex()}")
        
        # Send command
        send_sock.sendto(cmd.encode(), 
                        (GIMBAL_CONFIG['camera_ip'], 
                         GIMBAL_CONFIG['control_port']))
        
        # Wait for response
        print("\nWaiting for response...")
        try:
            data, addr = recv_sock.recvfrom(1024)
            print(f"\n✅ SUCCESS! Received response from {addr}")
            print(f"Raw data: {data}")
            print(f"Decoded: {data.decode('ascii', errors='ignore')}")
            
            # Try to parse attitude if valid response
            if b'GAC' in data and len(data) > 20:
                try:
                    resp_str = data.decode('ascii', errors='ignore')
                    # Find data portion (after identifier, before CRC)
                    idx = resp_str.find('GAC') + 3
                    attitude_data = resp_str[idx:idx+12]
                    
                    yaw_hex = attitude_data[0:4]
                    pitch_hex = attitude_data[4:8]
                    roll_hex = attitude_data[8:12]
                    
                    # Convert to degrees
                    yaw = int(yaw_hex, 16)
                    pitch = int(pitch_hex, 16)
                    roll = int(roll_hex, 16)
                    
                    # Handle signed values
                    if yaw > 0x7FFF: yaw -= 0x10000
                    if pitch > 0x7FFF: pitch -= 0x10000
                    if roll > 0x7FFF: roll -= 0x10000
                    
                    print(f"\nGimbal Attitude:")
                    print(f"  Yaw:   {yaw/100:.2f}°")
                    print(f"  Pitch: {pitch/100:.2f}°")
                    print(f"  Roll:  {roll/100:.2f}°")
                except Exception as e:
                    print(f"Could not parse attitude: {e}")
                    
        except socket.timeout:
            print("\n❌ TIMEOUT - No response received")
            print("\nTroubleshooting:")
            print("1. Check camera IP address")
            print("2. Verify camera is powered on")
            print("3. Check network connectivity (ping)")
            print("4. Ensure no firewall blocking UDP ports")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
    finally:
        send_sock.close()
        recv_sock.close()
    
    print("\n" + "="*30 + "\n")

if __name__ == "__main__":
    test_basic_connection()