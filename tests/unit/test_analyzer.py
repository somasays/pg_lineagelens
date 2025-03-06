"""
Unit tests for the PostgresQueryLineage analyzer class.
"""
import pytest
import networkx as nx
from unittest.mock import patch, MagicMock, call

from app.analyzer import PostgresQueryLineage


class TestPostgresQueryLineage:
    """Test cases for the PostgresQueryLineage class."""

    def test_init(self):
        """Test initialization with different parameters."""
        # Test with default parameters
        analyzer = PostgresQueryLineage(
            host="localhost",
            database="testdb",
            user="postgres",
            password="password"
        )
        assert analyzer.host == "localhost"
        assert analyzer.database == "testdb"
        assert analyzer.user == "postgres"
        assert analyzer.password == "password"
        assert analyzer.port == 5432  # Default port
        assert analyzer.conn is None
        
        # Test with custom port
        analyzer = PostgresQueryLineage(
            host="localhost",
            database="testdb",
            user="postgres",
            password="password",
            port=5433
        )
        assert analyzer.port == 5433

    @patch('app.analyzer.psycopg2.connect')
    def test_connect_success(self, mock_connect):
        """Test successful database connection."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        analyzer = PostgresQueryLineage(
            host="localhost",
            database="testdb",
            user="postgres",
            password="password"
        )
        
        result = analyzer.connect()
        
        assert result is True
        assert analyzer.conn == mock_conn
        mock_connect.assert_called_once_with(
            host="localhost",
            database="testdb",
            user="postgres",
            password="password",
            port=5432
        )

    @patch('app.analyzer.psycopg2.connect')
    def test_connect_failure(self, mock_connect):
        """Test failed database connection."""
        from psycopg2 import OperationalError
        mock_connect.side_effect = OperationalError("Connection refused")
        
        analyzer = PostgresQueryLineage(
            host="localhost",
            database="testdb",
            user="postgres",
            password="password"
        )
        
        result = analyzer.connect()
        
        assert result is False
        assert analyzer.conn is None

    def test_disconnect(self):
        """Test database disconnection."""
        analyzer = PostgresQueryLineage(
            host="localhost",
            database="testdb",
            user="postgres",
            password="password"
        )
        
        # Setup mock connection
        mock_conn = MagicMock()
        analyzer.conn = mock_conn
        
        analyzer.disconnect()
        
        # Verify the connection was closed
        mock_conn.close.assert_called_once()
        assert analyzer.conn is None

    def test_check_pg_stat_statements(self, mock_db_connection):
        """Test checking for pg_stat_statements extension."""
        analyzer = PostgresQueryLineage(
            host="localhost",
            database="testdb",
            user="postgres",
            password="password"
        )
        analyzer.conn = mock_db_connection
        cursor_mock = mock_db_connection.cursor.return_value
        
        # Test when extension exists
        cursor_mock.fetchone.return_value = ('1',)
        result = analyzer.check_pg_stat_statements()
        assert result is True
        
        # Test when extension doesn't exist
        cursor_mock.fetchone.return_value = None
        result = analyzer.check_pg_stat_statements()
        assert result is False

    def test_get_expensive_queries(self, mock_db_connection, sample_queries):
        """Test retrieving expensive queries."""
        analyzer = PostgresQueryLineage(
            host="localhost",
            database="testdb",
            user="postgres",
            password="password"
        )
        analyzer.conn = mock_db_connection
        cursor_mock = mock_db_connection.cursor.return_value
        
        # Mock the query result
        cursor_mock.fetchall.return_value = [
            (1, 'SELECT * FROM users JOIN orders ON users.id = orders.user_id', 100, 1000.0, 10.0, 1000),
            (2, 'INSERT INTO audit_log ...', 50, 500.0, 10.0, 500),
            (3, 'UPDATE products ...', 200, 2000.0, 10.0, 10)
        ]
        
        result = analyzer.get_expensive_queries(limit=10)
        
        assert len(result) == 3
        assert result[0]['queryid'] == 1
        assert 'SELECT * FROM users' in result[0]['query']
        assert result[0]['calls'] == 100
        
        # Test with different sorting and limit
        result = analyzer.get_expensive_queries(sort_by="calls", limit=2)
        assert len(result) == 3  # Would be 2 in real implementation, but we're mocking the DB call

    @patch('app.analyzer.sqlparse.parse')
    def test_get_table_dependencies(self, mock_parse, sample_queries):
        """Test extracting table dependencies from queries."""
        analyzer = PostgresQueryLineage(
            host="localhost",
            database="testdb",
            user="postgres",
            password="password"
        )
        
        # Setup mock parsing results
        mock_statements = [
            MagicMock(),  # For SELECT query
            MagicMock(),  # For INSERT query
            MagicMock()   # For UPDATE query
        ]
        mock_parse.side_effect = [[stmt] for stmt in mock_statements]
        
        # First query: SELECT * FROM users JOIN orders ON users.id = orders.user_id
        mock_statements[0].get_type.return_value = "SELECT"
        mock_table_refs_1 = [MagicMock(), MagicMock()]
        mock_table_refs_1[0].get_real_name.return_value = "users"
        mock_table_refs_1[1].get_real_name.return_value = "orders"
        mock_statements[0].get_tables.return_value = mock_table_refs_1
        
        # Second query: INSERT INTO audit_log ... SELECT FROM users
        mock_statements[1].get_type.return_value = "INSERT"
        mock_insert_target = MagicMock()
        mock_insert_target.get_real_name.return_value = "audit_log"
        mock_statements[1].get_insert_target.return_value = mock_insert_target
        mock_table_refs_2 = [MagicMock()]
        mock_table_refs_2[0].get_real_name.return_value = "users"
        mock_statements[1].get_tables.return_value = mock_table_refs_2
        
        # Third query: UPDATE products SET ... WHERE id IN (SELECT FROM order_items)
        mock_statements[2].get_type.return_value = "UPDATE"
        mock_update_target = MagicMock()
        mock_update_target.get_real_name.return_value = "products"
        mock_statements[2].get_update_target.return_value = mock_update_target
        mock_table_refs_3 = [MagicMock(), MagicMock()]
        mock_table_refs_3[0].get_real_name.return_value = "products"
        mock_table_refs_3[1].get_real_name.return_value = "order_items"
        mock_statements[2].get_tables.return_value = mock_table_refs_3
        
        dependencies = analyzer.get_table_dependencies(sample_queries)
        
        # Expected dependencies: 
        # - users depends on orders (SELECT)
        # - audit_log depends on users (INSERT)
        # - products depends on order_items (UPDATE)
        assert "users" in dependencies
        assert "orders" in dependencies["users"]["sources"]
        assert "audit_log" in dependencies
        assert "users" in dependencies["audit_log"]["sources"]
        assert "products" in dependencies
        assert "order_items" in dependencies["products"]["sources"]

    def test_build_lineage_graph(self, sample_tables):
        """Test building the lineage graph."""
        analyzer = PostgresQueryLineage(
            host="localhost",
            database="testdb",
            user="postgres",
            password="password"
        )
        
        # Create test dependencies dictionary
        dependencies = {
            "users": {
                "sources": ["orders", "audit_log"],
                "targets": []
            },
            "orders": {
                "sources": ["order_items"],
                "targets": ["users"]
            },
            "order_items": {
                "sources": ["products"],
                "targets": ["orders"]
            },
            "products": {
                "sources": [],
                "targets": ["order_items"]
            },
            "audit_log": {
                "sources": [],
                "targets": ["users"]
            }
        }
        
        # Build the graph
        graph, pos = analyzer.build_lineage_graph(dependencies)
        
        # Verify the graph structure
        assert isinstance(graph, nx.DiGraph)
        assert len(graph.nodes()) == 5  # 5 tables
        assert len(graph.edges()) == 5  # 5 dependencies
        
        # Check edges
        assert ("orders", "users") in graph.edges()
        assert ("audit_log", "users") in graph.edges()
        assert ("order_items", "orders") in graph.edges()
        assert ("products", "order_items") in graph.edges()

    @patch('app.analyzer.plt')
    @patch('app.analyzer.nx.draw_networkx_nodes')
    @patch('app.analyzer.nx.draw_networkx_edges')
    @patch('app.analyzer.nx.draw_networkx_labels')
    def test_visualize_lineage(self, mock_draw_labels, mock_draw_edges, mock_draw_nodes, mock_plt):
        """Test visualizing the lineage graph."""
        analyzer = PostgresQueryLineage(
            host="localhost",
            database="testdb",
            user="postgres",
            password="password"
        )
        
        # Create test graph and positions
        graph = nx.DiGraph()
        graph.add_nodes_from(["users", "orders", "order_items", "products", "audit_log"])
        graph.add_edges_from([
            ("orders", "users"),
            ("audit_log", "users"),
            ("order_items", "orders"),
            ("products", "order_items")
        ])
        
        pos = {
            "users": (0, 0),
            "orders": (1, 0),
            "order_items": (2, 0),
            "products": (3, 0),
            "audit_log": (4, 0)
        }
        
        # Configure mocks
        mock_plt.figure.return_value = MagicMock()
        mock_plt.savefig.return_value = None
        
        # Test visualization
        output_file = analyzer.visualize_lineage(graph, pos)
        
        # Verify figure creation and configuration
        mock_plt.figure.assert_called_once()
        mock_draw_nodes.assert_called_once()
        mock_draw_edges.assert_called_once()
        mock_draw_labels.assert_called_once()
        mock_plt.savefig.assert_called_once()
        assert output_file.endswith(".svg")
        
    def test_get_table_columns(self, mock_db_connection):
        """Test retrieving table columns."""
        analyzer = PostgresQueryLineage(
            host="localhost",
            database="testdb",
            user="postgres",
            password="password"
        )
        analyzer.conn = mock_db_connection
        cursor_mock = mock_db_connection.cursor.return_value
        
        # Mock query results
        cursor_mock.fetchall.return_value = [
            ("id", "integer"),
            ("name", "character varying"),
            ("email", "character varying"),
            ("created_at", "timestamp")
        ]
        
        columns = analyzer.get_table_columns("users")
        
        assert len(columns) == 4
        assert columns[0] == {"name": "id", "type": "integer"}
        assert columns[1] == {"name": "name", "type": "character varying"}
        assert columns[3] == {"name": "created_at", "type": "timestamp"}