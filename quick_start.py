#!/usr/bin/env python3
"""
Gimbal Control Quick Start
==========================
Run this script to quickly test all gimbal features.
"""

import sys
import os
import time

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


def print_menu():
    """Print main menu"""
    print("\n" + "="*60)
    print("GIMBAL CONTROL SYSTEM - QUICK START")
    print("="*60)
    print("\nBASIC TESTS:")
    print("1. Run diagnostics")
    print("2. Test basic connection (simple)")
    print("3. Unlock gimbal")
    print("4. Run full demo")
    
    print("\nMONITORING:")
    print("5. Real-time attitude monitor")
    print("6. Tracking status monitor")
    print("7. Read telemetry (no ffmpeg)")
    print("8. Network traffic monitor")
    
    print("\nMOTION & CONTROL:")
    print("9. Full motion range test")
    print("10. Test tracking (LOC command)")
    print("11. Application tests (surveillance, etc)")
    
    print("\nVIDEO:")
    print("12. RTSP stream viewer")
    
    print("\nDEBUGGING:")
    print("13. Troubleshoot issues")
    print("14. Test commands (detailed)")
    print("15. Protocol analyzer")
    print("16. Protocol validator")
    print("17. Command reference")
    
    print("\n18. Exit")
    print("-"*60)


def run_script(script_name):
    """Run a Python script"""
    print(f"\nRunning {script_name}...")
    print("-"*60)
    os.system(f"{sys.executable} {script_name}")
    input("\nPress Enter to continue...")


def main():
    """Main menu loop"""
    while True:
        print_menu()
        
        try:
            choice = input("Enter your choice (1-18): ").strip()
            
            if choice == '1':
                run_script("run_diagnostics.py")
            elif choice == '2':
                run_script("gimbal_simple_test.py")
            elif choice == '3':
                run_script("unlock_gimbal.py")
            elif choice == '4':
                run_script("gimbal_demo.py")
            elif choice == '5':
                run_script("monitor.py")
            elif choice == '6':
                run_script("tracking_status_monitor.py")
            elif choice == '7':
                run_script("telemetry_reader.py")
            elif choice == '8':
                run_script("network_monitor.py")
            elif choice == '9':
                run_script("gimbal_full_motion_test.py")
            elif choice == '10':
                run_script("test_loc_command.py")
            elif choice == '11':
                run_script("gimbal_application_test.py")
            elif choice == '12':
                run_script("rtsp_stream_viewer.py")
            elif choice == '13':
                run_script("gimbal_troubleshoot.py")
            elif choice == '14':
                run_script("test_commands_detailed.py")
            elif choice == '15':
                run_script("protocol_analyzer.py")
            elif choice == '16':
                run_script("protocol_validator.py")
            elif choice == '17':
                run_script("command_reference.py")
            elif choice == '18':
                print("\nExiting...")
                break
            else:
                print("\n[!] Invalid choice. Please try again.")
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\n[ERROR] {e}")
            input("Press Enter to continue...")


if __name__ == "__main__":
    # Check if all required files exist
    required_files = [
        "config.py",
        "gimbalcmdparse.py",
        "test_connection.py",
        "gimbal_simple_test.py",
        "gimbal_demo.py",
        "monitor.py",
        "tracking_demo.py",
        "test_loc_command.py",
        "telemetry_reader.py",
        "run_diagnostics.py",
        "gimbal_troubleshoot.py",
        "test_commands_detailed.py",
        "network_monitor.py",
        "protocol_validator.py",
        "unlock_gimbal.py",
        "gimbal_full_motion_test.py",
        "tracking_status_monitor.py",
        "rtsp_stream_viewer.py",
        "protocol_analyzer.py",
        "gimbal_application_test.py",
        "command_reference.py"
    ]
    
    missing = []
    for file in required_files:
        if not os.path.exists(file):
            missing.append(file)
    
    if missing:
        print("[ERROR] Missing required files:")
        for file in missing:
            print(f"  - {file}")
        print("\nPlease ensure all files are in the current directory.")
        sys.exit(1)
    
    # Run main menu
    main()