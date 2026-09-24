FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install all development libraries and tools required to build 86Box with Qt6
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    ninja-build \
    qt6-base-dev \
    qt6-tools-dev \
    qt6-tools-dev-tools \
    qt6-l10n-tools \
    qt6-base-private-dev \
    libfreetype-dev \
    libpng-dev \
    libslirp-dev \
    libzstd-dev \
    libx11-dev \
    libsdl2-dev \
    libsndfile1-dev \
    libopenal-dev \
    librtmidi-dev \
    libfluidsynth-dev \
    libvdeplug-dev \
    libserialport-dev \
    libqt6opengl6-dev \
    libvulkan-dev \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src

COPY build.sh /build.sh
RUN chmod +x /build.sh

ENTRYPOINT ["/build.sh"]
