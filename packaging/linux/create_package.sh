#!/bin/bash
# PostgreSQL Data Lineage Tool - Linux Package Script

echo "Creating Linux package..."

# Set variables
APP_NAME="PostgreSQL Data Lineage"
DIST_DIR="dist/pg_lineage"
PACKAGE_DIR="dist/linux_package"
DESKTOP_FILE="packaging/linux/pg_lineage.desktop"
ICON_FILE="packaging/linux/pg_lineage.png"

# Create directories
mkdir -p "$PACKAGE_DIR/usr/local/bin"
mkdir -p "$PACKAGE_DIR/usr/local/share/applications"
mkdir -p "$PACKAGE_DIR/usr/local/share/icons/hicolor/128x128/apps"

# Copy executable and dependencies
cp -R "$DIST_DIR"/* "$PACKAGE_DIR/usr/local/bin/"

# Copy icon
cp "$ICON_FILE" "$PACKAGE_DIR/usr/local/share/icons/hicolor/128x128/apps/"

# Create .desktop file
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=PostgreSQL Data Lineage
Comment=PostgreSQL Data Lineage Analysis Tool
Exec=/usr/local/bin/pg_lineage
Icon=/usr/local/share/icons/hicolor/128x128/apps/pg_lineage.png
Terminal=false
Type=Application
Categories=Development;Database;
EOF

# Copy .desktop file
cp "$DESKTOP_FILE" "$PACKAGE_DIR/usr/local/share/applications/"

# Create a tarball
echo "Creating tarball..."
cd dist
tar -czvf "${APP_NAME// /_}_linux.tar.gz" -C linux_package .
cd ..

echo "Done! Linux package created at: dist/${APP_NAME// /_}_linux.tar.gz"
echo "To install, run: sudo tar -xzvf ${APP_NAME// /_}_linux.tar.gz -C /"