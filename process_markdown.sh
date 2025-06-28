#!/bin/bash

# Script to process markdown files in a user-specified directory using Docker.

# --- Configuration ---
DOCKER_IMAGE_NAME="memory-app"
CONFIG_FILE_NAME="config.json"
# This is the path *inside the container* where the markdown directory will be mounted.
# Your config.json's "markdown_directories" should point to this path (e.g., ["data_to_process"]).
CONTAINER_MARKDOWN_PATH="/app/data_to_process"

# --- Prompt user for input ---
read -p "Enter the absolute path to your local markdown directory: " LOCAL_MARKDOWN_DIR
read -p "Enter the user ID for whom to process memories: " USER_ID

# --- Validate input ---
if [ -z "$LOCAL_MARKDOWN_DIR" ]; then
  echo "Error: Markdown directory path cannot be empty."
  exit 1
fi

if [ ! -d "$LOCAL_MARKDOWN_DIR" ]; then
  echo "Error: Local markdown directory '$LOCAL_MARKDOWN_DIR' not found."
  exit 1
fi

if [ -z "$USER_ID" ]; then
  echo "Error: User ID cannot be empty."
  exit 1
fi

if [ ! -f "$CONFIG_FILE_NAME" ]; then
  echo "Error: Configuration file '$CONFIG_FILE_NAME' not found in the current directory ($(pwd))."
  echo "Please ensure it exists and you are running this script from the correct location."
  exit 1
fi

# --- Construct and execute Docker command ---
echo ""
echo "Attempting to process markdown files..."
echo "Local Markdown Directory: $LOCAL_MARKDOWN_DIR"
echo "User ID: $USER_ID"
echo "Docker Image: $DOCKER_IMAGE_NAME"
echo "Mounting $LOCAL_MARKDOWN_DIR to $CONTAINER_MARKDOWN_PATH inside the container."
echo "Using $CONFIG_FILE_NAME from $(pwd)"
echo ""

docker run -it --rm \
  -v "$(pwd)/$CONFIG_FILE_NAME:/app/$CONFIG_FILE_NAME" \
  -v "$LOCAL_MARKDOWN_DIR:$CONTAINER_MARKDOWN_PATH" \
  "$DOCKER_IMAGE_NAME" process --user "$USER_ID" --config "/app/$CONFIG_FILE_NAME"

# Check exit status of Docker command
if [ $? -eq 0 ]; then
  echo ""
  echo "✅ Markdown processing command completed."
else
  echo ""
  echo "❌ Markdown processing command failed."
fi

