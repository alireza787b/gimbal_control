#!/usr/bin/env python3
"""
Interactive Command Reference
=============================
Quick reference and testing for gimbal commands.
Based on protocol documentation.
"""

import socket
from config import GIMBAL_CONFIG


class CommandReference:
    def __init__(self):
        self.camera_ip = GIMBAL_CONFIG['camera_ip']
        self.control_port = GIMBAL_CONFIG['control_port']
        
        # Command database from protocol
        self.commands = {
            'GIMBAL_CONTROL': {
                'Stop': b'#TPUG2wPTZ006A',
                'Up': b'#TPUG2wPTZ016B',
                'Down': b'#TPUG2wPTZ026C',
                'Left': b'#TPUG2wPTZ036D',
                'Right': b'#TPUG2wPTZ046E',
                'Home': b'#TPUG2wPTZ056F',
                'Lock Mode': b'#TPUG2wPTZ066F',
                'Follow Mode': b'#TPUG2wPTZ076E',
                'Lock/Follow Switch': b'#TPUG2wPTZ0870',
                'Calibrate': b'#TPUG2wPTZ0971',
                'One Button Down': b'#TPUG2wPTZ0A71'
            },
            'GIMBAL_QUERY': {
                'Get Attitude (Magnetic)': b'#TPPG2rGAC002D',
                'Get Attitude (Gyro)': b'#TPUG2rGIC003A',
                'Get Attitude Auto-Send Status': b'#TPUG2rGAA0030',
                'Enable Attitude Auto-Send': b'#TPUG2wGAA0136',
                'Disable Attitude Auto-Send': b'#TPUG2wGAA0035'
            },
            'ZOOM': {
                'Stop Zoom': b'#TPUM2wZMC005C',
                'Zoom Out': b'#TPUM2wZMC015D',
                'Zoom In': b'#TPUM2wZMC025E',
                'Get Zoom Position': b'#TPUM2rZOM0063',
                'Get Zoom Magnification': b'#TPUM2rZMP0065'
            },
            'FOCUS': {
                'Stop Focus': b'#TPUM2wFCC003E',
                'Focus +': b'#TPUM2wFCC013F',
                'Focus -': b'#TPUM2wFCC0240',
                'Auto Focus': b'#TPUM2wFCC104C',
                'Manual Focus': b'#TPUM2wFCC114D',
                'Get Focus Position': b'#TPUM2rFOC0045'
            },
            'RECORDING': {
                'Stop Recording': b'#TPUD2wREC0044',
                'Start Recording': b'#TPUD2wREC0145',
                'Toggle Recording': b'#TPUD2wREC0A54',
                'Get Recording Status': b'#TPUD2rREC003E'
            },
            'CAPTURE': {
                'Capture Visible+Thermal': b'#TPUD2wCAP013E',
                'Capture Visible Only': b'#TPUD2wCAP023F',
                'Capture Thermal Only': b'#TPUD2wCAP0340',
                'Capture All with Temp': b'#TPUD2wCAP0542'
            },
            'VIDEO_SETTINGS': {
                'Set 4K Resolution': b'#TPUD2wVID0049',
                'Set HD Resolution': b'#TPUD2wVID014A',
                'Set 720p Resolution': b'#TPUD2wVID024B',
                'Get Video Resolution': b'#TPUD2rVID0047',
                'Set Bitrate 2Mbps': b'#TPUD2wBIT0149',
                'Set Bitrate 4Mbps': b'#TPUD2wBIT034B',
                'Set Bitrate 8Mbps': b'#TPUD2wBIT074F'
            },
            'PICTURE_IN_PICTURE': {
                'Main Only': b'#TPUD2wPIP0063',
                'Main+Sub': b'#TPUD2wPIP015B',
                'Sub+Main': b'#TPUD2wPIP025C',
                'Sub Only': b'#TPUD2wPIP035C',
                'Next Mode': b'#TPUD2wPIP0A63',
                'Get PIP Mode': b'#TPUD2rPIP004D'
            },
            'DAY_NIGHT': {
                'Day Mode': b'#TPUM2wIRC005F',
                'Night Mode': b'#TPUM2wIRC0160',
                'Toggle Mode': b'#TPUM2wIRC0A61'
            },
            'SYSTEM': {
                'Get SD Card Free Space': b'#TPUD2rSDC003E',
                'Get SD Card Total Space': b'#TPUD2rSDC013F',
                'Normal Rotation': b'#TPUD2wROT005E',
                'Rotate 180°': b'#TPUD2wROT025C',
                'Get Rotation': b'#TPUD2rROT0059',
                'Get Version': b'#TPPD2rVSN0056'
            }
        }
        
    def print_commands(self):
        """Print all available commands"""
        print("\n" + "="*70)
        print("GIMBAL COMMAND REFERENCE")
        print("="*70)
        
        for category, commands in self.commands.items():
            print(f"\n{category.replace('_', ' ')}:")
            print("-" * 50)
            
            for i, (desc, cmd) in enumerate(commands.items(), 1):
                cmd_str = cmd.decode('ascii', errors='replace')
                print(f"{i:2d}. {desc:<35} {cmd_str}")
    
    def send_command(self, cmd_bytes):
        """Send a command"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(cmd_bytes, (self.camera_ip, self.control_port))
        sock.close()
        print(f"Sent: {cmd_bytes.decode('ascii', errors='replace')}")
    
    def interactive_mode(self):
        """Interactive command testing"""
        print("\nINTERACTIVE COMMAND MODE")
        print("Enter category letter + number (e.g., G1 for Gimbal Stop)")
        print("Or enter 'help' to see commands again")
        print("Enter 'quit' to exit")
        print()
        
        # Create category shortcuts
        categories = list(self.commands.keys())
        cat_map = {}
        
        print("Categories:")
        for i, cat in enumerate(categories):
            letter = cat[0]
            if letter in cat_map:
                letter = cat[0:2]
            cat_map[letter.upper()] = cat
            print(f"  {letter} - {cat.replace('_', ' ')}")
        
        while True:
            try:
                user_input = input("\nCommand> ").strip().upper()
                
                if user_input == 'QUIT':
                    break
                elif user_input == 'HELP':
                    self.print_commands()
                    continue
                
                # Parse input (e.g., "G1")
                if len(user_input) >= 2:
                    cat_letter = user_input[0]
                    if len(user_input) >= 3 and user_input[1].isalpha():
                        cat_letter = user_input[0:2]
                        num_str = user_input[2:]
                    else:
                        num_str = user_input[1:]
                    
                    # Find category
                    category = None
                    for key, cat in cat_map.items():
                        if key.startswith(cat_letter):
                            category = cat
                            break
                    
                    if category and num_str.isdigit():
                        cmd_num = int(num_str)
                        cmd_list = list(self.commands[category].items())
                        
                        if 1 <= cmd_num <= len(cmd_list):
                            desc, cmd = cmd_list[cmd_num - 1]
                            print(f"\nExecuting: {desc}")
                            self.send_command(cmd)
                        else:
                            print(f"Invalid number. Range: 1-{len(cmd_list)}")
                    else:
                        print("Invalid format. Use: CategoryLetter + Number (e.g., G1)")
                else:
                    print("Invalid input")
                    
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    def test_basic_communication(self):
        """Test basic communication"""
        print("\nTesting basic communication...")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.bind(('0.0.0.0', GIMBAL_CONFIG['listen_port']))
        recv_sock.settimeout(2.0)
        
        # Test get attitude
        cmd = self.commands['GIMBAL_QUERY']['Get Attitude (Magnetic)']
        sock.sendto(cmd, (self.camera_ip, self.control_port))
        
        try:
            data, _ = recv_sock.recvfrom(1024)
            print(f"✓ Communication working! Response: {data.decode('ascii', errors='replace')}")
            return True
        except socket.timeout:
            print("✗ No response - check connection")
            return False
        finally:
            sock.close()
            recv_sock.close()


def main():
    ref = CommandReference()
    
    print("="*70)
    print("GIMBAL COMMAND REFERENCE & TESTER")
    print("="*70)
    
    # Test communication first
    if not ref.test_basic_communication():
        print("\n⚠️  Cannot communicate with gimbal")
        print("Check connection and try again")
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    print("\nOptions:")
    print("1. Show all commands")
    print("2. Interactive command mode")
    print("3. Quick test (movement demo)")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == '1':
        ref.print_commands()
    elif choice == '2':
        ref.print_commands()
        ref.interactive_mode()
    elif choice == '3':
        print("\nQuick movement test...")
        import time
        
        # Move left
        print("Moving left...")
        ref.send_command(ref.commands['GIMBAL_CONTROL']['Left'])
        time.sleep(1)
        
        # Stop
        print("Stopping...")
        ref.send_command(ref.commands['GIMBAL_CONTROL']['Stop'])
        time.sleep(0.5)
        
        # Move right
        print("Moving right...")
        ref.send_command(ref.commands['GIMBAL_CONTROL']['Right'])
        time.sleep(1)
        
        # Stop
        print("Stopping...")
        ref.send_command(ref.commands['GIMBAL_CONTROL']['Stop'])
        
        print("\nQuick test complete!")


if __name__ == "__main__":
    main()