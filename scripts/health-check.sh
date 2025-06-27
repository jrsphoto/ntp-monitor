#!/bin/bash
# NTP Monitor Health Check Script

SERVICE="ntp-monitor"
LOG_FILE="/var/log/ntp-monitor/ntp-monitor.log"
DATA_FILE="/opt/ntp-monitor/data/ntp_metrics.csv"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_service() {
    if systemctl is-active --quiet $SERVICE; then
        echo -e "${GREEN}✓${NC} Service $SERVICE is running"
        return 0
    else
        echo -e "${RED}✗${NC} Service $SERVICE is not running"
        return 1
    fi
}

check_logs() {
    if [ ! -f "$LOG_FILE" ]; then
        echo -e "${RED}✗${NC} Log file $LOG_FILE not found"
        return 1
    fi
    
    # Check if log was updated in last 5 minutes
    if [ $(find "$LOG_FILE" -mmin -5 | wc -l) -eq 0 ]; then
        echo -e "${YELLOW}⚠${NC} Log file hasn't been updated in 5+ minutes"
        return 1
    fi
    
    echo -e "${GREEN}✓${NC} Log file is being updated"
    return 0
}

check_data() {
    if [ ! -f "$DATA_FILE" ]; then
        echo -e "${YELLOW}⚠${NC} Data file $DATA_FILE not found"
        return 1
    fi
    
    # Check if data file was updated recently
    if [ $(find "$DATA_FILE" -mmin -2 | wc -l) -eq 0 ]; then
        echo -e "${YELLOW}⚠${NC} Data file hasn't been updated recently"
        return 1
    fi
    
    echo -e "${GREEN}✓${NC} Data file is being updated"
    return 0
}

main() {
    echo "NTP Monitor Health Check"
    echo "========================"
    
    exit_code=0
    
    check_service || exit_code=1
    check_logs || exit_code=1
    check_data || exit_code=1
    
    if [ $exit_code -eq 0 ]; then
        echo -e "\n${GREEN}Overall Status: HEALTHY${NC}"
    else
        echo -e "\n${RED}Overall Status: ISSUES DETECTED${NC}"
    fi
    
    exit $exit_code
}

main "$@"
