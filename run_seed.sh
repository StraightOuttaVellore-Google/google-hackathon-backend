#!/bin/bash

# Quick script to run Firebase chat seeding with proper credentials

cd "$(dirname "$0")"

# Set the Firebase credentials path
export SERVICE_ACCOUNT_KEY_PATH="$(pwd)/firebase-service-account.json"

# Check if credentials file exists
if [ ! -f "$SERVICE_ACCOUNT_KEY_PATH" ]; then
    echo "❌ Error: Firebase credentials file not found at: $SERVICE_ACCOUNT_KEY_PATH"
    echo "   Please ensure firebase-service-account.json exists in this directory"
    exit 1
fi

echo "🌱 Running Firebase chat seeding..."
echo "   Using credentials: $SERVICE_ACCOUNT_KEY_PATH"
echo ""

# Run the seed script
python seed_chat_firebase.py


