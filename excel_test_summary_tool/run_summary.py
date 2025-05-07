#!/usr/bin/env python3
"""
Excel Test Summary Tool - Runner script

Simple launcher script that wraps the main functionality of the tool.
"""

import argparse
import sys
from main import main as run_main

if __name__ == "__main__":
    try:
        run_main()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        sys.exit(1)