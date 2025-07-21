#!/bin/bash
# Auto-commit daemon for Lucky Gas project
# Run this script to start automatic commits in the background

PROJECT_DIR="/Users/lgee258/Desktop/LuckyGas-v3"
SCRIPT_PATH="$PROJECT_DIR/auto-commit.sh"
PID_FILE="$PROJECT_DIR/.auto-commit.pid"
LOG_FILE="$PROJECT_DIR/auto-commit.log"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

start_daemon() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${YELLOW}Auto-commit daemon is already running (PID: $PID)${NC}"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}Starting auto-commit daemon...${NC}"
    nohup "$SCRIPT_PATH" > /dev/null 2>&1 &
    echo $! > "$PID_FILE"
    echo -e "${GREEN}Auto-commit daemon started (PID: $(cat "$PID_FILE"))${NC}"
    echo -e "Log file: $LOG_FILE"
}

stop_daemon() {
    if [ ! -f "$PID_FILE" ]; then
        echo -e "${YELLOW}Auto-commit daemon is not running${NC}"
        exit 1
    fi
    
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "${GREEN}Stopping auto-commit daemon (PID: $PID)...${NC}"
        kill $PID
        rm -f "$PID_FILE"
        echo -e "${GREEN}Auto-commit daemon stopped${NC}"
    else
        echo -e "${YELLOW}Auto-commit daemon is not running${NC}"
        rm -f "$PID_FILE"
    fi
}

status_daemon() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${GREEN}Auto-commit daemon is running (PID: $PID)${NC}"
            echo -e "Last 5 log entries:"
            tail -n 5 "$LOG_FILE"
        else
            echo -e "${RED}Auto-commit daemon is not running (stale PID file)${NC}"
            rm -f "$PID_FILE"
        fi
    else
        echo -e "${YELLOW}Auto-commit daemon is not running${NC}"
    fi
}

case "$1" in
    start)
        start_daemon
        ;;
    stop)
        stop_daemon
        ;;
    status)
        status_daemon
        ;;
    restart)
        stop_daemon
        sleep 2
        start_daemon
        ;;
    *)
        echo "Usage: $0 {start|stop|status|restart}"
        echo ""
        echo "  start   - Start the auto-commit daemon"
        echo "  stop    - Stop the auto-commit daemon"
        echo "  status  - Check daemon status"
        echo "  restart - Restart the daemon"
        exit 1
        ;;
esac