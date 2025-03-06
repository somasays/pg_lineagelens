#!/bin/bash
# PostgreSQL Data Lineage Tool - Unix Installation Script (Pipenv version)

echo "PostgreSQL Data Lineage Tool - Installation"
echo "==========================================="
echo

# Check for Python installation
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed or not in PATH."
    echo "Please install Python 3.8 or newer and try again."
    echo "You can download Python from https://www.python.org/downloads/"
    exit 1
fi

# Check for Pipenv
if ! command -v pipenv &> /dev/null; then
    echo "Pipenv is not installed. Installing Pipenv..."
    pip3 install pipenv
    if [ $? -ne 0 ]; then
        echo "Failed to install Pipenv."
        exit 1
    fi
fi

# Install dependencies with Pipenv
echo "Installing dependencies with Pipenv..."
pipenv install
if [ $? -ne 0 ]; then
    echo "Failed to install dependencies."
    exit 1
fi

# Create desktop shortcut for Linux
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Creating desktop shortcut..."
    SCRIPT_DIR=$(pwd)
    DESKTOP_FILE="$HOME/.local/share/applications/pg-lineage.desktop"
    
    mkdir -p "$HOME/.local/share/applications"
    
    cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=PostgreSQL Data Lineage
Comment=Analyze query performance and build data lineage graphs
Exec=sh -c "cd $SCRIPT_DIR && pipenv run start"
Icon=$SCRIPT_DIR/packaging/linux/pg_lineage.png
Terminal=false
Categories=Development;Database;
EOF
    
    chmod +x "$DESKTOP_FILE"
    echo "Desktop shortcut created at $DESKTOP_FILE"
fi

echo
echo "Installation completed successfully!"
echo "Run the application with:"
echo "  pipenv run start"
echo