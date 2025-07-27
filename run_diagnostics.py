#!/usr/bin/env python3
"""
Gimbal System Diagnostics
=========================
Run complete diagnostics and provide recommendations.
"""

import subprocess
import socket
import time
from config import GIMBAL_CONFIG
from gimbalcmdparse import build_command


def test_network_connectivity():
    """Test basic network connectivity"""
    print("\n1. NETWORK CONNECTIVITY TEST")
    print("-" * 40)
    
    # Ping test
    try:
        result = subprocess.run(
            ['ping', '-n', '1', GIMBAL_CONFIG['camera_ip']], 
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"[OK] Can ping {GIMBAL_CONFIG['camera_ip']}")
            return True
        else:
            print(f"[X] Cannot ping {GIMBAL_CONFIG['camera_ip']}")
            return False
    except:
        print("[!] Ping test failed (may need admin rights)")
        return None


def test_udp_ports():
    """Test UDP port availability"""
    print("\n2. UDP PORT TEST")
    print("-" * 40)
    
    ports_ok = True
    
    # Test control port (sending)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.close()
        print(f"[OK] Can create UDP socket for sending")
    except:
        print(f"[X] Cannot create UDP socket")
        ports_ok = False
    
    # Test listen port (receiving)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', GIMBAL_CONFIG['listen_port']))
        sock.close()
        print(f"[OK] Port {GIMBAL_CONFIG['listen_port']} is available for listening")
    except:
        print(f"[X] Port {GIMBAL_CONFIG['listen_port']} is in use or blocked")
        ports_ok = False
    
    return ports_ok


def test_gimbal_communication():
    """Test basic gimbal communication"""
    print("\n3. GIMBAL COMMUNICATION TEST")
    print("-" * 40)
    
    try:
        # Create sockets
        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.bind(('0.0.0.0', GIMBAL_CONFIG['listen_port']))
        recv_sock.settimeout(2.0)
        
        # Build test command (get attitude)
        cmd = build_command(
            frame_header='#TP',
            address_bit1='P',
            address_bit2='G',
            control_bit='r',
            identifier_bit='GAC',
            data='00',
            output_format='ASCII'
        )
        
        # Send command
        send_sock.sendto(cmd.encode(), 
                        (GIMBAL_CONFIG['camera_ip'], GIMBAL_CONFIG['control_port']))
        
        # Wait for response
        try:
            data, addr = recv_sock.recvfrom(1024)
            print(f"[OK] Received response from {addr}")
            print(f"     Response: {data.decode('ascii', errors='ignore')}")
            
            # Parse attitude
            if b'GAC' in data:
                print("[OK] Valid attitude response received")
                return True
            else:
                print("[!] Response received but format unexpected")
                return False
                
        except socket.timeout:
            print("[X] No response received (timeout)")
            return False
            
    except Exception as e:
        print(f"[X] Communication error: {e}")
        return False
    finally:
        send_sock.close()
        recv_sock.close()


def test_ffmpeg_installation():
    """Check if ffmpeg is installed"""
    print("\n4. FFMPEG INSTALLATION TEST")
    print("-" * 40)
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("[OK] ffmpeg is installed")
            return True
        else:
            print("[X] ffmpeg error")
            return False
    except FileNotFoundError:
        print("[X] ffmpeg not found")
        print("    -> SEI telemetry parsing will not work")
        print("    -> Install from: https://ffmpeg.org/download.html")
        return False


def test_python_packages():
    """Test required Python packages"""
    print("\n5. PYTHON PACKAGES TEST")
    print("-" * 40)
    
    packages_ok = True
    
    # Test OpenCV
    try:
        import cv2
        print(f"[OK] OpenCV installed (version: {cv2.__version__})")
    except ImportError:
        print("[X] OpenCV not installed")
        print("    -> Run: pip install opencv-python")
        packages_ok = False
    
    # Test numpy
    try:
        import numpy
        print(f"[OK] NumPy installed (version: {numpy.__version__})")
    except ImportError:
        print("[X] NumPy not installed")
        print("    -> Run: pip install numpy")
        packages_ok = False
    
    return packages_ok


def main():
    """Run all diagnostics"""
    print("="*60)
    print("GIMBAL CONTROL SYSTEM DIAGNOSTICS")
    print("="*60)
    print(f"Camera IP: {GIMBAL_CONFIG['camera_ip']}")
    print(f"Control Port: {GIMBAL_CONFIG['control_port']}")
    print(f"Listen Port: {GIMBAL_CONFIG['listen_port']}")
    
    # Run tests
    results = {
        "network": test_network_connectivity(),
        "ports": test_udp_ports(),
        "communication": test_gimbal_communication(),
        "ffmpeg": test_ffmpeg_installation(),
        "packages": test_python_packages()
    }
    
    # Summary
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    
    all_ok = True
    for test, result in results.items():
        status = "[OK]" if result else "[X]"
        print(f"{status} {test.upper()}")
        if not result:
            all_ok = False
    
    print("\n" + "="*60)
    print("RECOMMENDATIONS")
    print("="*60)
    
    if all_ok:
        print("[OK] All tests passed! System is ready.")
        print("\nYou can now run:")
        print("  - python gimbal_demo.py        (full demo)")
        print("  - python monitor.py            (real-time monitoring)")
        print("  - python tracking_demo.py      (object tracking)")
        print("  - python telemetry_reader.py   (telemetry without ffmpeg)")
    else:
        print("Please fix the following issues:\n")
        
        if not results["network"]:
            print("1. Network Connection:")
            print("   - Check camera IP address in config.py")
            print("   - Verify camera is powered on")
            print("   - Check network cable/connection")
        
        if not results["ports"]:
            print("\n2. UDP Ports:")
            print("   - Close any applications using port 9004")
            print("   - Check firewall settings")
            print("   - Try running as administrator")
        
        if not results["communication"]:
            print("\n3. Gimbal Communication:")
            print("   - Verify camera firmware supports this protocol")
            print("   - Check if another application is controlling the gimbal")
            print("   - Try power cycling the camera")
        
        if not results["ffmpeg"]:
            print("\n4. FFmpeg (optional for SEI telemetry):")
            print("   - Download from: https://ffmpeg.org/download.html")
            print("   - Add to system PATH")
            print("   - Or use: winget install ffmpeg")
        
        if not results["packages"]:
            print("\n5. Python Packages:")
            print("   - Run: pip install opencv-python numpy")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()