#!/usr/bin/env python3
"""
Simple Gimbal Test
==================
Minimal test using exact working command from logs.
"""

import socket
import time


def test_gimbal():
    """Simple test with known working command"""
    
    # Configuration
    CAMERA_IP = "192.168.0.108"
    SEND_PORT = 9003
    RECV_PORT = 9004
    
    print("Simple Gimbal Communication Test")
    print("="*40)
    print(f"Camera: {CAMERA_IP}:{SEND_PORT}")
    print(f"Listen: 0.0.0.0:{RECV_PORT}")
    print("="*40)
    
    # Create sockets
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        # Bind receive socket
        recv_sock.bind(('0.0.0.0', RECV_PORT))
        recv_sock.settimeout(3.0)
        print(f"✓ Listening on port {RECV_PORT}")
        
        # The exact command that worked before
        cmd = b"#TPPG2rGAC002D"
        
        print(f"\nSending command: {cmd.decode('ascii')}")
        print(f"Hex: {cmd.hex()}")
        
        # Send command
        bytes_sent = send_sock.sendto(cmd, (CAMERA_IP, SEND_PORT))
        print(f"✓ Sent {bytes_sent} bytes")
        
        # Wait for response
        print("\nWaiting for response...")
        start_time = time.time()
        
        try:
            data, addr = recv_sock.recvfrom(1024)
            elapsed = time.time() - start_time
            
            print(f"\n✓ SUCCESS! Response received in {elapsed:.3f} seconds")
            print(f"From: {addr}")
            print(f"Raw bytes: {data}")
            print(f"Hex: {data.hex()}")
            print(f"ASCII: {data.decode('ascii', errors='replace')}")
            
            # Parse response
            if b'GAC' in data and len(data) > 20:
                resp_str = data.decode('ascii', errors='replace')
                idx = resp_str.find('GAC') + 3
                
                if idx + 12 <= len(resp_str):
                    yaw_hex = resp_str[idx:idx+4]
                    pitch_hex = resp_str[idx+4:idx+8]
                    roll_hex = resp_str[idx+8:idx+12]
                    
                    print(f"\nParsed attitude data:")
                    print(f"  Yaw hex: {yaw_hex}")
                    print(f"  Pitch hex: {pitch_hex}")
                    print(f"  Roll hex: {roll_hex}")
                    
                    # Convert to degrees
                    try:
                        yaw = int(yaw_hex, 16)
                        pitch = int(pitch_hex, 16)
                        roll = int(roll_hex, 16)
                        
                        # Handle signed values
                        if yaw > 0x7FFF: yaw -= 0x10000
                        if pitch > 0x7FFF: pitch -= 0x10000
                        if roll > 0x7FFF: roll -= 0x10000
                        
                        print(f"\nGimbal attitude:")
                        print(f"  Yaw:   {yaw/100.0:7.2f}°")
                        print(f"  Pitch: {pitch/100.0:7.2f}°")
                        print(f"  Roll:  {roll/100.0:7.2f}°")
                        
                        return True
                        
                    except Exception as e:
                        print(f"Error converting values: {e}")
            
        except socket.timeout:
            print("\n✗ TIMEOUT - No response received")
            print("\nPossible issues:")
            print("1. Wrong IP address (check camera is at 192.168.0.108)")
            print("2. Firewall blocking UDP traffic")
            print("3. Camera not powered on or in standby mode")
            print("4. Another application using port 9004")
            return False
            
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        return False
        
    finally:
        send_sock.close()
        recv_sock.close()


def test_movement():
    """Test simple movement command"""
    print("\n" + "="*40)
    print("Testing Movement Command")
    print("="*40)
    
    CAMERA_IP = "192.168.0.108"
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Movement commands (no response expected)
    commands = [
        ("Move LEFT", b"#TPUG2wPTZ036D"),
        ("Wait", None, 1.0),
        ("STOP", b"#TPUG2wPTZ006A"),
    ]
    
    for item in commands:
        if item[1] is None:
            print(f"Waiting {item[2]} seconds...")
            time.sleep(item[2])
        else:
            desc, cmd = item[0], item[1]
            print(f"\nSending: {desc}")
            print(f"Command: {cmd.decode('ascii')}")
            sock.sendto(cmd, (CAMERA_IP, 9003))
            print("✓ Sent")
            time.sleep(0.5)
    
    sock.close()
    print("\nMovement test complete.")
    print("Check if gimbal moved left then stopped.")


def main():
    print("GIMBAL SIMPLE TEST")
    print("="*50)
    print("This uses the exact command that worked before.\n")
    
    # Test basic communication
    success = test_gimbal()
    
    if success:
        print("\n✓ Communication is working!")
        
        # Ask if user wants to test movement
        response = input("\nTest movement commands? (y/n): ")
        if response.lower() == 'y':
            test_movement()
    else:
        print("\n✗ Communication failed.")
        print("\nPlease check:")
        print("1. Camera IP is 192.168.0.108")
        print("2. Camera is powered on")
        print("3. No firewall blocking UDP 9003/9004")
        print("4. No other app using these ports")


if __name__ == "__main__":
    main()