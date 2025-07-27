#!/usr/bin/env python3
"""
Quick Gimbal Unlock
===================
Unlock gimbal and prepare for control.
"""

import socket
import time
from config import GIMBAL_CONFIG


def unlock_gimbal():
    """Try various methods to unlock gimbal"""
    print("GIMBAL UNLOCK UTILITY")
    print("="*50)
    print("This will try to unlock the gimbal for control.\n")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.bind(('0.0.0.0', GIMBAL_CONFIG['listen_port']))
    recv_sock.settimeout(1.0)
    
    # Unlock sequence
    commands = [
        ("1. Set follow mode", b"#TPUG2wPTZ076E"),
        ("2. Lock/follow switch", b"#TPUG2wPTZ0870"),
        ("3. Enable attitude sending", b"#TPUG2wGAA0136"),
        ("4. Go to home position", b"#TPUG2wPTZ056F"),
    ]
    
    for desc, cmd in commands:
        print(f"\n{desc}...")
        sock.sendto(cmd, (GIMBAL_CONFIG['camera_ip'], GIMBAL_CONFIG['control_port']))
        
        try:
            data, _ = recv_sock.recvfrom(1024)
            print(f"  Response: {data.decode('ascii', errors='replace')}")
        except socket.timeout:
            print("  No response")
        
        time.sleep(1.0)
    
    # Test if unlocked by checking attitude
    print("\n5. Testing if gimbal responds...")
    sock.sendto(b"#TPPG2rGAC002D", (GIMBAL_CONFIG['camera_ip'], GIMBAL_CONFIG['control_port']))
    
    try:
        data, _ = recv_sock.recvfrom(1024)
        response = data.decode('ascii', errors='replace')
        if 'GAC' in response:
            print(f"  ✓ Gimbal is responding! Response: {response}")
            
            # Test movement
            print("\n6. Testing movement...")
            sock.sendto(b"#TPUG2wPTZ036D", (GIMBAL_CONFIG['camera_ip'], GIMBAL_CONFIG['control_port']))
            print("  Sent LEFT command")
            time.sleep(1.0)
            
            sock.sendto(b"#TPUG2wPTZ006A", (GIMBAL_CONFIG['camera_ip'], GIMBAL_CONFIG['control_port']))
            print("  Sent STOP command")
            
            print("\n✓ Gimbal should be unlocked now!")
            print("  Try running other scripts to control it.")
            
        else:
            print("  ✗ Invalid response")
            
    except socket.timeout:
        print("  ✗ No response - gimbal may still be locked")
    
    sock.close()
    recv_sock.close()


if __name__ == "__main__":
    unlock_gimbal()