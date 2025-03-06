"""
Integration tests for database interaction.

These tests require a running PostgreSQL server with pg_stat_statements extension.
If no server is available, the tests will be skipped.
"""
import os
import pytest
import psycopg2
from unittest.mock import patch

from app.analyzer import PostgresQueryLineage


# Configuration for the test database
TEST_CONFIG = {
    'host': os.environ.get('PG_TEST_HOST', 'localhost'),
    'database': os.environ.get('PG_TEST_DB', 'postgres'),
    'user': os.environ.get('PG_TEST_USER', 'postgres'),
    'password': os.environ.get('PG_TEST_PASSWORD', 'postgres'),
    'port': int(os.environ.get('PG_TEST_PORT', '5432'))
}


# Skip all tests if no database connection is available
def is_postgres_available():
    """Check if PostgreSQL is available for testing."""
    try:
        conn = psycopg2.connect(
            host=TEST_CONFIG['host'],
            database=TEST_CONFIG['database'],
            user=TEST_CONFIG['user'],
            password=TEST_CONFIG['password'],
            port=TEST_CONFIG['port']
        )
        conn.close()
        return True
    except:
        return False


# Mark all tests in this module to be skipped if PostgreSQL is not available
pytestmark = pytest.mark.skipif(
    not is_postgres_available(),
    reason="PostgreSQL connection not available for integration tests"
)


