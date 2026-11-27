#!/bin/bash
# Starts the Pilot Vacation Scheduler on a Mac (also works on Linux).
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 was not found. Install it from https://www.python.org/downloads/ and run this again."
  read -r -p "Press Enter to close."
  exit 1
fi
if [ ! -x .venv/bin/python ]; then
  echo "First start: setting things up. This takes a minute or two..."
  python3 -m venv .venv || { read -r -p "Setup failed. Press Enter to close."; exit 1; }
fi
.venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements.txt \
  || { echo "Setup failed. Check your internet connection and try again."; read -r -p "Press Enter to close."; exit 1; }
.venv/bin/python run.py
