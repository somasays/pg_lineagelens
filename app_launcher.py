"""
Production launcher for PostgreSQL Data Lineage application.
Starts the application and automatically opens it in the default web browser.
"""

import os
import sys
import webbrowser
import threading
import time
import logging
from waitress import serve
from app import app

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(os.path.expanduser('~'), 'pg_lineage.log'))
    ]
)
logger = logging.getLogger('pg_lineage')

def open_browser():
    """Open the application in the default web browser"""
    # Wait for server to start
    time.sleep(1.5)
    url = 'http://127.0.0.1:5000'
    logger.info(f"Opening browser at {url}")
    webbrowser.open(url)

def start_server():
    """Start the production server"""
    host = '127.0.0.1'
    port = 5000
    
    logger.info(f"Starting PostgreSQL Data Lineage application on {host}:{port}")
    logger.info("Press Ctrl+C to exit")
    
    try:
        # Start the server with Waitress (production WSGI server)
        serve(app, host=host, port=port)
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Error starting server: {e}")
    
    logger.info("Server stopped")

if __name__ == '__main__':
    # Start browser in a separate thread
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Start server in the main thread
    start_server()