#!/usr/bin/env python3
"""
Gimbal Control Demo Script
==========================
A comprehensive demo for testing gimbal camera communication
following the SIP series protocol documentation.

Author: Your Name
Date: 2025
"""

import socket
import threading
import time
import struct
import logging
from datetime import datetime
from typing import Dict, Tuple, Optional, Any
import json

# Configure logging with detailed formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gimbal_demo.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('GimbalDemo')


class GimbalCommand:
    """Build and parse gimbal commands according to protocol specification"""
    
    @staticmethod
    def calculate_crc(command: bytes) -> int:
        """Calculate CRC checksum for command"""
        return sum(command) & 0xFF
    
    @staticmethod
    def build_command(
        frame_header: str,
        address_bit1: str,
        address_bit2: str,
        control_bit: str,
        identifier_bit: str,
        data: str = "",
        data_mode: str = 'ASCII'
    ) -> bytes:
        """
        Build a command according to protocol specification
        
        Args:
            frame_header: '#TP', '#tp', '#tP', or '#Tp'
            address_bit1: Source address (e.g., 'P' for network)
            address_bit2: Destination address (e.g., 'G' for gimbal)
            control_bit: 'r' for read, 'w' for write
            identifier_bit: 3-character command identifier
            data: Command data
            data_mode: 'ASCII' or 'Hex'
            
        Returns:
            Complete command as bytes
        """
        # Validate inputs
        if frame_header not in ('#TP', '#tp', '#tP', '#Tp'):
            raise ValueError(f"Invalid frame header: {frame_header}")
        if len(address_bit1) != 1 or len(address_bit2) != 1:
            raise ValueError("Address bits must be single characters")
        if len(identifier_bit) != 3:
            raise ValueError("Identifier must be exactly 3 characters")
        
        # Convert data based on mode
        if data_mode == 'ASCII':
            data_bytes = data.encode('ascii')
        else:  # Hex mode
            data_bytes = bytes.fromhex(data.replace(' ', ''))
        
        data_length = len(data_bytes)
        
        # Build command
        cmd = bytearray()
        cmd.extend(frame_header.encode('ascii'))
        cmd.extend(address_bit1.encode('ascii'))
        cmd.extend(address_bit2.encode('ascii'))
        
        # Handle length based on frame header
        if frame_header == '#TP':
            cmd.extend(b'2')  # Fixed length
        elif frame_header == '#tp':
            if data_length > 0x0F:
                raise ValueError("Data too long for #tp frame")
            cmd.extend(f"{data_length:X}".encode('ascii'))
        
        # Add control bit (except for #Tp)
        if frame_header != '#Tp':
            cmd.extend(control_bit.encode('ascii'))
        
        # Add identifier and data
        cmd.extend(identifier_bit.encode('ascii'))
        cmd.extend(data_bytes)
        
        # Calculate and add CRC
        crc_val = GimbalCommand.calculate_crc(cmd)
        cmd.extend(f"{crc_val:02X}".encode('ascii'))
        
        return bytes(cmd)
    
    @staticmethod
    def parse_response(response: bytes) -> Dict[str, Any]:
        """Parse gimbal response into structured data"""
        try:
            # Convert to string for easier parsing
            resp_str = response.decode('ascii', errors='ignore')
            
            # Basic parsing - extract key components
            if len(resp_str) < 10:
                return {"raw": resp_str, "error": "Response too short"}
            
            result = {
                "raw": resp_str,
                "frame_header": resp_str[0:3],
                "addresses": resp_str[3:5],
                "identifier": None,
                "data": None
            }
            
            # Extract identifier (after control bit)
            if '#tp' in resp_str or '#TP' in resp_str:
                identifier_start = 7
                result["identifier"] = resp_str[identifier_start:identifier_start+3]
                result["data"] = resp_str[identifier_start+3:-2]  # Exclude CRC
            
            return result
            
        except Exception as e:
            return {"raw": response.hex(), "error": str(e)}


