#!/bin/bash

# WeeWX AirVisual Extension Package Creator
set -e

echo "Creating WeeWX AirVisual extension package..."

# Version information
VERSION="1.0.0"
PACKAGE_NAME="weewx-airvisual-${VERSION}"

# Remove any existing package
rm -f ${PACKAGE_NAME}.zip weewx-airvisual.zip

# Create temporary directory for package
TEMP_DIR=$(mktemp -d)
PACKAGE_DIR="${TEMP_DIR}/${PACKAGE_NAME}"
mkdir -p "${PACKAGE_DIR}"

echo "Copying files according to MANIFEST..."

# Copy files according to MANIFEST
while IFS= read -r file; do
    if [[ -z "$file" || "$file" =~ ^# ]]; then
        continue
    fi
    
    echo "   Copying: $file"
    DIR=$(dirname "$file")
    if [ "$DIR" != "." ]; then
        mkdir -p "${PACKAGE_DIR}/${DIR}"
    fi
    
    if [ -f "$file" ]; then
        cp "$file" "${PACKAGE_DIR}/${file}"
    elif [ -d "$file" ]; then
        cp -r "$file" "${PACKAGE_DIR}/${DIR}/"
    else
        echo "   Warning: $file not found, skipping"
    fi
done < MANIFEST

# Create the ZIP package
echo "Creating ZIP package..."
cd "${TEMP_DIR}"
zip -r "${PACKAGE_NAME}.zip" "${PACKAGE_NAME}/"

# Move package to original directory
mv "${PACKAGE_NAME}.zip" "${OLDPWD}/"
cd "${OLDPWD}"

# Create symlink for convenience
ln -sf "${PACKAGE_NAME}.zip" "weewx-airvisual.zip"

# Clean up
rm -rf "${TEMP_DIR}"

echo "✅ Package created: ${PACKAGE_NAME}.zip"
echo "🔗 Symlink: weewx-airvisual.zip"

# Show package contents
echo
echo "Package contents:"
unzip -l "${PACKAGE_NAME}.zip"

echo
echo "Installation command:"
echo "  weectl extension install ${PACKAGE_NAME}.zip"
