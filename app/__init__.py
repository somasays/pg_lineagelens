"""
PostgreSQL Data Lineage Application
A tool for analyzing query performance and building data lineage graphs.
"""

import os
import tempfile
from flask import Flask

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# Set up temporary directory for storing analysis files
app.config['UPLOAD_FOLDER'] = os.path.join(tempfile.gettempdir(), 'pg_lineage')
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Maximum content length for file uploads (16MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Initialize session storage
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(tempfile.gettempdir(), 'pg_lineage_sessions')
if not os.path.exists(app.config['SESSION_FILE_DIR']):
    os.makedirs(app.config['SESSION_FILE_DIR'])

# Import routes after app is created to avoid circular imports
from app import routes