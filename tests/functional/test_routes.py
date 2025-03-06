"""
Functional tests for the Flask application routes.
"""
import os
import pytest
import json
import tempfile
import pandas as pd
from unittest.mock import patch, MagicMock
from flask import session

from app import app


class TestRoutes:
    """Test cases for the application routes."""

    def test_index_route(self, client):
        """Test the index route."""
        response = client.get('/')
        assert response.status_code == 200
        # Check for key elements in the response
        assert b'<title>pg_lineagelens' in response.data
        assert b'PostgreSQL Data Lineage' in response.data

    def test_connect_post(self, client):
        """Test the connect endpoint with POST method."""
        # The connect route now uses AJAX, so we send a POST and expect JSON
        response = client.post('/connect', data={
            'host': 'localhost',
            'database': 'testdb',
            'user': 'postgres',
            'password': 'password',
            'port': '5432'
        }, content_type='application/x-www-form-urlencoded')
        
        assert response.status_code == 200
        # Check response content type
        assert response.content_type == 'application/json'

    @patch('app.routes.PostgresQueryLineage')
    def test_connect_route_post_success(self, mock_lineage_class, client):
        """Test successful database connection."""
        # Configure mock
        mock_lineage = MagicMock()
        mock_lineage_class.return_value = mock_lineage
        mock_lineage.connect.return_value = (True, "Successfully connected to database")
        
        # Submit connection form via AJAX
        response = client.post('/connect', data={
            'host': 'localhost',
            'database': 'testdb',
            'user': 'postgres',
            'password': 'password',
            'port': '5432'
        })
        
        # Check JSON response
        assert response.status_code == 200
        json_data = json.loads(response.data)
        assert json_data['success'] is True
        
        # Verify session variables
        with client.session_transaction() as sess:
            assert 'connection_params' in sess
            assert sess['connection_params']['database'] == 'testdb'
            assert sess['connection_params']['host'] == 'localhost'

    @patch('app.routes.PostgresQueryLineage')
    def test_connect_route_post_failure(self, mock_lineage_class, client):
        """Test failed database connection."""
        # Configure mock
        mock_lineage = MagicMock()
        mock_lineage_class.return_value = mock_lineage
        mock_lineage.connect.return_value = (False, "Error connecting to database")
        
        # Submit connection form via AJAX
        response = client.post('/connect', data={
            'host': 'localhost',
            'database': 'non_existent_db',
            'user': 'postgres',
            'password': 'wrong_password',
            'port': '5432'
        })
        
        # Check JSON response
        assert response.status_code == 200
        json_data = json.loads(response.data)
        assert json_data['success'] is False
        assert "Error connecting to database" in json_data['message']

    @patch('app.routes.PostgresQueryLineage')
    def test_analyze_post(self, mock_lineage_class, client):
        """Test the analyze endpoint with POST method."""
        # Configure mock
        mock_lineage = MagicMock()
        mock_lineage_class.return_value = mock_lineage
        mock_lineage.run_complete_analysis.return_value = {
            'expensive_queries': pd.DataFrame([{
                'queryid': 1, 
                'query': 'SELECT * FROM users',
                'calls': 100,
                'total_time': 1000.0
            }]),
            'table_stats': pd.DataFrame(),
            'files': {
                'lineage_image': '/tmp/lineage.svg',
                'expensive_queries': '/tmp/queries.csv'
            }
        }
        
        # Set up session
        with client.session_transaction() as sess:
            sess['connection_params'] = {
                'host': 'localhost',
                'database': 'testdb',
                'user': 'postgres',
                'password': 'password',
                'port': 5432
            }
        
        # Submit analysis request
        response = client.post('/analyze', data={
            'limit': '20',
            'min_calls': '5'
        })
        
        # Check JSON response
        assert response.status_code == 200
        json_data = json.loads(response.data)
        assert json_data['success'] is True
        assert 'queries_count' in json_data

    def test_analyze_post_not_connected(self, client):
        """Test analyze endpoint when not connected."""
        # Post to analyze without connection params in session
        response = client.post('/analyze', data={
            'limit': '20',
            'min_calls': '5'
        })
        
        # Check JSON response
        assert response.status_code == 200
        json_data = json.loads(response.data)
        assert json_data['success'] is False
        assert 'Not connected to a database' in json_data['message']

    def test_expensive_queries_page(self, client):
        """Test expensive queries page."""
        # Set up session with analysis results
        with client.session_transaction() as sess:
            sess['has_results'] = True
            sess['analysis_files'] = {
                'expensive_queries': None  # This will cause a redirect with a flash message
            }
        
        response = client.get('/expensive_queries', follow_redirects=True)
        assert response.status_code == 200

    def test_lineage_page(self, client):
        """Test lineage page."""
        # Create a temp file to simulate the lineage image
        with tempfile.NamedTemporaryFile(suffix='.svg') as tmp:
            tmp_path = tmp.name
            # Write some SVG content to the temp file
            tmp.write(b'<svg></svg>')
            tmp.flush()
            
            # Set up session with analysis results
            with client.session_transaction() as sess:
                sess['has_results'] = True
                sess['analysis_files'] = {
                    'lineage_image': tmp_path,
                    'lineage_graphml': tmp_path
                }
            
            response = client.get('/lineage')
            assert response.status_code == 200
            assert b'Data Lineage' in response.data

    def test_reset_route(self, client):
        """Test session reset."""
        # Set session variables
        with client.session_transaction() as sess:
            sess['has_results'] = True
            sess['analysis_files'] = {'some_file': 'path'}
        
        # Request session reset
        response = client.get('/reset', follow_redirects=True)
        
        # Check response
        assert response.status_code == 200
        
        # Verify session variables
        with client.session_transaction() as sess:
            assert 'has_results' not in sess
            assert 'analysis_files' not in sess

    def test_disconnect_route(self, client):
        """Test database disconnect."""
        # Set session variables
        with client.session_transaction() as sess:
            sess['connection_params'] = {
                'host': 'localhost',
                'database': 'testdb',
                'user': 'postgres',
                'password': 'password',
                'port': 5432
            }
            sess['has_results'] = True
        
        # Request disconnect
        response = client.get('/disconnect', follow_redirects=True)
        
        # Check response
        assert response.status_code == 200
        
        # Verify session variables
        with client.session_transaction() as sess:
            assert 'connection_params' not in sess
            assert 'has_results' not in sess
    
    @patch('app.routes.os.path.exists')
    @patch('app.routes.send_file')
    def test_download_route(self, mock_send_file, mock_exists, client):
        """Test download endpoint."""
        # Mock file existence check
        mock_exists.return_value = True
        
        # Mock send_file to return a custom response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_send_file.return_value = mock_response
        
        # Set up session with analysis results
        with client.session_transaction() as sess:
            sess['has_results'] = True
            sess['analysis_files'] = {
                'expensive_queries': '/tmp/fake_path.csv'
            }
        
        # Try to download a file
        response = client.get('/download/expensive_queries')
        
        # Check that send_file was called
        mock_send_file.assert_called_once_with('/tmp/fake_path.csv', as_attachment=True)
        
        # Check response
        assert response.status_code == 200

    @patch('app.routes.pd.read_csv')
    def test_table_details_page(self, mock_read_csv, client):
        """Test table details page."""
        # Mock the pandas read_csv function to return test data
        mock_df = pd.DataFrame([
            {'table_name': 'users', 'schema': 'public', 'row_count': 1000}
        ])
        mock_read_csv.return_value = mock_df
        
        # Set up session with analysis results
        with client.session_transaction() as sess:
            sess['has_results'] = True
            sess['analysis_files'] = {
                'table_stats': '/tmp/fake_path.csv'  # Path doesn't matter as we're mocking read_csv
            }
        
        # Request table details for a table that exists in our mock data
        response = client.get('/table_details/users', follow_redirects=True)
        assert response.status_code == 200
            
    @patch('app.routes.os.path.exists')
    @patch('app.routes.pd.read_csv')
    def test_table_stats_page(self, mock_read_csv, mock_exists, client):
        """Test table stats page."""
        # Mock file existence check
        mock_exists.return_value = True
        
        # Mock the pandas read_csv function to return test data with all required columns
        # Based on the template, we need these specific columns
        mock_df = pd.DataFrame([
            {
                'table_name': 'users', 
                'schema': 'public', 
                'row_count': 1000,
                'total_queries': 150,
                'read_queries': 100,
                'write_queries': 50,
                'total_time': 1000.0,
                'total_read_time': 800.0,
                'total_write_time': 200.0
            }
        ])
        mock_read_csv.return_value = mock_df
        
        # Set up session with analysis results
        with client.session_transaction() as sess:
            sess['has_results'] = True
            sess['analysis_files'] = {
                'table_stats': '/tmp/fake_path.csv'  # Path doesn't matter as we're mocking read_csv
            }
        
        response = client.get('/table_stats', follow_redirects=True)
        assert response.status_code == 200
        # Check for some expected content
        assert b'Table Statistics' in response.data
        assert b'users' in response.data  # Should show our mock table name
    
    @patch('app.routes.pd.read_csv')
    def test_query_details_page(self, mock_read_csv, client):
        """Test query details page."""
        # Mock the pandas read_csv function to return test data
        mock_df = pd.DataFrame([
            {'queryid': 1, 'query': 'SELECT * FROM users', 'calls': 100, 'total_time': 1000.0}
        ])
        mock_read_csv.return_value = mock_df
        
        # Set up session with analysis results
        with client.session_transaction() as sess:
            sess['has_results'] = True
            sess['analysis_files'] = {
                'expensive_queries': '/tmp/fake_path.csv'  # Path doesn't matter as we're mocking read_csv
            }
        
        # Test with a valid query index that exists in our mock data
        response = client.get('/query_details/0', follow_redirects=True)
        assert response.status_code == 200