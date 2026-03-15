#!/bin/bash
set -e

echo "Installing Python dependencies with --prefer-binary flag..."
pip install --prefer-binary -r requirements.txt

echo "Build completed successfully!"
