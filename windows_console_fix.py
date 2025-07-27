#!/usr/bin/env python3
"""
Windows Console Encoding Fix
============================
Apply this fix before running scripts on Windows to handle Unicode.
"""

import sys
import os


def fix_windows_console():
    """Fix Windows console encoding for Unicode support"""
    if sys.platform == 'win32':
        # Set console code page to UTF-8
        os.system('chcp 65001 > nul')
        
        # Set Python's stdout encoding
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
        
        print("Windows console encoding fixed for UTF-8 support")
        return True
    return False


if __name__ == "__main__":
    fix_windows_console()
    print("You can now run the gimbal scripts with better Unicode support.")
    print("\nTest Unicode characters:")
    print("✓ Checkmark")
    print("→ Arrow")
    print("• Bullet")
    print("° Degree")