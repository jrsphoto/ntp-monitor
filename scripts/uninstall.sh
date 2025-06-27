#!/bin/bash
# Uninstall NTP Monitor

SERVICE_NAME="ntp-monitor"
SERVICE_USER="ntp-monitor"
INSTALL_DIR="/opt/ntp-monitor"
LOG_DIR="/var/log/ntp-monitor"

echo "Uninstalling NTP Monitor..."

# Stop and disable service
systemctl stop $SERVICE_NAME 2>/dev/null || true
systemctl disable $SERVICE_NAME 2>/dev/null || true

# Remove service file
rm -f /etc/systemd/system/$SERVICE_NAME.service

# Remove logrotate config
rm -f /etc/logrotate.d/ntp-monitor

# Reload systemd
systemctl daemon-reload

# Remove user and directories
userdel $SERVICE_USER 2>/dev/null || true
rm -rf $INSTALL_DIR
rm -rf $LOG_DIR

echo "NTP Monitor uninstalled successfully!"
