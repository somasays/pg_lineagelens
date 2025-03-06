"""
Integration tests for database interaction using Docker PostgreSQL container.

These tests will use a Docker container for PostgreSQL with pg_stat_statements enabled.
"""
import os
import pytest
import psycopg2
from unittest.mock import patch

from app.analyzer import PostgresQueryLineage


import sys
import os
# Add the tests directory to the path so we can import from conftest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from conftest import docker_required

@docker_required
class TestDatabaseIntegration:
    """Integration tests with a real PostgreSQL database."""
    
    @pytest.fixture
    def lineage_analyzer(self, postgres_connection_params):
        """Create a PostgresQueryLineage instance connected to the database."""
        analyzer = PostgresQueryLineage(postgres_connection_params)
        success, message = analyzer.connect()
        
        if not success:
            pytest.skip(f"Could not connect to the database: {message}")
        
        yield analyzer
        
        # Clean up
        analyzer.disconnect()
    
    def test_connection(self, lineage_analyzer, postgres_service):
        """Test connection to the database."""
        assert lineage_analyzer.conn is not None
        assert not lineage_analyzer.conn.closed
    
    def test_pg_stat_statements_detection(self, lineage_analyzer, postgres_service):
        """Test detection of pg_stat_statements extension."""
        has_extension, message = lineage_analyzer.check_pg_stat_statements()
        print(f"pg_stat_statements extension available: {has_extension} - {message}")
        
        # This should now pass because our Docker container has pg_stat_statements enabled
        assert has_extension is True
    
    def test_get_table_columns(self, lineage_analyzer, postgres_service):
        """Test retrieving column information from the database."""
        # Test with our sample tables from the Docker container
        columns = lineage_analyzer.get_table_columns("test.users")
        
        # Verify the columns structure
        assert isinstance(columns, list)
        assert len(columns) > 0
        
        # Check column details
        column_names = [col["name"] for col in columns]
        assert "id" in column_names
        assert "name" in column_names
        assert "email" in column_names
    
    def test_get_expensive_queries(self, lineage_analyzer, postgres_service):
        """Test retrieving expensive queries from pg_stat_statements."""
        # Execute some test queries to populate pg_stat_statements
        with lineage_analyzer.conn.cursor() as cursor:
            cursor.execute("SELECT * FROM test.users")
            cursor.execute("SELECT * FROM test.orders WHERE user_id = 1")
            lineage_analyzer.conn.commit()
        
        # Get expensive queries
        queries = lineage_analyzer.get_expensive_queries(limit=10)
        
        # There should be queries in pg_stat_statements now
        assert len(queries) > 0
        
        # Check the structure
        for query in queries:
            assert "query" in query
            if "calls" in query:  # Calls field might be named differently in different PostgreSQL versions
                assert isinstance(query["calls"], int) or isinstance(query["calls"], float)
    
    def test_get_table_dependencies(self, lineage_analyzer, postgres_service):
        """Test extracting table dependencies from SQL queries."""
        # Use queries that reference our test tables
        test_queries = [
            {
                'queryid': 1, 
                'query': 'SELECT * FROM test.users JOIN test.orders ON test.users.id = test.orders.user_id',
                'calls': 1,
                'total_time': 10.0,
                'mean_time': 10.0,
                'rows': 10
            },
            {
                'queryid': 2,
                'query': 'SELECT * FROM test.orders JOIN test.order_items ON test.orders.id = test.order_items.order_id',
                'calls': 1,
                'total_time': 5.0,
                'mean_time': 5.0,
                'rows': 10
            }
        ]
        
        # Get table dependencies
        dependencies = {}
        
        # Extract dependencies for each query separately
        for query in test_queries:
            source_tables, target_tables = lineage_analyzer.get_table_dependencies(query['query'])
            
            # Process source tables
            for table in source_tables:
                if table not in dependencies:
                    dependencies[table] = {"sources": [], "targets": []}
            
            # Process target tables
            for table in target_tables:
                if table not in dependencies:
                    dependencies[table] = {"sources": [], "targets": []}
                # Add source tables as dependencies for this target table
                for src_table in source_tables:
                    if src_table != table and src_table not in dependencies[table]["sources"]:
                        dependencies[table]["sources"].append(src_table)
                    # Also update the targets list for the source table
                    if table not in dependencies[src_table]["targets"]:
                        dependencies[src_table]["targets"].append(table)
        
        # Verify we found some dependencies
        assert len(dependencies) > 0
    
    def test_build_lineage_graph(self, lineage_analyzer, postgres_service):
        """Test building a lineage graph from dependencies."""
        # Create a test dependencies dictionary using our test tables
        dependencies = {
            "test.users": {
                "sources": [],
                "targets": ["test.orders"]
            },
            "test.orders": {
                "sources": ["test.users"],
                "targets": ["test.order_items"]
            },
            "test.order_items": {
                "sources": ["test.orders"],
                "targets": []
            }
        }
        
        # Build the graph
        graph = lineage_analyzer.build_lineage_graph(dependencies)
        
        # Verify the graph structure
        assert len(graph.nodes()) == 3
        
        # Verify edges (connections between tables)
        edges = list(graph.edges())
        nodes = list(graph.nodes())
        
        assert "test.users" in nodes
        assert "test.orders" in nodes
        assert "test.order_items" in nodes
    
    @patch('app.analyzer.plt')
    def test_visualize_lineage(self, mock_plt, lineage_analyzer, postgres_service):
        """Test visualizing the lineage graph."""
        # Create a test graph
        lineage_analyzer.lineage_graph.add_node("test.users", type="table")
        lineage_analyzer.lineage_graph.add_node("test.orders", type="table")
        lineage_analyzer.lineage_graph.add_node("test.order_items", type="table")
        lineage_analyzer.lineage_graph.add_edge("test.users", "test.orders")
        lineage_analyzer.lineage_graph.add_edge("test.orders", "test.order_items")
        
        # Configure mocks
        mock_plt.figure.return_value = MagicMock()
        mock_plt.savefig.return_value = None
        
        # Visualize without output file (returns base64 data)
        result = lineage_analyzer.visualize_lineage()
        
        # Verify savefig was called
        mock_plt.savefig.assert_called_once()
    
    def test_run_complete_analysis(self, lineage_analyzer, postgres_service):
        """Test the complete analysis workflow."""
        # Execute some test queries to populate pg_stat_statements
        with lineage_analyzer.conn.cursor() as cursor:
            # Simple query
            cursor.execute("SELECT * FROM test.users")
            
            # More complex query with JOINs
            cursor.execute("""
                SELECT u.name, o.order_date, oi.product_name, oi.quantity, oi.price
                FROM test.users u
                JOIN test.orders o ON u.id = o.user_id
                JOIN test.order_items oi ON o.id = oi.order_id
                WHERE u.id = 1
            """)
            
            lineage_analyzer.conn.commit()
        
        # Run the complete analysis
        results = lineage_analyzer.run_complete_analysis(limit=10)
        
        # Check that results contains the expected keys
        assert "files" in results
        assert "expensive_queries" in results