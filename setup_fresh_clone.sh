#!/bin/bash

# IRIS Project Fresh Clone Setup Script
# This script automates the complete setup process for a fresh clone of the IRIS project

set -e  # Exit on any error

echo "🚀 IRIS Project Fresh Clone Setup"
echo "=================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_step() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

# Check if Python 3.9+ is available
echo "🔍 Checking Python version..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.9 or later."
    exit 1
fi

python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.9"

if python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
    print_step "Python $python_version detected (compatible)"
else
    print_error "Python $python_version detected. Please upgrade to Python 3.9 or later."
    exit 1
fi

# Check if we're in the IRIS project root
if [ ! -f "setup.py" ] || [ ! -f "start_server.py" ]; then
    print_error "This script must be run from the IRIS project root directory."
    exit 1
fi

print_step "Running from IRIS project root"

# Step 1: Create virtual environment if it doesn't exist
echo "🔧 Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_step "Created new virtual environment"
else
    print_step "Virtual environment already exists"
fi

# Step 2: Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate
print_step "Activated virtual environment"

# Step 3: Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip
print_step "Pip upgraded"

# Step 4: Install project dependencies
echo "📦 Installing IRIS dependencies..."
pip install -e .
print_step "Installed main dependencies"

echo "📦 Installing development dependencies..."
pip install -e ".[dev]"
print_step "Installed development dependencies"

# Step 5: Set up environment file
echo "⚙️ Setting up environment configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    print_step "Created .env file from template"
    print_warning "⚠️  IMPORTANT: You need to edit .env with your actual configuration values!"
    print_warning "   Required variables to set:"
    print_warning "   - IRIS_DB_HOST"
    print_warning "   - IRIS_DB_USER"
    print_warning "   - IRIS_DB_PASSWORD"
    print_warning "   - IRIS_OAUTH_URL"
    print_warning "   - IRIS_OAUTH_CLIENT_ID"
    print_warning "   - IRIS_OAUTH_CLIENT_SECRET"
else
    print_step "Environment file already exists"
fi

# Step 6: Run code quality checks to verify installation
echo "🧪 Running installation verification..."
echo "   - Checking code formatting with Black..."
if black --check iris/ > /dev/null 2>&1; then
    print_step "Code formatting check passed"
else
    print_warning "Code formatting issues detected. Run 'black iris/' to fix."
fi

echo "   - Checking type hints with MyPy..."
if mypy iris/ > /dev/null 2>&1; then
    print_step "Type checking passed"
else
    print_warning "Type checking issues detected. Check output with 'mypy iris/'"
fi

# Step 7: Test API import
echo "🧪 Testing API import..."
if python3 -c "from iris.src.api import app; print('API import successful')" > /dev/null 2>&1; then
    print_step "API import test passed"
else
    print_warning "API import test failed. Check your environment configuration."
fi

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your actual configuration values"
echo "2. Start the server: python start_server.py"
echo "3. Test the API: python test_api.py"
echo "4. Open chat interface: open chat_interface.html"
echo ""
echo "Development commands:"
echo "- Format code: black iris/"
echo "- Type check: mypy iris/"
echo "- Run tests: pytest"
echo "- Start server: python start_server.py"
echo ""
echo "🔗 Server will run on: http://localhost:8000"
echo "📚 API Documentation: http://localhost:8000/docs"
echo ""
print_step "Fresh clone setup completed successfully!"