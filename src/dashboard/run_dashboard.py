"""
Dashboard runner script for the Meme Coin Signal Bot.

This script runs the Streamlit dashboard.
"""
import os
import sys
import subprocess

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """Run the Streamlit dashboard."""
    dashboard_path = os.path.join(os.path.dirname(__file__), "app.py")
    subprocess.run(["streamlit", "run", dashboard_path])

if __name__ == "__main__":
    main()
