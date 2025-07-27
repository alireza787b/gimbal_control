#!/usr/bin/env python3
"""
Test LOC Command for Object Tracking
====================================
Simple test to verify LOC command format and sending.
"""

import socket
import struct
from gimbalcmdparse import build_command
from config import GIMBAL_CONFIG


def test_loc_command():
    """Test LOC command building and sending"""
    print("\n=== LOC COMMAND TEST ===")
    print("-" * 30)
    
    # Test parameters
    x, y = 960, 540  # Center of 1920x1080 screen
    width, height = 100, 100
    preview_width, preview_height = 1920, 1080
    
    # Calculate protocol values (based on LOC_cmd.py formula)
    param_x = round(2000 * x / preview_width - 1000)
    param_y = round(2000 * y / preview_height - 1000)
    param_w = round(2000 * width / preview_width)
    param_h = round(2000 * height / preview_height)
    blur_click = 8  # Enable blur click
    
    print(f"Screen coordinates: ({x}, {y})")
    print(f"Object size: {width}x{height}")
    print(f"Protocol values: x={param_x}, y={param_y}, w={param_w}, h={param_h}")
    
    # Pack values as big-endian signed 16-bit integers
    vals = (param_x, param_y, param_w, param_h, blur_click)
    data_bytes = b''.join(struct.pack('>h', v) for v in vals)
    print(f"Data bytes (hex): {data_bytes.hex()}")
    
    # Convert to space-separated hex string for build_command
    data_hex = ' '.join(f'{b:02X}' for b in data_bytes)
    print(f"Data hex string: {data_hex}")
    
    # Build command with hex output
    try:
        cmd_hex = build_command(
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
        print(f"\nCommand built successfully!")
        print(f"Hex command: {cmd_hex}")
        print(f"Command length: {len(cmd_hex)//2} bytes")
        
        # Convert hex string to bytes for sending
        cmd_bytes = bytes.fromhex(cmd_hex)
        print(f"Command bytes: {cmd_bytes}")
        
        # Try to decode as ASCII to see structure
        try:
            ascii_repr = cmd_bytes.decode('ascii', errors='replace')
            print(f"ASCII representation: {ascii_repr}")
        except:
            pass
        
        # Send command
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(cmd_bytes, (GIMBAL_CONFIG['camera_ip'], GIMBAL_CONFIG['control_port']))
        print(f"\n[OK] Command sent to {GIMBAL_CONFIG['camera_ip']}:{GIMBAL_CONFIG['control_port']}")
        sock.close()
        
    except Exception as e:
        print(f"\n[ERROR] Failed to build/send command: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*30 + "\n")


def test_stop_tracking():
    """Test stopping tracking (zero size)"""
    print("\n=== STOP TRACKING TEST ===")
    print("-" * 30)
    
    # Zero values to stop tracking
    vals = (0, 0, 0, 0, 0)
    data_bytes = b''.join(struct.pack('>h', v) for v in vals)
    data_hex = ' '.join(f'{b:02X}' for b in data_bytes)
    
    try:
        cmd_hex = build_command(
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
        
        cmd_bytes = bytes.fromhex(cmd_hex)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(cmd_bytes, (GIMBAL_CONFIG['camera_ip'], GIMBAL_CONFIG['control_port']))
        print("[OK] Stop tracking command sent")
        sock.close()
        
    except Exception as e:
        print(f"[ERROR] Failed: {e}")
    
    print("\n" + "="*30 + "\n")


if __name__ == "__main__":
    # Test tracking at center
    test_loc_command()
    
    # Wait a bit
    import time
    time.sleep(2)
    
    # Test stop tracking
    test_stop_tracking()