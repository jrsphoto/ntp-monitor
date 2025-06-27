## docs/INSTALLATION.md
```markdown
# Installation Guide

## Prerequisites

### System Requirements
- Linux system with systemd
- Python 3.8 or higher
- Root/sudo access for service installation

### Optional Components
- InfluxDB 2.0+ for time-series storage
- Grafana 8.0+ for dashboards

## Installation Methods

### Method 1: Automated Installation (Recommended)

```bash
# Clone repository
git clone https://github.com/yourusername/ntp-monitor.git
cd ntp-monitor

# Make setup script executable
chmod +x setup.sh

# Run automated installation
sudo ./setup.sh
```

The setup script will:
- Install system dependencies
- Create service user and directories
- Install Python packages
- Configure systemd service
- Set up log rotation
- Guide you through configuration

### Method 2: Manual Installation

#### Step 1: Install Dependencies
```bash
sudo apt-get update
sudo apt-get install python3 python3-pip python3-dev

# Install Python packages
sudo pip3 install influxdb-client ntplib matplotlib numpy scipy
```

#### Step 2: Create Service User
```bash
sudo useradd --system --shell /bin/false --home /opt/ntp-monitor ntp-monitor
```

#### Step 3: Create Directories
```bash
sudo mkdir -p /opt/ntp-monitor/{data,config}
sudo mkdir -p /var/log/ntp-monitor
sudo chown -R ntp-monitor:ntp-monitor /opt/ntp-monitor
sudo chown -R ntp-monitor:ntp-monitor /var/log/ntp-monitor
```

#### Step 4: Install Files
```bash
# Copy application files
sudo cp src/ntp_monitor_service.py /opt/ntp-monitor/
sudo cp src/config.py.example /opt/ntp-monitor/config.py
sudo cp config/.env.example /opt/ntp-monitor/.env

