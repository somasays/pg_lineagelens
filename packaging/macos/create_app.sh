#!/bin/bash
# PostgreSQL Data Lineage Tool - macOS App Bundle Script

echo "Creating macOS app bundle..."

# Set variables
APP_NAME="PostgreSQL Data Lineage"
APP_DIR="dist/$APP_NAME.app"
CONTENTS_DIR="$APP_DIR/Contents"
RESOURCES_DIR="$CONTENTS_DIR/Resources"
MACOS_DIR="$CONTENTS_DIR/MacOS"
DIST_DIR="dist/pg_lineage"
ICON_FILE="packaging/macos/pg_lineage.icns"

# Create directories
mkdir -p "$RESOURCES_DIR"
mkdir -p "$MACOS_DIR"

# Copy executable and dependencies
cp -R "$DIST_DIR"/* "$MACOS_DIR"

# Create Info.plist
cat > "$CONTENTS_DIR/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>English</string>
    <key>CFBundleDisplayName</key>
    <string>PostgreSQL Data Lineage</string>
    <key>CFBundleExecutable</key>
    <string>pg_lineage</string>
    <key>CFBundleIconFile</key>
    <string>pg_lineage.icns</string>
    <key>CFBundleIdentifier</key>
    <string>com.pglineage</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>PostgreSQL Data Lineage</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright © 2024</string>
</dict>
</plist>
EOF

# Copy icon
cp "$ICON_FILE" "$RESOURCES_DIR"

# Create a wrapper script to ensure the executable is run from the correct directory
cat > "$MACOS_DIR/run.sh" << EOF
#!/bin/bash
cd "\$(dirname "\$0")"
./pg_lineage
EOF

# Make the wrapper script executable
chmod +x "$MACOS_DIR/run.sh"

# Create DMG
echo "Creating DMG..."
hdiutil create -volname "$APP_NAME" -srcfolder "$APP_DIR" -ov -format UDZO "dist/$APP_NAME.dmg"

echo "Done!"