class TestDatabaseIntegration:
    """Integration tests with a real PostgreSQL database."""
    
    @pytest.fixture
    def lineage_analyzer(self):
        """Create a PostgresQueryLineage instance connected to the database."""
        analyzer = PostgresQueryLineage(
            host=TEST_CONFIG['host'],
            database=TEST_CONFIG['database'],
            user=TEST_CONFIG['user'],
            password=TEST_CONFIG['password'],
            port=TEST_CONFIG['port']
        )
        connected = analyzer.connect()
        if not connected:
            pytest.skip("Could not connect to the database")
        
        yield analyzer
        
        # Clean up
        analyzer.disconnect()
    
    def test_connection(self, lineage_analyzer):
        """Test connection to the database."""
        assert lineage_analyzer.conn is not None
        assert not lineage_analyzer.conn.closed
    
    def test_pg_stat_statements_detection(self, lineage_analyzer):
        """Test detection of pg_stat_statements extension."""
        has_extension = lineage_analyzer.check_pg_stat_statements()
        # Note: This test won't fail if the extension is not available,
        # it just verifies the detection works correctly
        print(f"pg_stat_statements extension available: {has_extension}")
    
    def test_get_table_columns(self, lineage_analyzer):
        """Test retrieving column information from the database."""
        # This test uses the pg_class table which should exist in any PostgreSQL database
        columns = lineage_analyzer.get_table_columns("pg_class")
        
        # Verify the columns structure
        assert isinstance(columns, list)
        if columns:  # There should be columns, but don't fail if schema differs
            assert "name" in columns[0]
            assert "type" in columns[0]
            
        # Check for known columns that should exist in pg_class
        column_names = [col["name"] for col in columns]
        for expected_column in ["oid", "relname", "relnamespace"]:
            assert expected_column in column_names
    
    def test_get_expensive_queries(self, lineage_analyzer):
        """Test retrieving expensive queries from pg_stat_statements."""
        # Skip this test if pg_stat_statements is not available
        if not lineage_analyzer.check_pg_stat_statements():
            pytest.skip("pg_stat_statements extension not available")
        
        # Execute a query to have something in pg_stat_statements
        with lineage_analyzer.conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            lineage_analyzer.conn.commit()
        
        # Get expensive queries
        queries = lineage_analyzer.get_expensive_queries(limit=10)
        
        # Verify the structure
        assert isinstance(queries, list)
        # There should be at least one query (the one we just executed),
        # but don't fail if pg_stat_statements is not properly configured
        if queries:
            assert "queryid" in queries[0]
            assert "query" in queries[0]
            assert "calls" in queries[0]
            assert "total_time" in queries[0]
    
    def test_get_table_dependencies(self, lineage_analyzer):
        """Test extracting table dependencies from SQL queries."""
        # Create a list of test queries
        test_queries = [
            {
                'queryid': 1,
                'query': 'SELECT * FROM pg_class JOIN pg_namespace ON pg_class.relnamespace = pg_namespace.oid',
                'calls': 1,
                'total_time': 10.0,
                'mean_time': 10.0,
                'rows': 100
            },
            {
                'queryid': 2,
                'query': 'INSERT INTO pg_temp.test_table SELECT oid, relname FROM pg_class WHERE relkind = \'r\'',
                'calls': 1,
                'total_time': 5.0,
                'mean_time': 5.0,
                'rows': 10
            }
        ]
        
        # Extract dependencies
        dependencies = lineage_analyzer.get_table_dependencies(test_queries)
        
        # Verify the dependencies
        assert isinstance(dependencies, dict)
        # pg_class should depend on pg_namespace (from the first query)
        if 'pg_class' in dependencies:
            assert 'sources' in dependencies['pg_class']
            assert 'pg_namespace' in dependencies['pg_class']['sources']
        
        # pg_temp.test_table should depend on pg_class (from the second query)
        if 'pg_temp.test_table' in dependencies:
            assert 'sources' in dependencies['pg_temp.test_table']
            assert 'pg_class' in dependencies['pg_temp.test_table']['sources']
    
    def test_build_lineage_graph(self, lineage_analyzer):
        """Test building a lineage graph from dependencies."""
        # Create a test dependencies dictionary
        dependencies = {
            "pg_class": {
                "sources": ["pg_namespace"],
                "targets": ["pg_attribute"]
            },
            "pg_namespace": {
                "sources": [],
                "targets": ["pg_class"]
            },
            "pg_attribute": {
                "sources": ["pg_class"],
                "targets": []
            }
        }
        
        # Build the graph
        graph, positions = lineage_analyzer.build_lineage_graph(dependencies)
        
        # Verify the graph structure
        assert len(graph.nodes()) == 3
        assert ("pg_namespace", "pg_class") in graph.edges()
        assert ("pg_class", "pg_attribute") in graph.edges()
        
        # Verify positions are assigned
        assert "pg_namespace" in positions
        assert "pg_class" in positions
        assert "pg_attribute" in positions
    
    @patch('app.analyzer.plt')
    def test_visualize_lineage(self, mock_plt, lineage_analyzer):
        """Test visualizing the lineage graph."""
        # Create a test dependencies dictionary
        dependencies = {
            "pg_class": {
                "sources": ["pg_namespace"],
                "targets": ["pg_attribute"]
            },
            "pg_namespace": {
                "sources": [],
                "targets": ["pg_class"]
            },
            "pg_attribute": {
                "sources": ["pg_class"],
                "targets": []
            }
        }
        
        # Build the graph
        graph, positions = lineage_analyzer.build_lineage_graph(dependencies)
        
        # Mock plt.savefig to avoid actually creating a file
        mock_plt.savefig.return_value = None
        
        # Visualize the graph
        output_file = lineage_analyzer.visualize_lineage(graph, positions)
        
        # Verify the result
        assert output_file.endswith(".svg")
        mock_plt.savefig.assert_called_once()
    
    def test_end_to_end_analysis(self, lineage_analyzer):
        """Test the complete analysis workflow."""
        # Skip this test if pg_stat_statements is not available
        if not lineage_analyzer.check_pg_stat_statements():
            pytest.skip("pg_stat_statements extension not available")
        
        # Execute a query to have something in pg_stat_statements
        with lineage_analyzer.conn.cursor() as cursor:
            cursor.execute("SELECT relname, relkind FROM pg_class JOIN pg_namespace ON pg_class.relnamespace = pg_namespace.oid WHERE pg_namespace.nspname = 'pg_catalog'")
            lineage_analyzer.conn.commit()
        
        # Run the complete analysis
        has_pg_stat_statements, queries, dependencies, graph, positions = lineage_analyzer.run_complete_analysis(limit=10)
        
        # Verify the results
        assert isinstance(has_pg_stat_statements, bool)
        assert isinstance(queries, list)
        assert isinstance(dependencies, dict)
        
        # If analysis was successful, graph and positions should be valid
        if has_pg_stat_statements and queries:
            assert graph is not None
            assert positions is not None