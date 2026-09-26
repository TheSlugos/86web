# Compiling 86Box with UNIX Socket IPC

This guide explains how to compile the custom version of 86Box (from the `feat-unix-socket-ipc` branch) on a Debian/Ubuntu based system, which includes the UNIX socket IPC required for 86Web's headless hot-swapping feature.

## Method A: Build via Docker (Recommended - Zero Host Dependencies)

From the `86web` directory, simply run:

```bash
docker compose -f docker-compose.build-86box.yml up --build
```

This compiles 86Box in a self-contained container and automatically places the binary at `data/cache/86box/86Box` tagged with version `custom`.

---

## Method B: Manual Host Build

### 1. Install Build Dependencies

```bash
sudo apt-get update
sudo apt-get install -y \
    build-essential cmake ninja-build git \
    qt6-base-dev qt6-tools-dev qt6-tools-dev-tools qt6-l10n-tools qt6-base-private-dev \
    libqt6opengl6-dev libvulkan-dev \
    libfreetype-dev libpng-dev libslirp-dev libzstd-dev libx11-dev libsdl2-dev \
    libsndfile1-dev libopenal-dev librtmidi-dev libfluidsynth-dev \
    libvdeplug-dev libserialport-dev
```

### 2. Clone the Repository and Checkout the Branch

```bash
git clone git@github.com:TheSlugos/86Box.git
cd 86Box
git checkout feat-unix-socket-ipc
```

### 3. Configure the Build

Configure with CMake using Ninja. On Ubuntu 22.04 with Qt 6.2 and SDL2:

```bash
mkdir -p build
cd build
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release -DUSE_QT6=ON -DUSE_QT6_BELOW10=ON -DSDL2=ON
```

*(You can safely ignore any warnings about `libxkbcommon-x11-dev` missing, as we do not need advanced X11 raw input capture for headless VNC usage).*

## 4. Compile

Run ninja to compile the codebase:

```bash
ninja
```

## 5. Install into 86Web

Once compiled, the resulting binary will be located at `build/src/86Box`.

To use this with 86Web, copy it into 86Web's data cache directory so the Docker container mounts it automatically:

```bash
# Assuming you are in the 86Box/build directory
cp src/86Box /path/to/86web/data/cache/86box/86Box
```

Restart your VM in the 86Web UI, and the Python runner will begin routing Mount/Eject commands directly into the new `/tmp/86box-ipc.sock`!
