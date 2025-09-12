#!/bin/bash

# Modified from: https://mattrucker.com/your-secure-gateway-to-azure-connecting-to-anything-with-vs-code-and-azure-bastion/

# Load environment variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo ".env file not found!"
    exit 1
fi

echo "Let's get you logged into Azure..."
az login

echo "Starting the Bastion tunnel to your jump host..."
az network bastion tunnel \
    --name "$BASTION_NAME" \
    --resource-group "$BASTION_RG" \
    --target-resource-id "$TARGET_VM_ID" \
    --resource-port "$REMOTE_SSH_PORT" \
    --port "$LOCAL_SSH_PORT" &

TUNNEL_PID=$!

echo "Success! Tunnel is running in the background (PID: $TUNNEL_PID)."
echo "You can now connect to your jump host in VS Code."
echo "Press Ctrl+C to close this tunnel when you're done."

wait $TUNNEL_PID
