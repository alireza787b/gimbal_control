"""
Gimbal Command Parser Module
============================
Provides utilities for building and parsing gimbal commands
according to the SIP series protocol specification.

This module is imported by other scripts for command construction.
"""

import re
import struct
from typing import Union, Tuple


def validate_hex_input(data: str) -> None:
    """
    Validate hexadecimal input string
    
    Args:
        data: Hex string to validate
        
    Raises:
        ValueError: If hex string is invalid
    """
    if ' ' in data:
        # Space-separated hex bytes
        pattern = r'^(?:[0-9A-Fa-f]{1,2}\s*)+$'
        if not re.fullmatch(pattern, data):
            raise ValueError("Invalid hex string. Bytes must be 1-2 hex digits separated by spaces.")
    else:
        # Continuous hex string
        if len(data) % 2 != 0 or not re.fullmatch(r'^[0-9A-Fa-f]+$', data):
            raise ValueError("Invalid hex string. Continuous hex must be even length and only 0-9a-f.")


def calculate_crc(command: bytes) -> int:
    """
    Calculate CRC checksum for command
    
    Args:
        command: Command bytes to calculate CRC for
        
    Returns:
        CRC value (0-255)
    """
    return sum(command) & 0xFF


def build_command(
    frame_header: str,
    address_bit1: str,
    address_bit2: str,
    control_bit: str,
    identifier_bit: str,
    data: str,
    data_mode: str = 'ASCII',
    input_space_separate: bool = False,
    output_format: str = 'ASCII',
    output_space_separate: bool = False
) -> str:
    """
    Assemble a command string according to protocol specification.

    Parameters:
        frame_header: One of '#TP', '#tp', '#tP', '#Tp'
                     - '#TP': Fixed length command (2 bytes data)
                     - '#tp': Variable length (max 15 bytes)
                     - '#tP': Extended command (max 255 bytes)
                     - '#Tp': Extended hex format (max 65535 bytes)
        address_bit1: Single letter source code (e.g., 'P' for network, 'U' for UART)
        address_bit2: Single letter destination code:
                     - 'M': Lens
                     - 'D': System and Image
                     - 'E': Auxiliary Equipment
                     - 'G': Gimbal
                     - 'P': Network
        control_bit: 'w' for write or 'r' for read (empty when frame_header='#Tp')
        identifier_bit: Three-character command identifier (e.g., 'PTZ', 'GAC', 'REC')
        data: Payload string, ASCII or hex format
        data_mode: 'ASCII' or 'Hex'
        input_space_separate: Whether hex input is space-separated
        output_format: 'ASCII' or 'Hex' for output format
        output_space_separate: Whether to insert spaces in hex output

    Returns:
        The assembled command as a string in ASCII or hex form.

    Raises:
        ValueError: On invalid parameters or data.
    """
    # Validate frame header
    if frame_header not in ('#TP', '#tp', '#tP', '#Tp'):
        raise ValueError(f"Unsupported frame header: {frame_header}")
    
    # Validate addresses
    if len(address_bit1) != 1 or len(address_bit2) != 1:
        raise ValueError("Address bits must be single characters.")
    
    # Validate identifier
    if len(identifier_bit) != 3:
        raise ValueError("Identifier bit must be exactly 3 characters.")
    
    # Convert data based on mode
    if data_mode == 'ASCII':
        data_bytes = data.encode('ascii')
    elif data_mode == 'Hex':
        if input_space_separate:
            validate_hex_input(data)
            data_bytes = bytes(int(b, 16) for b in data.split())
        else:
            validate_hex_input(data)
            data_bytes = bytes.fromhex(data)
    else:
        raise ValueError(f"Unsupported data_mode: {data_mode}")
    
    data_length = len(data_bytes)
    
    # Determine length bytes based on frame header
    if frame_header == '#TP':
        # Fixed length command
        length_bytes = b'2'
        cb = control_bit
    elif frame_header == '#tp':
        # Variable length, max 15 bytes
        if data_length > 0x0F:
            raise ValueError("Data length exceeds maximum for #tp (15 bytes).")
        length_bytes = f"{data_length:X}".encode('ascii')
        cb = control_bit
    elif frame_header == '#tP':
        # Extended command, max 255 bytes
        if data_length > 0xFF:
            raise ValueError("Data length exceeds maximum for #tP (255 bytes).")
        length_bytes = data_length.to_bytes(1, 'big')
        cb = control_bit
    elif frame_header == '#Tp':
        # Extended hex format, max 65535 bytes
        if data_length > 0xFFFF:
            raise ValueError("Data length exceeds maximum for #Tp (65535 bytes).")
        length_bytes = data_length.to_bytes(2, 'big')
        cb = ''  # No control bit for #Tp
    
    # Build command
    cmd = bytearray()
    cmd.extend(frame_header.encode('ascii'))
    cmd.extend(address_bit1.encode('ascii'))
    cmd.extend(address_bit2.encode('ascii'))
    cmd.extend(length_bytes)
    
    # Add control bit if applicable
    if cb:
        cmd.extend(cb.encode('ascii'))
    
    # Add identifier and data
    cmd.extend(identifier_bit.encode('ascii'))
    cmd.extend(data_bytes)
    
    # Calculate and add CRC
    crc_val = calculate_crc(cmd)
    cmd.extend(f"{crc_val:02X}".encode('ascii'))
    
    # Format output
    if output_format == 'ASCII':
        try:
            return cmd.decode('ascii')
        except UnicodeDecodeError:
            raise ValueError("Command contains non-ASCII bytes; choose hex output.")
    elif output_format == 'Hex':
        hexstr = cmd.hex().upper()
        if output_space_separate:
            return ' '.join(hexstr[i:i+2] for i in range(0, len(hexstr), 2))
        return hexstr
    else:
        raise ValueError(f"Unsupported output_format: {output_format}")


