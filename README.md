# NTP Monitor

A comprehensive Network Time Protocol (NTP) monitoring solution with InfluxDB integration and Grafana dashboards for real-time visualization and alerting.

![NTP Monitor Dashboard](docs/dashboard-preview.png)

## Features

- 🕐 **Real-time NTP monitoring** with sub-millisecond precision
- 📊 **InfluxDB integration** for time-series data storage
- 📈 **Grafana dashboards** with beautiful visualizations
- 🚀 **Systemd service** for production deployment
- 📝 **Comprehensive logging** with automatic rotation
- 🔧 **Easy configuration** with environment variables
- 📱 **Multi-server support** for monitoring multiple NTP sources
- 🛡️ **Security hardened** service with minimal privileges
- 🔄 **Auto-restart** and health monitoring
- 📉 **Statistical analysis** including jitter, stability, and trends

## Quick Start

### 1. Clone and Install
```bash
git clone https://github.com/yourusername/ntp-monitor.git
cd ntp-monitor
chmod +x setup.sh
sudo ./setup.sh
```

### 2. Configure
```bash
# Edit configuration
sudo nano /opt/ntp-monitor/.env

# Set your NTP server and InfluxDB details
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=your-influx-token-here
INFLUX_ORG=your-org
INFLUX_BUCKET=ntp-monitoring
NTP_SERVER=pool.ntp.org
```

### 3. Start Service
```bash
sudo systemctl start ntp-monitor
sudo systemctl enable ntp-monitor
```

### 4. Import Grafana Dashboard
- Open Grafana → Import Dashboard
- Upload `grafana/dashboard.json`
- Configure your InfluxDB datasource

## Dashboard Metrics

- **Offset Trends** - Time synchronization accuracy over time
- **Delay Analysis** - Network latency to NTP servers  
- **Stability Metrics** - Jitter and variance analysis
- **Statistical Views** - Mean, median, percentiles, and distribution
- **Current Status** - Real-time gauges with threshold alerts
- **Health Monitoring** - Service uptime and query success rates

## Installation Options

### Option 1: Automated Setup (Recommended)
```bash
curl -sSL https://raw.githubusercontent.com/yourusername/ntp-monitor/main/setup.sh | sudo bash
```

### Option 2: Manual Installation
See [INSTALLATION.md](docs/INSTALLATION.md) for detailed manual setup instructions.

### Option 3: Docker (Coming Soon)
```bash
docker run -d --name ntp-monitor \
  -e INFLUX_URL=http://influxdb:8086 \
  -e INFLUX_TOKEN=your-token \
  yourusername/ntp-monitor
```

## Requirements

- **Python 3.8+**
- **InfluxDB 2.0+** (optional, can run CSV-only mode)
- **Grafana 8.0+** (for dashboards)
- **Linux system** with systemd

### Python Dependencies
- `influxdb-client` - InfluxDB integration
- `ntplib` - NTP client functionality  
- `matplotlib` - Plot generation
- `numpy` - Statistical calculations
- `scipy` - Advanced statistics

## Configuration

### Environment Variables
```bash
# NTP Settings
NTP_SERVER=pool.ntp.org           # NTP server to monitor
POLLING_INTERVAL=60               # Query interval in seconds

# InfluxDB Settings  
INFLUX_URL=http://localhost:8086  # InfluxDB URL
INFLUX_TOKEN=your-token-here      # Authentication token
INFLUX_ORG=your-org               # Organization name
INFLUX_BUCKET=ntp-monitoring      # Data bucket

# Logging
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
```

### Multiple Server Monitoring
```python
# config/multi-server.py
NTP_SERVERS = [
    "pool.ntp.org",
    "time.google.com", 
    "time.cloudflare.com",
    "time.windows.com"
]
```

## Usage

### Standalone Script
```bash
# Run the original standalone version
python3 src/ntp_monitor.py
```

### Service Management
```bash
# Service status
sudo systemctl status ntp-monitor

# View logs
sudo journalctl -u ntp-monitor -f

# Restart service
sudo systemctl restart ntp-monitor
```

### Health Monitoring
```bash
# Check service health
./scripts/health-check.sh

# Manual health check
curl http://localhost:8080/health  # If metrics endpoint enabled
```

## Monitoring and Alerting

### Grafana Alerts
The dashboard includes pre-configured alert rules for:
- **High Offset** - When time drift exceeds 50ms
- **Network Issues** - When NTP queries fail
- **Service Down** - When monitoring stops

### Slack/Email Notifications
Configure Grafana notification channels for:
- Critical timing issues
- Service health problems  
- Weekly summary reports

## Troubleshooting

### Common Issues

**Service won't start:**
```bash
# Check dependencies
./scripts/install-dependencies.sh

# Verify configuration
sudo -u ntp-monitor python3 /opt/ntp-monitor/ntp_monitor_service.py
```

**No data in dashboard:**
- Verify InfluxDB connection and credentials
- Check service logs: `sudo journalctl -u ntp-monitor`
- Confirm Grafana datasource configuration

**Permission errors:**
```bash
# Fix file permissions
sudo chown -R ntp-monitor:ntp-monitor /opt/ntp-monitor
sudo chown -R ntp-monitor:ntp-monitor /var/log/ntp-monitor
```

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for detailed solutions.

## Development

### Running Tests
```bash
python3 -m pytest tests/
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality  
4. Submit a pull request

### Building Documentation
```bash
# Generate API docs
pdoc --html src/ -o docs/api/

# Build user guide
mkdocs build
```

## Security

- Service runs as dedicated `ntp-monitor` user
- Minimal system privileges (only network access)
- Secure credential management via environment variables
- Log files protected with appropriate permissions
- No shell access for service user

## Performance

- **Memory usage:** ~50MB typical
- **CPU usage:** <1% on modern systems  
- **Disk usage:** ~100MB/year for CSV logs (with rotation)
- **Network:** <1KB per query (configurable interval)

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Changelog

### v1.0.0 (2025-06-26)
- Initial release
- Basic NTP monitoring with InfluxDB
- Grafana dashboard integration
- Systemd service support
- Comprehensive logging and health checks

### Planned Features
- [ ] Docker containerization
- [ ] Multi-server dashboard views  
- [ ] REST API for external integrations
- [ ] Advanced statistical analysis
- [ ] Custom alert rules engine
- [ ] Web-based configuration interface

## Support

- 📖 **Documentation:** [docs/](docs/)
- 🐛 **Issues:** [GitHub Issues](https://github.com/yourusername/ntp-monitor/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/yourusername/ntp-monitor/discussions)
- 📧 **Security:** security@yourdomain.com

## Acknowledgments

- Built for monitoring critical time infrastructure
- Inspired by the need for reliable NTP monitoring
- Community contributions welcome!
