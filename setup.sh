#!/bin/bash
set -euo pipefail

# NTP Monitor Installation Script
# Usage: sudo ./setup.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICE_USER="ntp-monitor"
INSTALL_DIR="/opt/ntp-monitor"
LOG_DIR="/var/log/ntp-monitor"
SERVICE_NAME="ntp-monitor"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_system() {
    log_info "Checking system requirements..."
    
    # Check if systemd is available
    if ! command -v systemctl &> /dev/null; then
        log_error "systemctl not found. This script requires systemd."
        exit 1
    fi
    
    # Check Python version
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
        log_error "Python 3.8 or higher is required"
        exit 1
    fi
    
    # Check if pip is available
    if ! command -v pip3 &> /dev/null; then
        log_warning "pip3 not found, attempting to install..."
        apt-get update && apt-get install -y python3-pip
    fi
    
    log_success "System requirements check passed"
}

create_user() {
    log_info "Creating service user: $SERVICE_USER"
    
    if id "$SERVICE_USER" &>/dev/null; then
        log_warning "User $SERVICE_USER already exists"
    else
        useradd --system --shell /bin/false --home "$INSTALL_DIR" --create-home "$SERVICE_USER"
        log_success "Created user: $SERVICE_USER"
    fi
}

install_dependencies() {
    log_info "Installing Python dependencies..."
    
    # Install system packages
    apt-get update
    apt-get install -y python3-pip python3-dev python3-matplotlib python3-numpy python3-scipy
    
    # Install Python packages
    pip3 install influxdb-client ntplib
    
    log_success "Dependencies installed"
}

create_directories() {
    log_info "Creating directories..."
    
    # Create main directories
    mkdir -p "$INSTALL_DIR"/{data,config}
    mkdir -p "$LOG_DIR"
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$LOG_DIR"
    
    # Set permissions
    chmod 755 "$INSTALL_DIR"
    chmod 755 "$INSTALL_DIR/data"
    chmod 755 "$LOG_DIR"
    
    log_success "Directories created"
}

install_files() {
    log_info "Installing application files..."
    
    # Copy Python scripts
    cp src/ntp_monitor.py "$INSTALL_DIR/"
    cp src/ntp_monitor_service.py "$INSTALL_DIR/"
    
    # Copy configuration template
    if [[ ! -f "$INSTALL_DIR/config.py" ]]; then
        cp src/config.py.example "$INSTALL_DIR/config.py"
        log_info "Created config.py from template"
    else
        log_warning "config.py already exists, not overwriting"
    fi
    
    # Copy environment template
    if [[ ! -f "$INSTALL_DIR/.env" ]]; then
        cp config/.env.example "$INSTALL_DIR/.env"
        log_info "Created .env from template"
    else
        log_warning ".env already exists, not overwriting"
    fi
    
    # Set permissions
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    chmod 755 "$INSTALL_DIR"/*.py
    chmod 600 "$INSTALL_DIR/.env"  # Protect credentials
    
    log_success "Application files installed"
}

install_service() {
    log_info "Installing systemd service..."
    
    # Copy service file
    cp systemd/ntp-monitor.service /etc/systemd/system/
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable service
    systemctl enable "$SERVICE_NAME"
    
    log_success "Systemd service installed and enabled"
}

configure_logrotate() {
    log_info "Configuring log rotation..."
    
    cp config/logrotate.conf /etc/logrotate.d/ntp-monitor
    
    log_success "Log rotation configured"
}

prompt_configuration() {
    log_info "Configuration setup..."
    
    echo
    echo "Please configure the following settings:"
    echo "1. Edit $INSTALL_DIR/.env for InfluxDB credentials"
    echo "2. Edit $INSTALL_DIR/config.py for NTP server settings"
    echo
    
    read -p "Would you like to configure now? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        configure_interactive
    else
        log_warning "Configuration skipped. Remember to configure before starting the service."
    fi
}

configure_interactive() {
    log_info "Interactive configuration..."
    
    # Get NTP server
    read -p "Enter NTP server to monitor [pool.ntp.org]: " ntp_server
    ntp_server=${ntp_server:-pool.ntp.org}
    
    # Get InfluxDB settings
    read -p "Enter InfluxDB URL [http://localhost:8086]: " influx_url
    influx_url=${influx_url:-http://localhost:8086}
    
    read -p "Enter InfluxDB token (leave empty to disable InfluxDB): " influx_token
    
    read -p "Enter InfluxDB organization [your-org]: " influx_org
    influx_org=${influx_org:-your-org}
    
    read -p "Enter InfluxDB bucket [ntp-monitoring]: " influx_bucket
    influx_bucket=${influx_bucket:-ntp-monitoring}
    
    # Update configuration files
    cat > "$INSTALL_DIR/.env" << EOF
# InfluxDB Settings
INFLUX_URL=$influx_url
INFLUX_TOKEN=$influx_token
INFLUX_ORG=$influx_org
INFLUX_BUCKET=$influx_bucket

# Environment
PYTHONPATH=$INSTALL_DIR
MPLCONFIGDIR=$INSTALL_DIR/.config/matplotlib
EOF
    
    # Update config.py
    sed -i "s/NTP_SERVER = .*/NTP_SERVER = \"$ntp_server\"/" "$INSTALL_DIR/config.py"
    
    # Set permissions
    chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/.env"
    chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/config.py"
    chmod 600 "$INSTALL_DIR/.env"
    
    # Create matplotlib config directory
    mkdir -p "$INSTALL_DIR/.config/matplotlib"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/.config"
    
    log_success "Configuration updated"
}

