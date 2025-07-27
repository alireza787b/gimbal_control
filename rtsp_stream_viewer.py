#!/usr/bin/env python3
"""
RTSP Stream Viewer
==================
View RTSP video stream using GStreamer pipeline or OpenCV.
Based on protocol documentation RTSP URLs.
"""

import cv2
import time
import threading
import numpy as np
from datetime import datetime
from config import GIMBAL_CONFIG, get_rtsp_url


class RTSPViewer:
    def __init__(self):
        self.camera_ip = GIMBAL_CONFIG['camera_ip']
        self.main_stream_url = get_rtsp_url("main")
        self.sub_stream_url = get_rtsp_url("sub")
        self.running = False
        self.frame = None
        self.fps = 0
        self.frame_count = 0
        self.start_time = None
        
    def test_stream_opencv(self, stream_url):
        """Test stream using OpenCV"""
        print(f"\nTesting stream with OpenCV: {stream_url}")
        
        cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
        
        if not cap.isOpened():
            print("Failed to open stream with default backend")
            
            # Try with different backends
            backends = [
                (cv2.CAP_GSTREAMER, "GStreamer"),
                (cv2.CAP_DSHOW, "DirectShow"),
                (cv2.CAP_ANY, "Any")
            ]
            
            for backend_id, backend_name in backends:
                print(f"Trying {backend_name} backend...")
                cap = cv2.VideoCapture(stream_url, backend_id)
                if cap.isOpened():
                    print(f"Success with {backend_name}!")
                    break
            else:
                print("Could not open stream with any backend")
                return False
        
        # Get stream properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        print(f"Stream opened successfully!")
        print(f"Resolution: {width}x{height}")
        print(f"FPS: {fps}")
        
        # Test reading frames
        print("\nTesting frame capture...")
        success_count = 0
        for i in range(10):
            ret, frame = cap.read()
            if ret:
                success_count += 1
        
        print(f"Successfully read {success_count}/10 frames")
        
        cap.release()
        return success_count > 0
    
    def create_gstreamer_pipeline(self, rtsp_url, latency=200):
        """Create GStreamer pipeline for RTSP"""
        # Different pipeline options
        pipelines = {
            'basic': f'rtspsrc location={rtsp_url} latency={latency} ! '
                     'rtph264depay ! h264parse ! avdec_h264 ! '
                     'videoconvert ! appsink',
            
            'optimized': f'rtspsrc location={rtsp_url} latency={latency} ! '
                         'rtph264depay ! h264parse ! avdec_h264 ! '
                         'videoscale ! video/x-raw,width=1920,height=1080 ! '
                         'videoconvert ! appsink max-buffers=1 drop=true',
            
            'gpu': f'rtspsrc location={rtsp_url} latency={latency} ! '
                   'rtph264depay ! h264parse ! nvh264dec ! '
                   'videoconvert ! appsink',
            
            'udp': f'rtspsrc location={rtsp_url} protocols=udp latency={latency} ! '
                   'rtph264depay ! h264parse ! avdec_h264 ! '
                   'videoconvert ! appsink'
        }
        
        return pipelines
    
    def view_stream_opencv(self, use_main=True):
        """View stream using OpenCV"""
        stream_url = self.main_stream_url if use_main else self.sub_stream_url
        stream_type = "Main" if use_main else "Sub"
        
        print(f"\nStarting {stream_type} stream viewer (OpenCV)")
        print(f"URL: {stream_url}")
        print("Press 'q' to quit, 's' to save snapshot")
        
        # Try direct OpenCV first
        cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
        
        if not cap.isOpened():
            print("Trying GStreamer pipeline...")
            # Try with GStreamer pipeline
            pipelines = self.create_gstreamer_pipeline(stream_url)
            
            for pipeline_name, pipeline in pipelines.items():
                print(f"Trying {pipeline_name} pipeline...")
                cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
                if cap.isOpened():
                    print(f"Success with {pipeline_name} pipeline!")
                    break
            else:
                print("Failed to open stream")
                return
        
        self.running = True
        self.start_time = time.time()
        self.frame_count = 0
        
        # Create window
        window_name = f'Gimbal {stream_type} Stream'
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        
        while self.running:
            ret, frame = cap.read()
            
            if not ret:
                print("Failed to read frame")
                time.sleep(0.1)
                continue
            
            self.frame = frame
            self.frame_count += 1
            
            # Calculate FPS
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                self.fps = self.frame_count / elapsed
            
            # Add overlay information
            overlay = frame.copy()
            self.add_overlay(overlay)
            
            # Display
            cv2.imshow(window_name, overlay)
            
            # Handle key press
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Save snapshot
                filename = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                cv2.imwrite(filename, frame)
                print(f"Saved snapshot: {filename}")
            elif key == ord('r'):
                # Toggle recording (implement if needed)
                pass
        
        self.running = False
        cap.release()
        cv2.destroyAllWindows()
    
    def add_overlay(self, frame):
        """Add overlay information to frame"""
        height, width = frame.shape[:2]
        
        # Create semi-transparent overlay
        overlay = frame.copy()
        
        # Add timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cv2.putText(overlay, timestamp, (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Add FPS
        cv2.putText(overlay, f"FPS: {self.fps:.1f}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Add resolution
        cv2.putText(overlay, f"Resolution: {width}x{height}", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Add camera info
        cv2.putText(overlay, f"Camera: {self.camera_ip}", (10, height - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Blend overlay
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
    
    def view_dual_streams(self):
        """View both main and sub streams side by side"""
        print("\nStarting dual stream viewer")
        print("Press 'q' to quit")
        
        # Open both streams
        cap_main = cv2.VideoCapture(self.main_stream_url, cv2.CAP_FFMPEG)
        cap_sub = cv2.VideoCapture(self.sub_stream_url, cv2.CAP_FFMPEG)
        
        if not cap_main.isOpened() or not cap_sub.isOpened():
            print("Failed to open one or both streams")
            return
        
        window_name = 'Gimbal Dual Stream'
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        
        while True:
            # Read frames
            ret_main, frame_main = cap_main.read()
            ret_sub, frame_sub = cap_sub.read()
            
            if not ret_main or not ret_sub:
                continue
            
            # Resize frames to same height
            height = 540  # Target height
            h1, w1 = frame_main.shape[:2]
            h2, w2 = frame_sub.shape[:2]
            
            new_w1 = int(w1 * height / h1)
            new_w2 = int(w2 * height / h2)
            
            frame_main = cv2.resize(frame_main, (new_w1, height))
            frame_sub = cv2.resize(frame_sub, (new_w2, height))
            
            # Add labels
            cv2.putText(frame_main, "Main Stream", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame_sub, "Sub Stream", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Concatenate horizontally
            combined = np.hstack([frame_main, frame_sub])
            
            cv2.imshow(window_name, combined)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap_main.release()
        cap_sub.release()
        cv2.destroyAllWindows()
    
    def stream_with_gimbal_control(self):
        """View stream with gimbal control overlay"""
        print("\nStarting stream with gimbal control")
        print("Use arrow keys to control gimbal")
        print("Press 'q' to quit")
        
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        cap = cv2.VideoCapture(self.main_stream_url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            print("Failed to open stream")
            return
        
        window_name = 'Gimbal Control Stream'
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        
        # Control state
        control_active = False
        
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            
            # Add control overlay
            if control_active:
                cv2.putText(frame, "CONTROL ACTIVE", (10, 120),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            # Add control hints
            cv2.putText(frame, "Arrow Keys: Move | Space: Stop | H: Home", 
                       (10, frame.shape[0] - 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.imshow(window_name, frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                break
            elif key == 82:  # Up arrow
                sock.sendto(b"#TPUG2wPTZ016B", (self.camera_ip, self.control_port))
                control_active = True
            elif key == 84:  # Down arrow
                sock.sendto(b"#TPUG2wPTZ026C", (self.camera_ip, self.control_port))
                control_active = True
            elif key == 81:  # Left arrow
                sock.sendto(b"#TPUG2wPTZ036D", (self.camera_ip, self.control_port))
                control_active = True
            elif key == 83:  # Right arrow
                sock.sendto(b"#TPUG2wPTZ046E", (self.camera_ip, self.control_port))
                control_active = True
            elif key == ord(' '):  # Space - stop
                sock.sendto(b"#TPUG2wPTZ006A", (self.camera_ip, self.control_port))
                control_active = False
            elif key == ord('h'):  # Home
                sock.sendto(b"#TPUG2wPTZ056F", (self.camera_ip, self.control_port))
                control_active = False
        
        sock.close()
        cap.release()
        cv2.destroyAllWindows()


def test_gstreamer_available():
    """Test if GStreamer is available"""
    try:
        # Try to create a simple GStreamer pipeline
        test_pipeline = "videotestsrc ! videoconvert ! appsink"
        cap = cv2.VideoCapture(test_pipeline, cv2.CAP_GSTREAMER)
        if cap.isOpened():
            cap.release()
            return True
    except:
        pass
    return False


def main():
    print("="*60)
    print("RTSP STREAM VIEWER")
    print("="*60)
    
    viewer = RTSPViewer()
    
    # Check GStreamer availability
    print("\nChecking GStreamer support...")
    if test_gstreamer_available():
        print("✓ GStreamer is available")
    else:
        print("✗ GStreamer not available (will use FFMPEG)")
    
    # Test streams first
    print("\nTesting stream connectivity...")
    main_ok = viewer.test_stream_opencv(viewer.main_stream_url)
    sub_ok = viewer.test_stream_opencv(viewer.sub_stream_url)
    
    if not main_ok and not sub_ok:
        print("\n✗ Could not connect to any stream")
        print("Please check:")
        print("1. Camera IP is correct")
        print("2. Camera is powered on")
        print("3. RTSP service is running")
        return
    
    print("\n" + "="*60)
    print("STREAMING OPTIONS")
    print("="*60)
    print("1. View main stream")
    print("2. View sub stream")
    print("3. View dual streams")
    print("4. Stream with gimbal control")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == '1':
        viewer.view_stream_opencv(use_main=True)
    elif choice == '2':
        viewer.view_stream_opencv(use_main=False)
    elif choice == '3':
        viewer.view_dual_streams()
    elif choice == '4':
        viewer.stream_with_gimbal_control()
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()