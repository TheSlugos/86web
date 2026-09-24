#!/bin/bash
set -e

PUID=${PUID:-1000}
PGID=${PGID:-1000}

echo "=================================================="
echo " [86Box Builder] Starting build for 86Box"
echo " UID: ${PUID}, GID: ${PGID}"
echo "=================================================="

mkdir -p /build
cd /build

echo "[86Box Builder] Running CMake configure..."
cmake /src -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DUSE_QT6=ON \
    -DDEV_BUILD=OFF

echo "[86Box Builder] Running Ninja build..."
ninja

echo "[86Box Builder] Installing binary to /output..."
mkdir -p /output
cp /build/src/86Box /output/86Box
chmod 0755 /output/86Box
chown "$PUID:$PGID" /output/86Box

# Set version to custom to prevent runner's auto-updater from replacing it
echo "custom" > /output/86box.version
chown "$PUID:$PGID" /output/86box.version

echo "=================================================="
echo " [86Box Builder] Build complete!"
echo " Binary installed to: /output/86Box"
echo " Version set to: custom"
echo "=================================================="
