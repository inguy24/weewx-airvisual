#!/bin/bash

# WeeWX AirVisual Extension Package Creator
# This script creates a proper WeeWX extension package for distribution

set -e  # Exit on any error

echo "WeeWX AirVisual Extension Package Creator"
echo "========================================="

# Check if we're in the right directory
if [ ! -f "MANIFEST" ]; then
    echo "❌ Error: MANIFEST file not found. Are you in the repository root?"
    exit 1
fi

if [ ! -f "install.py" ]; then
    echo "❌ Error: install.py not found. Please ensure all files are present."
    exit 1
fi

if [ ! -f "bin/user/airvisual.py" ]; then
    echo "❌ Error: bin/user/airvisual.py not found. Please ensure all files are present."
    exit 1
fi

# Version information
VERSION="1.0.0"
PACKAGE_NAME="weewx-airvisual-${VERSION}"

echo "Creating package: ${PACKAGE_NAME}.zip"
echo

# Remove any existing package
rm -f ${PACKAGE_NAME}.zip weewx-airvisual.zip

# Create temporary directory for package
TEMP_DIR=$(mktemp -d)
PACKAGE_DIR="${TEMP_DIR}/${PACKAGE_NAME}"

echo "📁 Creating package structure in ${PACKAGE_DIR}"
mkdir -p "${PACKAGE_DIR}"

# Copy files according to MANIFEST
echo "📄 Copying files according to MANIFEST..."

while IFS= read -r file; do
    # Skip empty lines and comments
    if [[ -z "$file" || "$file" =~ ^# ]]; then
        continue
    fi
    
    echo "   Copying: $file"
    
    # Create directory if needed
    DIR=$(dirname "$file")
    if [ "$DIR" != "." ]; then
        mkdir -p "${PACKAGE_DIR}/${DIR}"
    fi
    
    # Copy the file
    if [ -f "$file" ]; then
        cp "$file" "${PACKAGE_DIR}/${file}"
    elif [ -d "$file" ]; then
        cp -r "$file" "${PACKAGE_DIR}/${DIR}/"
    else
        echo "   ⚠️ Warning: $file not found, skipping"
    fi
done < MANIFEST

# Verify required files are present
echo
echo "🔍 Verifying package contents..."

required_files=(
    "install.py"
    "bin/user/airvisual.py"
    "MANIFEST"
)

for file in "${required_files[@]}"; do
    if [ -f "${PACKAGE_DIR}/${file}" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file (MISSING - CRITICAL)"
        exit 1
    fi
done

# Optional files check
optional_files=(
    "README.md"
    "LICENSE"
    "CHANGELOG.md"
    "examples/weewx.conf.example"
)

for file in "${optional_files[@]}"; do
    if [ -f "${PACKAGE_DIR}/${file}" ]; then
        echo "   ✅ $file"
    else
        echo "   ⚠️ $file (missing - recommended)"
    fi
done

# Create the ZIP package
echo
echo "📦 Creating ZIP package..."
cd "${TEMP_DIR}"
zip -r "${PACKAGE_NAME}.zip" "${PACKAGE_NAME}/"

# Move package to original directory
mv "${PACKAGE_NAME}.zip" "${OLDPWD}/"
cd "${OLDPWD}"

# Create symlink for convenience
ln -sf "${PACKAGE_NAME}.zip" "weewx-airvisual.zip"

# Clean up temporary directory
rm -rf "${TEMP_DIR}"

# Display package information
echo
echo "✅ Package created successfully!"
echo "📦 Package file: ${PACKAGE_NAME}.zip"
echo "🔗 Symlink: weewx-airvisual.zip"
echo

# Calculate package size
PACKAGE_SIZE=$(du -h "${PACKAGE_NAME}.zip" | cut -f1)
echo "📊 Package size: ${PACKAGE_SIZE}"

# Show package contents
echo
echo "📋 Package contents:"
unzip -l "${PACKAGE_NAME}.zip"

echo
echo "🚀 Installation Instructions:"
echo "================================"
echo "1. Copy ${PACKAGE_NAME}.zip to your WeeWX system"
echo "2. Install with: weectl extension install ${PACKAGE_NAME}.zip"
echo "3. Follow the prompts to enter your API key"
echo "4. Restart WeeWX: sudo systemctl restart weewx"
echo

echo "✨ Package creation complete!"