# Set permissions
sudo chown -R ntp-monitor:ntp-monitor /opt/ntp-monitor
sudo chmod 755 /opt/ntp-monitor/*.py
sudo chmod 600 /opt/ntp-monitor/.env
```

#### Step 5: Configure Service
```bash
# Copy systemd service file
sudo cp systemd/ntp-monitor.service /etc/systemd/system/

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable ntp-monitor
```

#### Step 6: Configure Log Rotation
```bash
sudo cp config/logrotate.conf /etc/logrotate.d/ntp-monitor
```

## Configuration

### Environment Variables
Edit `/opt/ntp-monitor/.env`:
```bash
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=your-influx-token-here
INFLUX_ORG=your-org
INFLUX_BUCKET=ntp-monitoring
NTP_SERVER=pool.ntp.org
```

### Application Configuration
Edit `/opt/ntp-monitor/config.py`:
```python
NTP_SERVER = "your.ntp.server.com"
POLLING_INTERVAL = 60  # seconds
LOG_LEVEL = "INFO"
```

## Starting the Service

```bash
# Start service
sudo systemctl start ntp-monitor

# Check status
sudo systemctl status ntp-monitor

# View logs
sudo journalctl -u ntp-monitor -f
```

## Verification

1. **Check service status:**
   ```bash
   sudo systemctl status ntp-monitor
   ```

2. **Verify data collection:**
   ```bash
   ls -la /opt/ntp-monitor/data/
   tail /var/log/ntp-monitor/ntp-monitor.log
   ```

3. **Run health check:**
   ```bash
   ./scripts/health-check.sh
   ```

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.
```

## docs/CONFIGURATION.md
```markdown
# Configuration Reference

## Environment Variables

All configuration can be done via environment variables in `/opt/ntp-monitor/.env`:

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `NTP_SERVER` | NTP server to monitor | `pool.ntp.org` | `time.google.com` |
| `POLLING_INTERVAL` | Query interval in seconds | `60` | `30` |
| `INFLUX_URL` | InfluxDB URL | `http://localhost:8086` | `https://influx.example.com` |
| `INFLUX_TOKEN` | InfluxDB authentication token | _(empty)_ | `abc123...` |
| `INFLUX_ORG` | InfluxDB organization | `your-org` | `monitoring` |
| `INFLUX_BUCKET` | InfluxDB bucket name | `ntp-monitoring` | `metrics` |
| `LOG_LEVEL` | Logging level | `INFO` | `DEBUG` |

## Application Configuration

Advanced settings in `/opt/ntp-monitor/config.py`:

```python
# NTP Settings
NTP_SERVER = "pool.ntp.org"
POLLING_INTERVAL = 60
MAX_POINTS = 1000  # In-memory data points

# File Paths
DATA_DIR = "/opt/ntp-monitor/data"
CSV_FILE = os.path.join(DATA_DIR, "ntp_metrics.csv")
PLOT_FILE = os.path.join(DATA_DIR, "ntp_metrics.png")
LOG_FILE = "/var/log/ntp-monitor/ntp-monitor.log"

# InfluxDB Configuration
INFLUX_CONFIG = {
    'url': os.getenv('INFLUX_URL', 'http://localhost:8086'),
    'token': os.getenv('INFLUX_TOKEN', ''),
    'org': os.getenv('INFLUX_ORG', 'your-org'),
    'bucket': os.getenv('INFLUX_BUCKET', 'ntp-monitoring')
}
```

## Multiple Server Monitoring

Create a custom configuration for monitoring multiple servers:

```python
# Multi-server configuration
NTP_SERVERS = [
    {"host": "pool.ntp.org", "name": "NTP Pool"},
    {"host": "time.google.com", "name": "Google Time"},
    {"host": "time.cloudflare.com", "name": "Cloudflare Time"},
    {"host": "time.windows.com", "name": "Microsoft Time"}
]
```

## Security Configuration

### Service User Permissions
The service runs as `ntp-monitor` user with minimal privileges:
- No shell access (`/bin/false`)
- Limited filesystem access
- Only network capability for NTP queries

### File Permissions
- Configuration files: `600` (owner read/write only)
- Application files: `755` (executable)
- Data directory: `755` (read/write for service user)
- Log directory: `755` (read/write for service user)

### Credential Management
- Store sensitive tokens in `.env` file
- Use environment variables for deployment
- Rotate InfluxDB tokens regularly

## Performance Tuning

### Memory Usage
- Adjust `MAX_POINTS` to control memory usage
- Default 1000 points ≈ 50MB memory

### Disk Usage
- CSV files grow ~100MB/year with 60s intervals
- Configure log rotation to manage disk space
- Consider InfluxDB retention policies

### Network Impact
- Each query is <1KB
- Default 60s interval = 1440 queries/day
- Adjust `POLLING_INTERVAL` based on requirements

## Logging Configuration

### Log Levels
- `DEBUG`: Detailed debugging information
- `INFO`: General operational messages
- `WARNING`: Warning conditions
- `ERROR`: Error conditions

### Log Rotation
Configured in `/etc/logrotate.d/ntp-monitor`:
- Daily rotation
- Keep 30 days
- Compress old logs
- Reload service after rotation
```

## examples/multi-server-config.py
```python
#!/usr/bin/env python3
"""
Example: Multi-Server NTP Monitoring Configuration

This example shows how to monitor multiple NTP servers
with different configurations and tagging.
"""

import os
from typing import List, Dict

# Multiple NTP servers to monitor
NTP_SERVERS = [
    {
        "host": "pool.ntp.org",
        "name": "NTP_Pool",
        "location": "Global",
        "priority": "primary"
    },
    {
        "host": "time.google.com", 
        "name": "Google_Time",
        "location": "Global",
        "priority": "secondary"
    },
    {
        "host": "time.cloudflare.com",
        "name": "Cloudflare_Time", 
        "location": "Global",
        "priority": "secondary"
    },
    {
        "host": "time.nist.gov",
        "name": "NIST_Time",
        "location": "US",
        "priority": "reference"
    }
]

# Polling intervals per server type
POLLING_INTERVALS = {
    "primary": 30,      # 30 seconds for primary
    "secondary": 60,    # 60 seconds for secondary  
    "reference": 300    # 5 minutes for reference
}

# InfluxDB configuration with server tagging
def get_influx_config(server_info: Dict) -> Dict:
    return {
        'url': os.getenv('INFLUX_URL', 'http://localhost:8086'),
        'token': os.getenv('INFLUX_TOKEN', ''),
        'org': os.getenv('INFLUX_ORG', 'monitoring'),
        'bucket': os.getenv('INFLUX_BUCKET', 'ntp-monitoring'),
        'tags': {
            'server_name': server_info['name'],
            'location': server_info['location'],
            'priority': server_info['priority']
        }
    }

# Alerting thresholds per server priority
ALERT_THRESHOLDS = {
    "primary": {
        "offset_warning": 10.0,    # 10ms
        "offset_critical": 50.0,   # 50ms
        "delay_warning": 100.0,    # 100ms
        "delay_critical": 500.0    # 500ms
    },
    "secondary": {
        "offset_warning": 20.0,    # 20ms
        "offset_critical": 100.0,  # 100ms
        "delay_warning": 200.0,    # 200ms
        "delay_critical": 1000.0   # 1000ms
    },
    "reference": {
        "offset_warning": 50.0,    # 50ms
        "offset_critical": 200.0,  # 200ms
        "delay_warning": 500.0,    # 500ms
        "delay_critical": 2000.0   # 2000ms
    }
}

# Usage example for multi-server monitoring service
if __name__ == "__main__":
    print("Multi-Server NTP Monitoring Configuration")
    print("=" * 50)
    
    for server in NTP_SERVERS:
        interval = POLLING_INTERVALS[server['priority']]
        thresholds = ALERT_THRESHOLDS[server['priority']]
        
        print(f"Server: {server['name']}")
        print(f"  Host: {server['host']}")
        print(f"  Location: {server['location']}")
        print(f"  Priority: {server['priority']}")
        print(f"  Polling Interval: {interval}s")
        print(f"  Alert Thresholds: {thresholds}")
        print()
```
