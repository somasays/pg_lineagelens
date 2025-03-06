"""
Global pytest configuration and fixtures.
"""
import os
import sys
import time
import socket
import pytest
try:
    import docker
except ImportError:
    # Mock docker for unit tests if not available
    docker = None
from unittest.mock import patch, MagicMock
from flask import Flask

# Add the app directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import routes
from app.analyzer import PostgresQueryLineage

# Check if we can use docker for integration tests
DOCKER_AVAILABLE = docker is not None

# Skip decorator for tests that require Docker
docker_required = pytest.mark.docker(
    pytest.mark.skipif(
        not DOCKER_AVAILABLE,
        reason="Docker not available for integration tests"
    )
)

if DOCKER_AVAILABLE:
    # Docker container fixture for integration tests
    @pytest.fixture(scope="session")
    def docker_compose_file(pytestconfig):
        """Path to the docker-compose.yml file."""
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), "docker-compose.yml")

    @pytest.fixture(scope="session")
    def docker_compose_project_name():
        """Project name for the Docker Compose."""
        return "pg_lineage_test"

    @pytest.fixture(scope="session")
    def postgres_service(docker_ip, docker_services):
        """Ensure that PostgreSQL service is up and responsive."""
        port = docker_services.port_for("postgres", 5432)
        server_url = f"postgresql://postgres:postgres@{docker_ip}:{port}/postgres"
        docker_services.wait_until_responsive(
            timeout=30.0, pause=0.1, check=lambda: is_postgres_responsive(docker_ip, port)
        )
        return server_url

    def is_postgres_responsive(host, port):
        """Check if PostgreSQL is responsive."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.connect((host, port))
            sock.close()
            return True
        except socket.error:
            return False

    @pytest.fixture(scope="session")
    def postgres_connection_params(docker_ip, docker_services):
        """PostgreSQL connection parameters for integration tests."""
        port = docker_services.port_for("postgres", 5432)
        return {
            "host": docker_ip,
            "database": "postgres",
            "user": "postgres",
            "password": "postgres",
            "port": port
        }
else:
    # Provide mock fixtures when Docker is not available
    @pytest.fixture(scope="session")
    def postgres_service():
        """Mock PostgreSQL service when Docker is not available."""
        pytest.skip("Docker not available for integration tests")
        
    @pytest.fixture(scope="session")
    def postgres_connection_params():
        """Mock PostgreSQL connection parameters when Docker is not available."""
        pytest.skip("Docker not available for integration tests")

@pytest.fixture
def app():
    """Create and configure a Flask app for testing."""
    from app import app as flask_app
    
    # Configure app for testing
    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test_key',
        'DEBUG': True,
        'SESSION_TYPE': 'filesystem',
        'SESSION_PERMANENT': False
    })
    
    # Since routes are already registered in the app module, we don't need to register them again
    
    yield flask_app


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
        mock_analyzer.connect.return_value = (True, "Connected successfully")
        mock_analyzer.disconnect.return_value = None
        mock_analyzer.check_pg_stat_statements.return_value = (True, "pg_stat_statements is available")
        mock_analyzer.get_expensive_queries.return_value = []
        mock_analyzer.get_table_dependencies.return_value = {}
        mock_analyzer.build_lineage_graph.return_value = MagicMock()
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