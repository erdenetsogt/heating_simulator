#!/bin/bash

# Set the name of the service you want to delete
SERVICE_NAME="heating-simulator"

echo "Stopping and deleting service: $SERVICE_NAME"

# 1. Stop the running service
sudo systemctl stop "$SERVICE_NAME"

# 2. Disable the service to prevent it from starting on boot
sudo systemctl disable "$SERVICE_NAME"

# 3. Remove the service unit file from systemd directories
# Note: Most custom services are in /etc/systemd/system/
sudo rm "/etc/systemd/system/$SERVICE_NAME.service"
sudo rm -rf "/var/log/$SERVICE_NAME"
# 4. Reload the systemd daemon to apply changes
sudo systemctl daemon-reload

# 5. Optional: Clear the failed state from system memory
sudo systemctl reset-failed

echo "Service $SERVICE_NAME has been successfully removed."
