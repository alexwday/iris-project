#!/bin/bash
# Setup and run comparison script for fresh clone

echo "Setting up Python virtual environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

echo "Installing project dependencies..."
pip install -e .

echo ""
echo "Setup complete! Now you can run the comparison:"
echo ""
echo "Usage:"
echo "  python compare_src_folders.py /path/to/your/src /path/to/their/src"
echo ""
echo "Example:"
echo "  python compare_src_folders.py ./iris/src /path/to/their/iris/src"
echo ""
echo "The script will open an HTML report in your browser showing all differences."