def parse_command_response(response: bytes) -> dict:
    """
    Parse a command response from the gimbal
    
    Args:
        response: Raw response bytes
        
    Returns:
        Dictionary containing parsed response components
    """
    try:
        # Try ASCII decode first
        resp_str = response.decode('ascii', errors='ignore')
        
        result = {
            "raw_bytes": response,
            "raw_string": resp_str,
            "frame_header": None,
            "addresses": None,
            "length": None,
            "control": None,
            "identifier": None,
            "data": None,
            "crc": None,
            "valid": False
        }
        
        # Basic validation
        if len(resp_str) < 10:
            result["error"] = "Response too short"
            return result
        
        # Parse frame header
        if resp_str.startswith(('#TP', '#tp', '#tP', '#Tp')):
            result["frame_header"] = resp_str[0:3]
            result["addresses"] = resp_str[3:5]
            
            # Parse based on frame type
            if result["frame_header"] == '#TP':
                # Fixed length format
                result["length"] = 2
                result["control"] = resp_str[6]
                result["identifier"] = resp_str[7:10]
                result["data"] = resp_str[10:-2]
                result["crc"] = resp_str[-2:]
            elif result["frame_header"] == '#tp':
                # Variable length format
                length_char = resp_str[5]
                result["length"] = int(length_char, 16) if length_char.isdigit() or length_char in 'ABCDEFabcdef' else 0
                result["control"] = resp_str[6]
                result["identifier"] = resp_str[7:10]
                result["data"] = resp_str[10:10+result["length"]]
                result["crc"] = resp_str[-2:]
            
            # Validate CRC if possible
            try:
                cmd_part = response[:-2]
                calculated_crc = calculate_crc(cmd_part)
                provided_crc = int(result["crc"], 16)
                result["valid"] = calculated_crc == provided_crc
            except:
                pass
        
        return result
        
    except Exception as e:
        return {
            "raw_bytes": response,
            "error": str(e),
            "valid": False
        }


# Utility functions for specific data types
def pack_int16(value: int) -> bytes:
    """Pack a signed 16-bit integer in little-endian format"""
    return struct.pack('<h', value)


def pack_uint16(value: int) -> bytes:
    """Pack an unsigned 16-bit integer in little-endian format"""
    return struct.pack('<H', value)


def pack_uint32(value: int) -> bytes:
    """Pack an unsigned 32-bit integer in little-endian format"""
    return struct.pack('<I', value)


def unpack_int16(data: bytes, offset: int = 0) -> int:
    """Unpack a signed 16-bit integer from little-endian bytes"""
    return struct.unpack_from('<h', data, offset)[0]


def unpack_uint16(data: bytes, offset: int = 0) -> int:
    """Unpack an unsigned 16-bit integer from little-endian bytes"""
    return struct.unpack_from('<H', data, offset)[0]


def unpack_uint32(data: bytes, offset: int = 0) -> int:
    """Unpack an unsigned 32-bit integer from little-endian bytes"""
    return struct.unpack_from('<I', data, offset)[0]