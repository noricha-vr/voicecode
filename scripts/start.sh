#!/bin/bash
# VoiceCode startup script for LaunchAgent

cd /Users/ms25/project/voicecode

echo "=== Debug: Starting VoiceCode ===" >> /tmp/voicecode.log
echo "PWD: $(pwd)" >> /tmp/voicecode.log
echo ".env exists: $(test -f .env && echo yes || echo no)" >> /tmp/voicecode.log

# Load environment variables from .env file
while IFS='=' read -r key value; do
    # Skip comments and empty lines
    [[ $key =~ ^#.*$ ]] && continue
    [[ -z $key ]] && continue
    export "$key=$value"
done < .env

echo "OPENROUTER_API_KEY set: $(test -n \"$OPENROUTER_API_KEY\" && echo yes || echo no)" >> /tmp/voicecode.log

# Start the application
exec /opt/homebrew/bin/uv run python main.py
