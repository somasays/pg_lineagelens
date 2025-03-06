"""
Development server for PostgreSQL Data Lineage application.
This script is used during development and testing.
"""

from app import app

if __name__ == '__main__':
    # Run in debug mode for development
    app.run(debug=True, host='127.0.0.1', port=5000)