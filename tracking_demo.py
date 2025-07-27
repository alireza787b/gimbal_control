#!/usr/bin/env python3
"""
Gimbal Object Tracking Demo
===========================
Demonstrates object tracking functionality using LOC commands.
"""

import socket
import struct
import time
import logging
from gimbalcmdparse import build_command
from config import GIMBAL_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('TrackingDemo')


class TrackingController:
    """Controller for gimbal tracking operations"""
    
    def __init__(self, camera_ip: str, control_port: int = 9003):
        self.camera_ip = camera_ip
        self.control_port = control_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
    def start_tracking(self, x: int, y: int, width: int = 64, height: int = 64,
                      preview_width: int = 1920, preview_height: int = 1080):
        """
        Start tracking an object at specified coordinates
        
        Args:
            x: X coordinate of object center in preview
            y: Y coordinate of object center in preview
            width: Object width in pixels
            height: Object height in pixels
            preview_width: Preview resolution width (default 1920)
            preview_height: Preview resolution height (default 1080)
        """
        # Convert preview coordinates to protocol values
        param_x = round(2000 * x / preview_width - 1000)
        param_y = round(2000 * y / preview_height - 1000)
        param_w = round(2000 * width / preview_width)
        param_h = round(2000 * height / preview_height)
        
        # Blur click enabled (8) or disabled (0)
        blur_click = 8  # Enable blur click for better tracking
        
        logger.info(f"Starting tracking at ({x},{y}) with size {width}x{height}")
        logger.info(f"Protocol values: x={param_x}, y={param_y}, w={param_w}, h={param_h}")
        
        # Pack parameters as big-endian signed 16-bit integers
        vals = (param_x, param_y, param_w, param_h, blur_click)
        data_bytes = b''.join(struct.pack('>h', v) for v in vals)
        data_hex = ' '.join(f'{b:02X}' for b in data_bytes)
        
        # Build LOC command
        cmd = build_command(
            frame_header='#tp',
            address_bit1='P',      # Network source
            address_bit2='D',      # System/Image destination
            control_bit='w',       # Write command
            identifier_bit='LOC',  # Location/tracking command
            data=data_hex,
            data_mode='Hex',
            input_space_separate=True,
            output_format='Hex',
            output_space_separate=False
        )
        
        # Send command
        cmd_bytes = bytes.fromhex(cmd)
        self.sock.sendto(cmd_bytes, (self.camera_ip, self.control_port))
        logger.info(f"Tracking command sent (hex): {cmd}")
        
    def stop_tracking(self):
        """Stop object tracking"""
        # Send tracking command with zero size to stop
        self.start_tracking(0, 0, 0, 0)
        logger.info("Tracking stopped")
        
    def track_center(self):
        """Start tracking object at center of frame"""
        self.start_tracking(960, 540, 100, 100)
        logger.info("Tracking center of frame")


def demo_tracking():
    """Run tracking demonstration"""
    print("\n=== GIMBAL TRACKING DEMO ===")
    print("-" * 30)
    
    tracker = TrackingController(
        GIMBAL_CONFIG['camera_ip'],
        GIMBAL_CONFIG['control_port']
    )
    
    try:
        # Demo 1: Track center of screen
        print("\n1. Tracking center of screen...")
        tracker.track_center()
        time.sleep(3)
        
        # Demo 2: Track custom positions
        positions = [
            (480, 270, "top-left quadrant"),
            (1440, 270, "top-right quadrant"),
            (1440, 810, "bottom-right quadrant"),
            (480, 810, "bottom-left quadrant"),
            (960, 540, "center")
        ]
        
        print("\n2. Tracking different positions...")
        for x, y, desc in positions:
            print(f"   Tracking {desc} ({x},{y})...")
            tracker.start_tracking(x, y, 80, 80)
            time.sleep(2)
        
        # Demo 3: Different object sizes
        print("\n3. Testing different tracking box sizes...")
        sizes = [(50, 50), (100, 100), (150, 150), (200, 200)]
        for w, h in sizes:
            print(f"   Tracking with size {w}x{h}...")
            tracker.start_tracking(960, 540, w, h)
            time.sleep(2)
        
        # Stop tracking
        print("\n4. Stopping tracking...")
        tracker.stop_tracking()
        
        print("\n✅ Tracking demo completed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Tracking demo error")
    finally:
        tracker.sock.close()


def interactive_tracking():
    """Interactive tracking mode - click coordinates to track"""
    print("\n=== INTERACTIVE TRACKING MODE ===")
    print("Enter coordinates to track, or 'q' to quit")
    print("Format: x y [width] [height]")
    print("Example: 960 540 100 100")
    print("-" * 30)
    
    tracker = TrackingController(
        GIMBAL_CONFIG['camera_ip'],
        GIMBAL_CONFIG['control_port']
    )
    
    try:
        while True:
            user_input = input("\nEnter coordinates: ").strip()
            
            if user_input.lower() == 'q':
                print("Stopping tracking and exiting...")
                tracker.stop_tracking()
                break
            
            try:
                parts = user_input.split()
                if len(parts) >= 2:
                    x = int(parts[0])
                    y = int(parts[1])
                    width = int(parts[2]) if len(parts) > 2 else 100
                    height = int(parts[3]) if len(parts) > 3 else 100
                    
                    if 0 <= x <= 1920 and 0 <= y <= 1080:
                        tracker.start_tracking(x, y, width, height)
                        print(f"✓ Tracking started at ({x},{y}) with size {width}x{height}")
                    else:
                        print("❌ Coordinates out of range (0-1920, 0-1080)")
                else:
                    print("❌ Please enter at least x and y coordinates")
                    
            except ValueError:
                print("❌ Invalid input. Please enter numbers only.")
                
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        tracker.stop_tracking()
    finally:
        tracker.sock.close()
        print("\nTracking session ended.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        interactive_tracking()
    else:
        demo_tracking()