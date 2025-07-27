#!/usr/bin/env python3
"""
Protocol Command Validator
==========================
Validate and build commands exactly according to protocol specification.
"""

import struct


def calculate_crc_manual(cmd_bytes):
    """Calculate CRC according to protocol: sum all bytes before CRC"""
    crc_sum = 0
    for byte in cmd_bytes:
        crc_sum += byte
    return crc_sum & 0xFF


def validate_command(cmd_str):
    """Validate a command string against protocol specification"""
    print(f"\nValidating command: {cmd_str}")
    print("-" * 50)
    
    # Check minimum length
    if len(cmd_str) < 10:
        print("[X] Command too short (min 10 chars)")
        return False
    
    # Check frame header
    frame_header = cmd_str[0:3]
    if frame_header not in ['#TP', '#tp', '#tP', '#Tp']:
        print(f"[X] Invalid frame header: {frame_header}")
        return False
    print(f"[OK] Frame header: {frame_header}")
    
    # Check addresses
    src_addr = cmd_str[3]
    dst_addr = cmd_str[4]
    valid_addrs = ['U', 'M', 'D', 'E', 'P', 'G']
    if src_addr not in valid_addrs or dst_addr not in valid_addrs:
        print(f"[X] Invalid addresses: {src_addr}{dst_addr}")
        return False
    print(f"[OK] Addresses: {src_addr} -> {dst_addr}")
    
    # Parse based on frame type
    if frame_header == '#TP':
        # Fixed length
        if len(cmd_str) < 12:
            print("[X] #TP command too short")
            return False
        
        length_char = cmd_str[5]
        if length_char != '2':
            print(f"[X] #TP must have length '2', got '{length_char}'")
            return False
        
        control_bit = cmd_str[6]
        identifier = cmd_str[7:10]
        data = cmd_str[10:12]
        crc_provided = cmd_str[12:14]
        
    elif frame_header == '#tp':
        # Variable length
        length_char = cmd_str[5]
        try:
            data_len = int(length_char, 16)
        except:
            print(f"[X] Invalid length character: {length_char}")
            return False
        
        if data_len > 0x0F:
            print(f"[X] Data length {data_len} exceeds max 15 for #tp")
            return False
        
        control_bit = cmd_str[6]
        identifier = cmd_str[7:10]
        
        expected_len = 10 + data_len + 2  # header(3) + addr(2) + len(1) + ctrl(1) + id(3) + data + crc(2)
        if len(cmd_str) != expected_len:
            print(f"[X] Command length mismatch. Expected {expected_len}, got {len(cmd_str)}")
            return False
        
        data = cmd_str[10:10+data_len]
        crc_provided = cmd_str[-2:]
    
    else:
        print(f"[!] Frame type {frame_header} validation not fully implemented")
        return True
    
    # Validate control bit
    if control_bit not in ['r', 'w', 'c']:
        print(f"[X] Invalid control bit: {control_bit}")
        return False
    print(f"[OK] Control bit: {control_bit} ({'read' if control_bit == 'r' else 'write'})")
    
    # Validate identifier
    if len(identifier) != 3:
        print(f"[X] Invalid identifier length: {identifier}")
        return False
    print(f"[OK] Identifier: {identifier}")
    
    # Print data
    print(f"[OK] Data: {data}")
    
    # Validate CRC
    cmd_without_crc = cmd_str[:-2]
    calculated_crc = calculate_crc_manual(cmd_without_crc.encode('ascii'))
    calculated_crc_str = f"{calculated_crc:02X}"
    
    print(f"CRC provided: {crc_provided}")
    print(f"CRC calculated: {calculated_crc_str}")
    
    if crc_provided == calculated_crc_str:
        print("[OK] CRC is valid")
        return True
    else:
        print("[X] CRC mismatch!")
        return False


def build_command_manual(frame_type, src, dst, ctrl, identifier, data=""):
    """Build command manually according to protocol specification"""
    print(f"\nBuilding command:")
    print(f"  Frame: {frame_type}")
    print(f"  Address: {src} -> {dst}")
    print(f"  Control: {ctrl}")
    print(f"  Identifier: {identifier}")
    print(f"  Data: {data}")
    
    cmd = frame_type + src + dst
    
    if frame_type == '#TP':
        cmd += '2'  # Fixed length
        cmd += ctrl
        cmd += identifier
        cmd += data.ljust(2, '0')[:2]  # Ensure 2 chars
    
    elif frame_type == '#tp':
        data_len = len(data)
        if data_len > 15:
            print("[X] Data too long for #tp frame")
            return None
        cmd += f"{data_len:X}"
        cmd += ctrl
        cmd += identifier
        cmd += data
    
    # Calculate CRC
    crc = calculate_crc_manual(cmd.encode('ascii'))
    cmd += f"{crc:02X}"
    
    print(f"Built command: {cmd}")
    return cmd


