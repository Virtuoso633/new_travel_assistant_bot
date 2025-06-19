#!/bin/bash
echo "Starting Rasa server... $PORT"
rasa run --enable-api --cors "*" --port $PORT &
rasa run actions