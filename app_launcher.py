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
import argparse
from waitress import serve
from app import app
from app._version import __version__

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

def open_browser(url):
    """Open the application in the default web browser"""
    # Wait for server to start
    time.sleep(1.5)
    logger.info(f"Opening browser at {url}")
    webbrowser.open(url)

def start_server(host='127.0.0.1', port=5000, open_browser_flag=True):
    """Start the production server"""
    url = f'http://{host}:{port}'
    
    logger.info(f"Starting PostgreSQL Data Lineage application on {host}:{port}")
    logger.info("Press Ctrl+C to exit")
    
    if open_browser_flag:
        # Start browser in a separate thread
        browser_thread = threading.Thread(target=open_browser, args=(url,))
        browser_thread.daemon = True
        browser_thread.start()
    
    try:
        # Start the server with Waitress (production WSGI server)
        serve(app, host=host, port=port)
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Error starting server: {e}")
    
    logger.info("Server stopped")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='PostgreSQL Query Lineage and Performance Analyzer'
    )
    parser.add_argument(
        '--host', 
        default='127.0.0.1', 
        help='Host address to bind to (default: 127.0.0.1)'
    )
    parser.add_argument(
        '--port', 
        type=int, 
        default=5000, 
        help='Port to run the server on (default: 5000)'
    )
    parser.add_argument(
        '--no-browser', 
        action='store_true',
        help='Do not open browser automatically'
    )
    parser.add_argument(
        '--version', 
        action='version', 
        version=f'%(prog)s {__version__}'
    )
    return parser.parse_args()

def main():
    """Main entry point for the command line tool"""
    args = parse_args()
    start_server(
        host=args.host, 
        port=args.port, 
        open_browser_flag=not args.no_browser
    )

if __name__ == '__main__':
    main()