class GimbalController:
    """Main controller class for gimbal communication"""
    
    def __init__(self, camera_ip: str, control_port: int = 9003, 
                 listen_port: int = 9004, timeout: float = 2.0):
        """
        Initialize gimbal controller
        
        Args:
            camera_ip: IP address of the gimbal camera
            control_port: UDP port for sending commands (default: 9003)
            listen_port: UDP port for receiving responses (default: 9004)
            timeout: Socket timeout in seconds
        """
        self.camera_ip = camera_ip
        self.control_port = control_port
        self.listen_port = listen_port
        self.timeout = timeout
        
        # Create sockets
        self.send_socket = None
        self.recv_socket = None
        self.listening = False
        self.response_buffer = {}
        self.response_lock = threading.Lock()
        
        # Statistics
        self.stats = {
            "commands_sent": 0,
            "responses_received": 0,
            "errors": 0,
            "connection_established": False
        }
        
        logger.info(f"Initialized GimbalController for {camera_ip}:{control_port}")
    
    def connect(self) -> bool:
        """
        Establish connection with gimbal camera
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Create send socket
            self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.send_socket.settimeout(self.timeout)
            
            # Create receive socket and bind to listen port
            self.recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.recv_socket.bind(('0.0.0.0', self.listen_port))
            self.recv_socket.settimeout(0.1)  # Short timeout for non-blocking
            
            # Start listener thread
            self.listening = True
            self.listener_thread = threading.Thread(
                target=self._listen_loop, 
                daemon=True
            )
            self.listener_thread.start()
            
            # Test connection with a simple command
            logger.info("Testing connection...")
            if self._test_connection():
                self.stats["connection_established"] = True
                logger.info("[OK] Connection established successfully!")
                return True
            else:
                logger.error("[X] Failed to establish connection")
                return False
                
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def _test_connection(self) -> bool:
        """Test connection by reading gimbal attitude"""
        try:
            # Send GAC (Get Attitude Command)
            response = self.send_command(
                identifier="GAC",
                address2="G",
                control="r",
                data="00"
            )
            return response is not None
        except:
            return False
    
    def _listen_loop(self):
        """Background thread to listen for responses"""
        logger.info(f"Listener started on port {self.listen_port}")
        
        while self.listening:
            try:
                data, addr = self.recv_socket.recvfrom(4096)
                self.stats["responses_received"] += 1
                
                # Parse response
                parsed = GimbalCommand.parse_response(data)
                
                # Store in buffer with timestamp
                with self.response_lock:
                    key = parsed.get("identifier", "unknown")
                    self.response_buffer[key] = {
                        "data": parsed,
                        "timestamp": time.time(),
                        "raw": data
                    }
                
                logger.debug(f"Received from {addr}: {parsed['raw']}")
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.listening:
                    logger.error(f"Listener error: {e}")
    
    def send_command(self, identifier: str, address2: str = "G", 
                     control: str = "w", data: str = "", 
                     wait_response: bool = True) -> Optional[Dict]:
        """
        Send command to gimbal and optionally wait for response
        
        Args:
            identifier: 3-character command identifier
            address2: Destination address
            control: 'r' for read, 'w' for write
            data: Command data
            wait_response: Whether to wait for response
            
        Returns:
            Response data if wait_response=True, None otherwise
        """
        try:
            # Build command
            cmd = GimbalCommand.build_command(
                frame_header='#TP' if len(data) == 2 else '#tp',
                address_bit1='P',  # Network source
                address_bit2=address2,
                control_bit=control,
                identifier_bit=identifier,
                data=data
            )
            
            # Clear response buffer for this identifier
            with self.response_lock:
                if identifier in self.response_buffer:
                    del self.response_buffer[identifier]
            
            # Send command
            self.send_socket.sendto(cmd, (self.camera_ip, self.control_port))
            self.stats["commands_sent"] += 1
            
            logger.info(f"-> Sent {identifier} command: {cmd.hex()}")
            
            # Wait for response if requested
            if wait_response:
                start_time = time.time()
                while time.time() - start_time < self.timeout:
                    with self.response_lock:
                        if identifier in self.response_buffer:
                            response = self.response_buffer[identifier]
                            logger.info(f"<- Received response: {response['data']['raw']}")
                            return response['data']
                    time.sleep(0.01)
                
                logger.warning(f"Timeout waiting for {identifier} response")
                self.stats["errors"] += 1
            
            return None
            
        except Exception as e:
            logger.error(f"Command error: {e}")
            self.stats["errors"] += 1
            return None
    
    def get_gimbal_attitude(self) -> Optional[Dict[str, float]]:
        """
        Get current gimbal attitude (yaw, pitch, roll)
        
        Returns:
            Dictionary with yaw, pitch, roll in degrees, or None on error
        """
        response = self.send_command("GAC", "G", "r", "00")
        
        if response and response.get("data"):
            try:
                # Parse attitude data (format: Y0Y1Y2Y3P0P1P2P3R0R1R2R3)
                data = response["data"]
                if len(data) >= 12:
                    # Convert hex characters to angles
                    yaw_hex = data[0:4]
                    pitch_hex = data[4:8]
                    roll_hex = data[8:12]
                    
                    # Convert to signed integers (0.01 degree units)
                    yaw_raw = int(yaw_hex, 16)
                    pitch_raw = int(pitch_hex, 16)
                    roll_raw = int(roll_hex, 16)
                    
                    # Handle signed values (two's complement)
                    if yaw_raw > 0x7FFF:
                        yaw_raw -= 0x10000
                    if pitch_raw > 0x7FFF:
                        pitch_raw -= 0x10000
                    if roll_raw > 0x7FFF:
                        roll_raw -= 0x10000
                    
                    # Convert to degrees
                    attitude = {
                        "yaw": yaw_raw / 100.0,
                        "pitch": pitch_raw / 100.0,
                        "roll": roll_raw / 100.0
                    }
                    
                    logger.info(f"Gimbal attitude: Yaw={attitude['yaw']:.2f}°, "
                              f"Pitch={attitude['pitch']:.2f}°, Roll={attitude['roll']:.2f}°")
                    
                    return attitude
                    
            except Exception as e:
                logger.error(f"Error parsing attitude data: {e}")
        
        return None
    
    def control_gimbal(self, direction: str) -> bool:
        """
        Control gimbal movement
        
        Args:
            direction: 'stop', 'up', 'down', 'left', 'right', 'home'
            
        Returns:
            True if command sent successfully
        """
        direction_codes = {
            'stop': '00',
            'up': '01',
            'down': '02',
            'left': '03',
            'right': '04',
            'home': '05'
        }
        
        if direction not in direction_codes:
            logger.error(f"Invalid direction: {direction}")
            return False
        
        response = self.send_command(
            "PTZ", "G", "w", 
            direction_codes[direction],
            wait_response=False  # PTZ commands don't typically respond
        )
        
        logger.info(f"Gimbal command sent: {direction}")
        return True
    
    def set_gimbal_speed(self, yaw_speed: float, pitch_speed: float) -> bool:
        """
        Set gimbal rotation speed
        
        Args:
            yaw_speed: Yaw speed in degrees/second (-99 to 99)
            pitch_speed: Pitch speed in degrees/second (-99 to 99)
            
        Returns:
            True if command sent successfully
        """
        # Convert to 0.1 deg/s units
        yaw_val = int(yaw_speed * 10)
        pitch_val = int(pitch_speed * 10)
        
        # Clamp to valid range
        yaw_val = max(-990, min(990, yaw_val))
        pitch_val = max(-990, min(990, pitch_val))
        
        # Convert to hex format
        yaw_hex = f"{yaw_val & 0xFFFF:04X}"
        pitch_hex = f"{pitch_val & 0xFFFF:04X}"
        
        response = self.send_command(
            "GSM", "G", "w",
            yaw_hex + pitch_hex,
            wait_response=False
        )
        
        logger.info(f"Set gimbal speed: Yaw={yaw_speed}°/s, Pitch={pitch_speed}°/s")
        return True
    
    def capture_image(self) -> bool:
        """Capture an image"""
        response = self.send_command("CAP", "D", "w", "01")
        logger.info("Image capture command sent")
        return response is not None
    
    def start_recording(self) -> bool:
        """Start video recording"""
        response = self.send_command("REC", "D", "w", "01")
        logger.info("Recording started")
        return response is not None
    
    def stop_recording(self) -> bool:
        """Stop video recording"""
        response = self.send_command("REC", "D", "w", "00")
        logger.info("Recording stopped")
        return response is not None
    
    def get_zoom_position(self) -> Optional[int]:
        """Get current zoom position"""
        response = self.send_command("ZOM", "M", "r", "00")
        
        if response and response.get("data"):
            try:
                # Parse zoom position (4 hex characters)
                zoom_hex = response["data"][0:4]
                zoom_raw = int(zoom_hex, 16)
                
                # Handle signed value
                if zoom_raw > 0x7FFF:
                    zoom_raw -= 0x10000
                
                logger.info(f"Zoom position: {zoom_raw}")
                return zoom_raw
                
            except Exception as e:
                logger.error(f"Error parsing zoom data: {e}")
        
        return None
    
    def print_statistics(self):
        """Print communication statistics"""
        print("\n" + "="*50)
        print("COMMUNICATION STATISTICS")
        print("="*50)
        print(f"Connection Status: {'[OK] Connected' if self.stats['connection_established'] else '[X] Not Connected'}")
        print(f"Commands Sent: {self.stats['commands_sent']}")
        print(f"Responses Received: {self.stats['responses_received']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"Success Rate: {(self.stats['responses_received'] / max(self.stats['commands_sent'], 1) * 100):.1f}%")
        print("="*50 + "\n")
    
    def disconnect(self):
        """Clean up and disconnect"""
        self.listening = False
        
        if self.send_socket:
            self.send_socket.close()
        if self.recv_socket:
            self.recv_socket.close()
        
        logger.info("Disconnected from gimbal")


def run_demo():
    """Run the comprehensive gimbal demo"""
    print("\n" + "="*60)
    print("GIMBAL CAMERA CONTROL DEMO")
    print("="*60)
    print(f"Starting demo at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    
    # Configuration
    CAMERA_IP = "192.168.0.118"
    
    # Create controller
    controller = GimbalController(CAMERA_IP)
    
    try:
        # Step 1: Connect to gimbal
        print("\n[1/6] ESTABLISHING CONNECTION...")
        print("-" * 40)
        if not controller.connect():
            print("[X] Failed to connect to gimbal. Please check:")
            print("   - Camera IP address is correct")
            print("   - Camera is powered on")
            print("   - Network connection is established")
            return
        print("[OK] Connection established successfully!")
        
        # Wait a moment for connection to stabilize
        time.sleep(0.5)
        
        # Step 2: Read gimbal attitude
        print("\n[2/6] READING GIMBAL TELEMETRY...")
        print("-" * 40)
        attitude = controller.get_gimbal_attitude()
        if attitude:
            print(f"[OK] Current gimbal attitude:")
            print(f"   * Yaw:   {attitude['yaw']:8.2f}°")
            print(f"   * Pitch: {attitude['pitch']:8.2f}°")
            print(f"   * Roll:  {attitude['roll']:8.2f}°")
        else:
            print("[!] Could not read gimbal attitude")
        
        # Step 3: Test gimbal movement
        print("\n[3/6] TESTING GIMBAL MOVEMENT...")
        print("-" * 40)
        movements = [
            ("Moving UP", "up", 1.0),
            ("Moving DOWN", "down", 1.0),
            ("Moving LEFT", "left", 1.0),
            ("Moving RIGHT", "right", 1.0),
            ("Stopping", "stop", 0.5),
            ("Returning HOME", "home", 2.0)
        ]
        
        for description, direction, duration in movements:
            print(f"   * {description}...", end='', flush=True)
            controller.control_gimbal(direction)
            time.sleep(duration)
            print(" [OK]")
        
        print("[OK] Gimbal movement test completed!")
        
        # Step 4: Test speed control
        print("\n[4/6] TESTING SPEED CONTROL...")
        print("-" * 40)
        print("   * Setting slow speed (5°/s)...", end='', flush=True)
        controller.set_gimbal_speed(5.0, 5.0)
        controller.control_gimbal("right")
        time.sleep(1.0)
        controller.control_gimbal("stop")
        print(" [OK]")
        
        print("   * Setting fast speed (20°/s)...", end='', flush=True)
        controller.set_gimbal_speed(20.0, 20.0)
        controller.control_gimbal("left")
        time.sleep(1.0)
        controller.control_gimbal("stop")
        print(" [OK]")
        
        print("[OK] Speed control test completed!")
        
        # Step 5: Test camera functions
        print("\n[5/6] TESTING CAMERA FUNCTIONS...")
        print("-" * 40)
        
        # Get zoom position
        print("   * Reading zoom position...", end='', flush=True)
        zoom_pos = controller.get_zoom_position()
        if zoom_pos is not None:
            print(f" [OK] (Position: {zoom_pos})")
        else:
            print(" [!] Could not read")
        
        # Capture image
        print("   * Capturing image...", end='', flush=True)
        if controller.capture_image():
            print(" [OK]")
        else:
            print(" [!] No response")
        
        # Test recording
        print("   * Starting recording...", end='', flush=True)
        if controller.start_recording():
            print(" [OK]")
            time.sleep(2.0)
            print("   * Stopping recording...", end='', flush=True)
            if controller.stop_recording():
                print(" [OK]")
            else:
                print(" [!] No response")
        else:
            print(" [!] No response")
        
        print("[OK] Camera function tests completed!")
        
        # Step 6: Final attitude reading
        print("\n[6/6] FINAL TELEMETRY CHECK...")
        print("-" * 40)
        final_attitude = controller.get_gimbal_attitude()
        if final_attitude:
            print(f"[OK] Final gimbal attitude:")
            print(f"   * Yaw:   {final_attitude['yaw']:8.2f}°")
            print(f"   * Pitch: {final_attitude['pitch']:8.2f}°")
            print(f"   * Roll:  {final_attitude['roll']:8.2f}°")
        
    except KeyboardInterrupt:
        print("\n\n[!] Demo interrupted by user")
    except Exception as e:
        print(f"\n\n[X] Demo error: {e}")
        logger.exception("Demo error")
    finally:
        # Print statistics
        controller.print_statistics()
        
        # Disconnect
        controller.disconnect()
        print("\n[OK] Demo completed successfully!")
        print(f"   Log file: gimbal_demo.log")
        print(f"   Ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")


if __name__ == "__main__":
    run_demo()