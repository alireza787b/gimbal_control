#!/usr/bin/env python3
"""
Test SEI and RTSP Connection
=============================
Diagnostic script to test RTSP streaming and ffmpeg availability.
"""

import subprocess
import cv2
import socket
from config import GIMBAL_CONFIG, get_rtsp_url


def test_ffmpeg():
    """Test if ffmpeg is installed and accessible"""
    print("\n=== TESTING FFMPEG ===")
    print("-" * 30)
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("[OK] ffmpeg is installed")
            version_line = result.stdout.split('\n')[0]
            print(f"Version: {version_line}")
            return True
        else:
            print("[X] ffmpeg returned error")
            return False
    except FileNotFoundError:
        print("[X] ffmpeg not found in PATH")
        print("\nTo install ffmpeg:")
        print("1. Download from: https://ffmpeg.org/download.html")
        print("2. Extract and add to system PATH")
        print("3. Or use: winget install ffmpeg (on Windows)")
        return False
    except Exception as e:
        print(f"[X] Error testing ffmpeg: {e}")
        return False


def test_rtsp_connection():
    """Test RTSP port connectivity"""
    print("\n=== TESTING RTSP CONNECTION ===")
    print("-" * 30)
    
    # Test TCP connection to RTSP port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2.0)
    
    try:
        result = sock.connect_ex((GIMBAL_CONFIG['camera_ip'], 554))
        if result == 0:
            print(f"[OK] RTSP port 554 is open on {GIMBAL_CONFIG['camera_ip']}")
            return True
        else:
            print(f"[X] Cannot connect to RTSP port 554 on {GIMBAL_CONFIG['camera_ip']}")
            return False
    except Exception as e:
        print(f"[X] Connection error: {e}")
        return False
    finally:
        sock.close()


def test_rtsp_stream():
    """Test RTSP stream with OpenCV"""
    print("\n=== TESTING RTSP STREAM ===")
    print("-" * 30)
    
    rtsp_url = get_rtsp_url("main")
    print(f"Testing: {rtsp_url}")
    
    try:
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        
        if not cap.isOpened():
            print("[X] Cannot open RTSP stream")
            print("\nPossible issues:")
            print("1. Wrong IP address or camera offline")
            print("2. RTSP service not running on camera")
            print("3. Network/firewall blocking connection")
            return False
        
        # Try to read a frame
        ret, frame = cap.read()
        if ret and frame is not None:
            height, width = frame.shape[:2]
            print(f"[OK] Stream is working! Resolution: {width}x{height}")
            
            # Get stream properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            print(f"FPS: {fps}")
            
            cap.release()
            return True
        else:
            print("[X] Cannot read frames from stream")
            cap.release()
            return False
            
    except Exception as e:
        print(f"[X] Error testing stream: {e}")
        return False


def test_stream_with_ffmpeg():
    """Test RTSP stream directly with ffmpeg"""
    print("\n=== TESTING STREAM WITH FFMPEG ===")
    print("-" * 30)
    
    rtsp_url = get_rtsp_url("main")
    
    # Try both h264 and h265
    for codec in ['h264', 'h265']:
        print(f"\nTesting {codec} codec...")
        
        if codec == 'h264':
            cmd = [
                'ffmpeg', '-rtsp_transport', 'udp', '-i', rtsp_url,
                '-frames:v', '10',  # Only process 10 frames
                '-f', 'null', '-'
            ]
        else:
            cmd = [
                'ffmpeg', '-rtsp_transport', 'udp', '-i', rtsp_url,
                '-c:v', 'hevc',
                '-frames:v', '10',
                '-f', 'null', '-'
            ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            # Check stderr for codec information
            if 'Video:' in result.stderr:
                for line in result.stderr.split('\n'):
                    if 'Video:' in line:
                        print(f"[OK] Found video stream: {line.strip()}")
                        # Try to detect actual codec
                        if 'h264' in line.lower():
                            print("  -> Detected H.264 codec")
                            return 'h264'
                        elif 'hevc' in line.lower() or 'h265' in line.lower():
                            print("  -> Detected H.265/HEVC codec")
                            return 'h265'
            else:
                print(f"[X] No video stream found for {codec}")
                
        except subprocess.TimeoutExpired:
            print(f"[X] Timeout testing {codec}")
        except Exception as e:
            print(f"[X] Error: {e}")
    
    return None


def main():
    """Run all tests"""
    print("="*50)
    print("GIMBAL SEI/RTSP DIAGNOSTIC TEST")
    print("="*50)
    
    # Test ffmpeg
    ffmpeg_ok = test_ffmpeg()
    
    # Test RTSP connection
    rtsp_ok = test_rtsp_connection()
    
    # Test RTSP stream
    if rtsp_ok:
        stream_ok = test_rtsp_stream()
        
        # Test with ffmpeg if available
        if ffmpeg_ok and stream_ok:
            detected_codec = test_stream_with_ffmpeg()
            if detected_codec:
                print(f"\n[RECOMMENDATION] Use codec='{detected_codec}' for SEI parsing")
    
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"ffmpeg available: {'Yes' if ffmpeg_ok else 'No'}")
    print(f"RTSP port open: {'Yes' if rtsp_ok else 'No'}")
    
    if not ffmpeg_ok:
        print("\n[ACTION REQUIRED] Install ffmpeg to enable SEI telemetry parsing")
    
    if not rtsp_ok:
        print("\n[ACTION REQUIRED] Check camera connection and RTSP service")


if __name__ == "__main__":
    main()