#!/bin/bash
# Install NTP Monitor Dependencies

set -euo pipefail

echo "Installing NTP Monitor dependencies..."

# Update package list
apt-get update

# Install system packages
apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-matplotlib \
    python3-numpy \
    python3-scipy

# Install Python packages
pip3 install \
    influxdb-client \
    ntplib

echo "Dependencies installed successfully!"
