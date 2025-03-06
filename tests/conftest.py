"""
Global pytest configuration and fixtures.
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from flask import Flask

# Add the app directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import routes
from app.analyzer import PostgresQueryLineage


@pytest.fixture
def app():
    """Create and configure a Flask app for testing."""
    app = Flask(__name__)
    app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test_key',
        'DEBUG': True,
        'SESSION_TYPE': 'filesystem',
        'SESSION_PERMANENT': False
    })
    
    # Register routes
    app.register_blueprint(routes.bp)
    
    yield app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def mock_db_connection():
    """Mock PostgreSQL database connection."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    
    # Configure the cursor to return empty results by default
    mock_cursor.fetchall.return_value = []
    mock_cursor.fetchone.return_value = None
    
    return mock_conn


@pytest.fixture
def mock_lineage_analyzer():
    """Create a mock PostgresQueryLineage instance."""
    with patch('app.analyzer.PostgresQueryLineage', autospec=True) as mock_analyzer_cls:
        mock_analyzer = mock_analyzer_cls.return_value
        mock_analyzer.connect.return_value = True
        mock_analyzer.disconnect.return_value = None
        mock_analyzer.check_pg_stat_statements.return_value = True
        mock_analyzer.get_expensive_queries.return_value = []
        mock_analyzer.get_table_dependencies.return_value = {}
        mock_analyzer.build_lineage_graph.return_value = (MagicMock(), MagicMock())
        mock_analyzer.visualize_lineage.return_value = "graph.svg"
        yield mock_analyzer


@pytest.fixture
def sample_queries():
    """Sample query data for testing."""
    return [
        {
            'queryid': 1,
            'query': 'SELECT * FROM users JOIN orders ON users.id = orders.user_id',
            'calls': 100,
            'total_time': 1000.0,
            'mean_time': 10.0,
            'rows': 1000
        },
        {
            'queryid': 2,
            'query': 'INSERT INTO audit_log (user_id, action) SELECT id, "login" FROM users WHERE last_login > NOW() - interval \'1 day\'',
            'calls': 50,
            'total_time': 500.0,
            'mean_time': 10.0,
            'rows': 500
        },
        {
            'queryid': 3,
            'query': 'UPDATE products SET stock = stock - 1 WHERE id IN (SELECT product_id FROM order_items WHERE order_id = 1234)',
            'calls': 200,
            'total_time': 2000.0,
            'mean_time': 10.0,
            'rows': 10
        }
    ]


@pytest.fixture
def sample_tables():
    """Sample table metadata for testing."""
    return {
        'public.users': {
            'columns': ['id', 'name', 'email', 'last_login'],
            'dependencies': ['public.orders', 'public.audit_log'],
            'dependents': []
        },
        'public.orders': {
            'columns': ['id', 'user_id', 'order_date', 'status'],
            'dependencies': ['public.order_items'],
            'dependents': ['public.users']
        },
        'public.order_items': {
            'columns': ['id', 'order_id', 'product_id', 'quantity'],
            'dependencies': ['public.products'],
            'dependents': ['public.orders']
        },
        'public.products': {
            'columns': ['id', 'name', 'price', 'stock'],
            'dependencies': [],
            'dependents': ['public.order_items']
        },
        'public.audit_log': {
            'columns': ['id', 'user_id', 'action', 'timestamp'],
            'dependencies': [],
            'dependents': ['public.users']
        }
    }