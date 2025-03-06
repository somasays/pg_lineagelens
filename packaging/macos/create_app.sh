#!/bin/bash
# PostgreSQL Data Lineage Tool - macOS App Bundle Script

echo "Creating macOS app bundle..."

# Set variables
APP_NAME="pg_lineagelens"
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
    <string>pg_lineagelens</string>
    <key>CFBundleExecutable</key>
    <string>pg_lineage</string>
    <key>CFBundleIconFile</key>
    <string>pg_lineage.icns</string>
    <key>CFBundleIdentifier</key>
    <string>com.pglineagelens</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>pg_lineagelens</string>
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

# Add entitlements and remove quarantine attributes
# This helps with macOS security restrictions
# Create entitlements file
cat > "$CONTENTS_DIR/entitlements.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
</dict>
</plist>
EOF

# Make sure all files in the app are executable
find "$APP_DIR" -type f -name "pg_lineage" -exec chmod +x {} \;

# Create DMG with special options for better compatibility
echo "Creating DMG..."
hdiutil create -volname "$APP_NAME" -srcfolder "$APP_DIR" -ov -format UDZO "dist/$APP_NAME.dmg"

# Add readme file with instructions for opening the app
cat > "dist/README_MACOS.txt" << EOF
IMPORTANT: Opening pg_lineagelens on macOS

Due to macOS security features, you may see a message that the app is damaged or can't be opened.
To fix this, please follow these steps:

1. After mounting the DMG, right-click (or Control+click) on the pg_lineagelens app
2. Select "Open" from the context menu
3. Click "Open" when prompted to confirm
4. If you still see a warning, open System Preferences > Security & Privacy
5. Look for a message about pg_lineagelens being blocked and click "Open Anyway"

Alternatively, you can run this command in Terminal:
xattr -d com.apple.quarantine /Applications/pg_lineagelens.app

This will remove the quarantine attribute and allow the app to run.
EOF

echo "Done!"