def test_known_commands():
    """Test known working commands from the logs"""
    print("\n" + "="*60)
    print("TESTING KNOWN COMMANDS")
    print("="*60)
    
    # Commands that worked in test_connection.py
    known_commands = [
        "#TPPG2rGAC002D",  # Get attitude - this worked!
        "#TPUD2wCAP013E",  # Capture
        "#TPUG2wPTZ006A",  # Stop
        "#TPUM2wZMC005C",  # Zoom stop
    ]
    
    for cmd in known_commands:
        validate_command(cmd)
    
    # Build some commands manually
    print("\n" + "="*60)
    print("BUILDING COMMANDS MANUALLY")
    print("="*60)
    
    # Build get attitude command
    cmd1 = build_command_manual('#TP', 'P', 'G', 'r', 'GAC', '00')
    if cmd1:
        validate_command(cmd1)
    
    # Build capture command
    cmd2 = build_command_manual('#TP', 'U', 'D', 'w', 'CAP', '01')
    if cmd2:
        validate_command(cmd2)


def analyze_response(response_str):
    """Analyze a response string"""
    print(f"\nAnalyzing response: {response_str}")
    print("-" * 50)
    
    if len(response_str) < 10:
        print("[X] Response too short")
        return
    
    # Basic parsing
    frame = response_str[0:3]
    addrs = response_str[3:5]
    
    print(f"Frame: {frame}")
    print(f"Addresses: {addrs[0]} -> {addrs[1]} (swapped from command)")
    
    if frame == '#tp':
        length_char = response_str[5]
        try:
            data_len = int(length_char, 16)
            print(f"Data length: {data_len}")
            
            if len(response_str) >= 10 + data_len:
                ctrl = response_str[6]
                ident = response_str[7:10]
                data = response_str[10:10+data_len]
                
                print(f"Control: {ctrl}")
                print(f"Identifier: {ident}")
                print(f"Data: {data}")
                
                # Parse specific responses
                if ident == 'GAC' and len(data) >= 12:
                    yaw_hex = data[0:4]
                    pitch_hex = data[4:8]
                    roll_hex = data[8:12]
                    
                    print("\nAttitude data:")
                    print(f"  Yaw hex: {yaw_hex}")
                    print(f"  Pitch hex: {pitch_hex}")
                    print(f"  Roll hex: {roll_hex}")
                    
                    # Convert to degrees
                    try:
                        yaw = int(yaw_hex, 16)
                        pitch = int(pitch_hex, 16)
                        roll = int(roll_hex, 16)
                        
                        # Handle signed
                        if yaw > 0x7FFF: yaw -= 0x10000
                        if pitch > 0x7FFF: pitch -= 0x10000
                        if roll > 0x7FFF: roll -= 0x10000
                        
                        print(f"  Yaw: {yaw/100.0:.2f}°")
                        print(f"  Pitch: {pitch/100.0:.2f}°")
                        print(f"  Roll: {roll/100.0:.2f}°")
                    except:
                        print("  [X] Error converting values")
                        
        except Exception as e:
            print(f"[X] Error parsing: {e}")


def main():
    print("="*60)
    print("GIMBAL PROTOCOL VALIDATOR")
    print("="*60)
    
    # Test known commands
    test_known_commands()
    
    # Analyze the successful response from earlier
    print("\n" + "="*60)
    print("ANALYZING SUCCESSFUL RESPONSE")
    print("="*60)
    
    # From the logs: #tpGPCrGACFF36ED5A0048DE
    analyze_response("#tpGPCrGACFF36ED5A0048DE")
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("\nKey findings:")
    print("1. The command #TPPG2rGAC002D works and gets attitude")
    print("2. Response format: #tpGPCrGACFF36ED5A0048DE")
    print("3. Addresses are swapped in response (GP instead of PG)")
    print("4. Attitude values are in the data portion as hex")
    print("\nIf commands are sent but don't execute:")
    print("- The gimbal might be in locked mode")
    print("- Another application might be controlling it")
    print("- The gimbal might need to be in a specific mode")


if __name__ == "__main__":
    main()