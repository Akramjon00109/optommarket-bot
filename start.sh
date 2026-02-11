#!/bin/bash
# Start script for Render deployment

# Create logs directory if not exists
mkdir -p logs

# Start the bot
python -m bot.main
