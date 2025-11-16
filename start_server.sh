#!/bin/bash
# Startup script for IRF Database Django server

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Initialize conda for bash if not already done
eval "$(conda shell.bash hook)"

# Activate the conda environment
echo "Activating irfdatabase conda environment..."
conda activate irfdatabase

# Check if activation was successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to activate conda environment 'irfdatabase'"
    echo "Please ensure the environment exists by running: conda env create -f environment.yml"
    exit 1
fi

# Run Django development server
echo "Starting Django development server..."
echo "Access the application at: http://127.0.0.1:8000/"
echo "Press Ctrl+C to stop the server"
python manage.py runserver