test_installation() {
    log_info "Testing installation..."
    
    # Test Python script
    if sudo -u "$SERVICE_USER" python3 "$INSTALL_DIR/ntp_monitor_service.py" --test 2>/dev/null; then
        log_success "Python script test passed"
    else
        log_warning "Python script test failed - check configuration"
    fi
    
    # Test service start
    if systemctl start "$SERVICE_NAME"; then
        sleep 5
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            log_success "Service started successfully"
            systemctl stop "$SERVICE_NAME"
        else
            log_error "Service failed to start"
            systemctl status "$SERVICE_NAME" --no-pager
            return 1
        fi
    else
        log_error "Failed to start service"
        return 1
    fi
}

show_completion() {
    log_success "Installation completed successfully!"
    
    echo
    echo "========================================"
    echo "  NTP Monitor Installation Complete"
    echo "========================================"
    echo
    echo "Next steps:"
    echo "1. Review configuration:"
    echo "   sudo nano $INSTALL_DIR/.env"
    echo "   sudo nano $INSTALL_DIR/config.py"
    echo
    echo "2. Start the service:"
    echo "   sudo systemctl start $SERVICE_NAME"
    echo
    echo "3. Check service status:"
    echo "   sudo systemctl status $SERVICE_NAME"
    echo
    echo "4. View logs:"
    echo "   sudo journalctl -u $SERVICE_NAME -f"
    echo
    echo "5. Import Grafana dashboard:"
    echo "   Use grafana/dashboard.json"
    echo
    echo "Configuration files:"
    echo "  - Service config: $INSTALL_DIR/config.py"
    echo "  - Environment: $INSTALL_DIR/.env"
    echo "  - Data directory: $INSTALL_DIR/data"
    echo "  - Logs: $LOG_DIR"
    echo
    echo "Documentation: docs/"
    echo "Health check: ./scripts/health-check.sh"
    echo
}

# Main installation process
main() {
    echo "========================================"
    echo "    NTP Monitor Installation Script"
    echo "========================================"
    echo
    
    check_root
    check_system
    create_user
    install_dependencies
    create_directories
    install_files
    install_service
    configure_logrotate
    prompt_configuration
    
    if test_installation; then
        show_completion
    else
        log_error "Installation completed with errors. Check logs and configuration."
        exit 1
    fi
}

# Run main function
main "$@"
