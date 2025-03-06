"""
Functional tests for the Flask application routes.
"""
import os
import pytest
import json
from unittest.mock import patch, MagicMock
from flask import session

from app.routes import bp


class TestRoutes:
    """Test cases for the application routes."""

    def test_index_route(self, client):
        """Test the index route."""
        response = client.get('/')
        assert response.status_code == 200
        # Check for key elements in the response
        assert b'<title>PostgreSQL Data Lineage</title>' in response.data
        assert b'Connect to Database' in response.data

    def test_connect_route_get(self, client):
        """Test the connect route (GET method)."""
        response = client.get('/connect')
        assert response.status_code == 200
        assert b'<title>PostgreSQL Data Lineage</title>' in response.data
        assert b'<form' in response.data
        assert b'name="host"' in response.data
        assert b'name="database"' in response.data
        assert b'name="user"' in response.data
        assert b'name="password"' in response.data
        assert b'name="port"' in response.data

    @patch('app.routes.PostgresQueryLineage')
    def test_connect_route_post_success(self, mock_lineage_class, client):
        """Test successful database connection."""
        # Configure mock
        mock_lineage = MagicMock()
        mock_lineage_class.return_value = mock_lineage
        mock_lineage.connect.return_value = True
        mock_lineage.check_pg_stat_statements.return_value = True
        
        # Submit connection form
        response = client.post('/connect', data={
            'host': 'localhost',
            'database': 'testdb',
            'user': 'postgres',
            'password': 'password',
            'port': '5432'
        }, follow_redirects=True)
        
        # Check response
        assert response.status_code == 200
        assert b'Successfully connected to database' in response.data or b'Database Analysis' in response.data
        
        # Verify session variables
        with client.session_transaction() as sess:
            assert sess.get('connected') == True
            assert sess.get('database') == 'testdb'
            assert sess.get('host') == 'localhost'
            assert sess.get('has_pg_stat_statements') == True

    @patch('app.routes.PostgresQueryLineage')
    def test_connect_route_post_failure(self, mock_lineage_class, client):
        """Test failed database connection."""
        # Configure mock
        mock_lineage = MagicMock()
        mock_lineage_class.return_value = mock_lineage
        mock_lineage.connect.return_value = False
        
        # Submit connection form
        response = client.post('/connect', data={
            'host': 'localhost',
            'database': 'non_existent_db',
            'user': 'postgres',
            'password': 'wrong_password',
            'port': '5432'
        }, follow_redirects=True)
        
        # Check response
        assert response.status_code == 200
        assert b'Failed to connect to database' in response.data
        
        # Verify session variables
        with client.session_transaction() as sess:
            assert not sess.get('connected', False)

    @patch('app.routes.PostgresQueryLineage')
    def test_connect_missing_pg_stat_statements(self, mock_lineage_class, client):
        """Test connection with missing pg_stat_statements extension."""
        # Configure mock
        mock_lineage = MagicMock()
        mock_lineage_class.return_value = mock_lineage
        mock_lineage.connect.return_value = True
        mock_lineage.check_pg_stat_statements.return_value = False
        
        # Submit connection form
        response = client.post('/connect', data={
            'host': 'localhost',
            'database': 'testdb',
            'user': 'postgres',
            'password': 'password',
            'port': '5432'
        }, follow_redirects=True)
        
        # Check response
        assert response.status_code == 200
        assert b'connected to database' in response.data
        assert b'pg_stat_statements extension is not enabled' in response.data
        
        # Verify session variables
        with client.session_transaction() as sess:
            assert sess.get('connected') == True
            assert sess.get('has_pg_stat_statements') == False

    def test_analyze_route_not_connected(self, client):
        """Test analyze route when not connected."""
        response = client.get('/analyze', follow_redirects=True)
        assert response.status_code == 200
        assert b'not connected to any database' in response.data

    @patch('app.routes.PostgresQueryLineage')
    def test_analyze_route_success(self, mock_lineage_class, client):
        """Test successful analysis."""
        # Configure mock
        mock_lineage = MagicMock()
        mock_lineage_class.return_value = mock_lineage
        mock_lineage.connect.return_value = True
        mock_lineage.check_pg_stat_statements.return_value = True
        mock_lineage.get_expensive_queries.return_value = [
            {'queryid': 1, 'query': 'SELECT * FROM users', 'calls': 100, 'total_time': 1000.0, 'mean_time': 10.0, 'rows': 1000}
        ]
        
        # Set session variables to simulate connection
        with client.session_transaction() as sess:
            sess['connected'] = True
            sess['database'] = 'testdb'
            sess['host'] = 'localhost'
            sess['user'] = 'postgres'
            sess['password'] = 'password'
            sess['port'] = '5432'
            sess['has_pg_stat_statements'] = True
        
        # Request analysis
        response = client.get('/analyze', follow_redirects=True)
        
        # Check response
        assert response.status_code == 200
        assert b'Analysis complete' in response.data or b'Expensive Queries' in response.data
        
        # Verify session variables
        with client.session_transaction() as sess:
            assert sess.get('analyzed') == True

    @patch('app.routes.PostgresQueryLineage')
    def test_expensive_queries_route(self, mock_lineage_class, client, sample_queries):
        """Test expensive queries display."""
        # Configure mock
        mock_lineage = MagicMock()
        mock_lineage_class.return_value = mock_lineage
        mock_lineage.connect.return_value = True
        mock_lineage.get_expensive_queries.return_value = sample_queries
        
        # Set session variables
        with client.session_transaction() as sess:
            sess['connected'] = True
            sess['database'] = 'testdb'
            sess['host'] = 'localhost'
            sess['user'] = 'postgres'
            sess['password'] = 'password'
            sess['port'] = '5432'
            sess['has_pg_stat_statements'] = True
            sess['analyzed'] = True
            sess['expensive_queries'] = sample_queries
        
        # Request expensive queries
        response = client.get('/expensive_queries')
        
        # Check response
        assert response.status_code == 200
        assert b'Expensive Queries' in response.data
        for query in sample_queries:
            assert query['query'].encode() in response.data or str(query['calls']).encode() in response.data

    @patch('app.routes.PostgresQueryLineage')
    def test_lineage_route(self, mock_lineage_class, client):
        """Test lineage visualization."""
        # Configure mock
        mock_lineage = MagicMock()
        mock_lineage_class.return_value = mock_lineage
        mock_lineage.connect.return_value = True
        
        # Create mock graph data
        mock_dependencies = {
            "users": {
                "sources": ["orders"],
                "targets": []
            },
            "orders": {
                "sources": [],
                "targets": ["users"]
            }
        }
        
        mock_lineage.get_table_dependencies.return_value = mock_dependencies
        mock_lineage.build_lineage_graph.return_value = (MagicMock(), MagicMock())
        mock_lineage.visualize_lineage.return_value = "graph.svg"
        
        # Set session variables
        with client.session_transaction() as sess:
            sess['connected'] = True
            sess['database'] = 'testdb'
            sess['host'] = 'localhost'
            sess['user'] = 'postgres'
            sess['password'] = 'password'
            sess['port'] = '5432'
            sess['analyzed'] = True
            sess['expensive_queries'] = [{'queryid': 1, 'query': 'SELECT * FROM users'}]
        
        # Request lineage visualization
        response = client.get('/lineage')
        
        # Check response
        assert response.status_code == 200
        assert b'Table Lineage' in response.data
        assert b'<svg' in response.data or b'graph.svg' in response.data

    @patch('app.routes.PostgresQueryLineage')
    def test_table_details_route(self, mock_lineage_class, client):
        """Test table details display."""
        # Configure mock
        mock_lineage = MagicMock()
        mock_lineage_class.return_value = mock_lineage
        mock_lineage.connect.return_value = True
        
        # Mock table columns
        mock_columns = [
            {"name": "id", "type": "integer"},
            {"name": "name", "type": "character varying"},
            {"name": "email", "type": "character varying"}
        ]
        mock_lineage.get_table_columns.return_value = mock_columns
        
        # Set session variables
        with client.session_transaction() as sess:
            sess['connected'] = True
            sess['database'] = 'testdb'
            sess['host'] = 'localhost'
            sess['user'] = 'postgres'
            sess['password'] = 'password'
            sess['port'] = '5432'
            sess['analyzed'] = True
        
        # Request table details
        response = client.get('/table_details/users')
        
        # Check response
        assert response.status_code == 200
        assert b'Table Details: users' in response.data
        assert b'id' in response.data
        assert b'integer' in response.data
        assert b'name' in response.data
        assert b'character varying' in response.data

    def test_reset_route(self, client):
        """Test session reset."""
        # Set session variables
        with client.session_transaction() as sess:
            sess['connected'] = True
            sess['database'] = 'testdb'
            sess['analyzed'] = True
        
        # Request session reset
        response = client.get('/reset', follow_redirects=True)
        
        # Check response
        assert response.status_code == 200
        assert b'Session reset' in response.data
        
        # Verify session variables
        with client.session_transaction() as sess:
            assert not sess.get('connected', False)
            assert not sess.get('analyzed', False)

    @patch('app.routes.PostgresQueryLineage')
    def test_disconnect_route(self, mock_lineage_class, client):
        """Test database disconnect."""
        # Configure mock
        mock_lineage = MagicMock()
        mock_lineage_class.return_value = mock_lineage
        
        # Set session variables
        with client.session_transaction() as sess:
            sess['connected'] = True
            sess['database'] = 'testdb'
            sess['host'] = 'localhost'
            sess['user'] = 'postgres'
            sess['password'] = 'password'
            sess['port'] = '5432'
            sess['analyzed'] = True
        
        # Request disconnect
        response = client.get('/disconnect', follow_redirects=True)
        
        # Check response
        assert response.status_code == 200
        assert b'Disconnected from database' in response.data
        
        # Verify session variables and disconnect call
        mock_lineage.disconnect.assert_called_once()
        with client.session_transaction() as sess:
            assert not sess.get('connected', False)