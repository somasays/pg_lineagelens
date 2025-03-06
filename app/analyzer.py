"""
PostgreSQL Query Analyzer for building data lineage.
Uses PostgreSQL system catalogs and statistics to analyze expensive queries
and build table dependency graphs.
"""

import re
import pandas as pd
import networkx as nx
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import psycopg2
from sqlparse import parse, tokens
from sqlparse.sql import IdentifierList, Identifier
from datetime import datetime
import os
import tempfile


class PostgresQueryLineage:
    def __init__(self, connection_params):
        """
        Initialize the PostgreSQL connection for query analysis and lineage tracking.
        
        Args:
            connection_params (dict): Connection parameters for PostgreSQL
                (host, database, user, password, port)
        """
        self.connection_params = connection_params
        self.conn = None
        self.cursor = None
        self.lineage_graph = nx.DiGraph()
    
    def connect(self):
        """Establish connection to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(**self.connection_params)
            self.cursor = self.conn.cursor()
            return True, "Connected to PostgreSQL database successfully."
        except Exception as e:
            return False, f"Error connecting to PostgreSQL database: {str(e)}"
    
    def disconnect(self):
        """Close connection to PostgreSQL database"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def check_pg_stat_statements(self):
        """Check if pg_stat_statements extension is installed and available"""
        try:
            self.cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'")
            if not self.cursor.fetchone():
                return False, "pg_stat_statements extension is not installed. Run 'CREATE EXTENSION pg_stat_statements;' as a superuser."
            
            # Check if current user has access to pg_stat_statements
            try:
                self.cursor.execute("SELECT query FROM pg_stat_statements LIMIT 1")
                self.cursor.fetchone()
                return True, "pg_stat_statements is available and accessible."
            except Exception as e:
                return False, f"Cannot access pg_stat_statements: {str(e)}"
                
        except Exception as e:
            return False, f"Error checking pg_stat_statements: {str(e)}"
    
    def get_expensive_queries(self, limit=20, min_calls=5, sort_by='total_time'):
        """
        Get the most expensive queries from pg_stat_statements.
        
        Args:
            limit (int): Number of queries to return
            min_calls (int): Minimum number of calls to include query
            sort_by (str): Column to sort by ('total_time', 'mean_time', 'calls', etc.)
        
        Returns:
            pandas.DataFrame: DataFrame with query statistics
        """
        if not self.conn or self.conn.closed:
            success, msg = self.connect()
            if not success:
                return pd.DataFrame()
        
        # Check for pg_stat_statements
        success, msg = self.check_pg_stat_statements()
        if not success:
            print(f"WARNING: {msg}")
            return pd.DataFrame()
        
        # Determine which version of pg_stat_statements we're using
        self.cursor.execute("SELECT current_setting('server_version_num')::int")
        pg_version = int(self.cursor.fetchone()[0])
        
        # Different columns in different PostgreSQL versions
        # First check if io_time exists in pg_stat_statements
        has_io_time = False
        try:
            # Try a query that directly tests if the io_time column exists
            self.cursor.execute("SELECT 1 FROM pg_stat_statements LIMIT 0")
            column_names = [desc[0] for desc in self.cursor.description]
            has_io_time = 'io_time' in column_names
        except Exception as e:
            print(f"Warning when checking for io_time column: {e}")
            has_io_time = False

        # First get a list of system schemas to exclude
        try:
            self.cursor.execute("""
            SELECT nspname FROM pg_namespace 
            WHERE nspname IN ('pg_catalog', 'information_schema', 'pg_toast') 
               OR nspname LIKE 'pg_%temp_%'
            """)
            system_schemas = [row[0] for row in self.cursor.fetchall()]
            system_schemas_str = ', '.join(f"'{schema}'" for schema in system_schemas)
            
            # Get list of user tables to include
            self.cursor.execute(f"""
            SELECT schemaname, tablename
            FROM pg_tables
            WHERE schemaname NOT IN ({system_schemas_str})
            """)
            user_tables = [f"{row[0]}.{row[1]}" for row in self.cursor.fetchall()]
            
            # Make sure we have found some user tables
            if user_tables:
                # Create regex pattern for user tables
                # This will match queries that include user table names
                table_pattern = '|'.join(re.escape(table.split('.')[-1]) for table in user_tables)
            else:
                print("No user tables found, falling back to including all tables")
                table_pattern = '.*'  # Match any table if no user tables were found
                
            system_schema_pattern = '|'.join(re.escape(schema) for schema in system_schemas)
        except Exception as e:
            print(f"Warning when getting user tables: {e}")
            table_pattern = '.*'  # Match any table if we can't get the user tables
            system_schema_pattern = 'pg_catalog|information_schema'
            
        if pg_version >= 130000:  # PostgreSQL 13+
            if has_io_time:
                query = f"""
                SELECT 
                    query, 
                    calls, 
                    total_exec_time as total_time, 
                    mean_exec_time as mean_time, 
                    rows, 
                    shared_blks_hit,
                    shared_blks_read,
                    temp_blks_written,
                    io_time
                FROM pg_stat_statements
                WHERE calls >= {min_calls}
                  AND query ~* '({table_pattern})'
                  AND query !~* '^(SHOW|SET|BEGIN|COMMIT|ROLLBACK)'
                  AND query !~* '({system_schema_pattern})\\.'
                ORDER BY {sort_by} DESC
                LIMIT {limit}
                """
            else:
                query = f"""
                SELECT 
                    query, 
                    calls, 
                    total_exec_time as total_time, 
                    mean_exec_time as mean_time, 
                    rows, 
                    shared_blks_hit,
                    shared_blks_read,
                    temp_blks_written,
                    0 as io_time
                FROM pg_stat_statements
                WHERE calls >= {min_calls}
                  AND query ~* '({table_pattern})'
                  AND query !~* '^(SHOW|SET|BEGIN|COMMIT|ROLLBACK)'
                  AND query !~* '({system_schema_pattern})\\.'
                ORDER BY {sort_by} DESC
                LIMIT {limit}
                """
        else:  # PostgreSQL 9.6 - 12
            # Check if blk_read_time and blk_write_time exist
            has_blk_read_time = False
            has_blk_write_time = False
            try:
                # Try a query that directly tests if these columns exist
                self.cursor.execute("SELECT 1 FROM pg_stat_statements LIMIT 0")
                column_names = [desc[0] for desc in self.cursor.description]
                has_blk_read_time = 'blk_read_time' in column_names
                has_blk_write_time = 'blk_write_time' in column_names
            except Exception as e:
                print(f"Warning when checking for blk_read_time/blk_write_time columns: {e}")
                has_blk_read_time = False
                has_blk_write_time = False
            
            if has_blk_read_time and has_blk_write_time:
                query = f"""
                SELECT 
                    query, 
                    calls, 
                    total_time, 
                    mean_time, 
                    rows, 
                    shared_blks_hit,
                    shared_blks_read,
                    temp_blks_written,
                    COALESCE(blk_read_time + blk_write_time, 0) as io_time
                FROM pg_stat_statements
                WHERE calls >= {min_calls}
                  AND query ~* '({table_pattern})'
                  AND query !~* '^(SHOW|SET|BEGIN|COMMIT|ROLLBACK)'
                  AND query !~* '({system_schema_pattern})\\.'
                ORDER BY {sort_by} DESC
                LIMIT {limit}
                """
            else:
                query = f"""
                SELECT 
                    query, 
                    calls, 
                    total_time, 
                    mean_time, 
                    rows, 
                    shared_blks_hit,
                    shared_blks_read,
                    temp_blks_written,
                    0 as io_time
                FROM pg_stat_statements
                WHERE calls >= {min_calls}
                  AND query ~* '({table_pattern})'
                  AND query !~* '^(SHOW|SET|BEGIN|COMMIT|ROLLBACK)'
                  AND query !~* '({system_schema_pattern})\\.'
                ORDER BY {sort_by} DESC
                LIMIT {limit}
                """
        
        try:
            self.cursor.execute(query)
            columns = [desc[0] for desc in self.cursor.description]
            results = self.cursor.fetchall()
            
            # Create DataFrame
            df = pd.DataFrame(results, columns=columns)
            
            # Additional Python-side filtering to exclude system queries
            # This is a safeguard in case the SQL filters weren't sufficient
            if not df.empty:
                # Get all system schemas for additional filtering
                system_schemas = ['pg_catalog', 'information_schema', 'pg_toast']
                
                # Filter out queries that are clearly system queries
                df = df[~df['query'].str.contains('pg_|information_schema|pg_toast', case=False, regex=True)]
                
                # Filter out transaction management and administrative commands
                admin_patterns = [
                    r'^BEGIN', r'^COMMIT', r'^ROLLBACK', r'^SET ', r'^SHOW ', 
                    r'^CREATE TEMP', r'^DROP TEMP', r'^VACUUM', r'^ANALYZE'
                ]
                for pattern in admin_patterns:
                    df = df[~df['query'].str.contains(pattern, case=False, regex=True)]
                
                # Add additional metrics
                df['time_per_row'] = df['total_time'] / df['rows'].replace(0, 1)  # Avoid division by zero
                # Avoid division by zero for io_percentage
                df['io_percentage'] = df.apply(
                    lambda row: (row['io_time'] / row['total_time']) * 100 if row['total_time'] > 0 else 0, 
                    axis=1
                )
            
            return df
        except Exception as e:
            print(f"Error retrieving expensive queries: {e}")
            return pd.DataFrame()
    
    def get_table_dependencies(self, query_text):
        """
        Parse a SQL query to extract source and destination tables.
        
        Args:
            query_text (str): SQL query text
            
        Returns:
            tuple: (source_tables, destination_tables)
        """
        if not query_text or not isinstance(query_text, str):
            return [], []
            
        # Normalize query text
        query_text = query_text.strip().lower()
        
        # Parse the query using sqlparse
        try:
            parsed = parse(query_text)[0]
        except IndexError:
            return [], []
        
        # Extract destination tables (INSERT INTO, UPDATE, CREATE TABLE AS, etc.)
        destination_tables = []
        source_tables = []
        
        # Check query type
        query_type = None
        for token in parsed.tokens:
            if token.ttype is tokens.DML:
                query_type = token.value.upper()
                break
        
        # Process based on query type
        if query_type == 'SELECT':
            # For subqueries (CREATE TABLE AS SELECT, INSERT INTO ... SELECT)
            create_pattern = r'create\s+table\s+(\w+(?:\.\w+)?)'
            insert_pattern = r'insert\s+into\s+(\w+(?:\.\w+)?)'
            
            create_match = re.search(create_pattern, query_text)
            insert_match = re.search(insert_pattern, query_text)
            
            if create_match:
                destination_tables.append(create_match.group(1))
            if insert_match:
                destination_tables.append(insert_match.group(1))
            
            # Extract source tables from FROM clause
            from_seen = False
            join_seen = False
            
            for token in parsed.tokens:
                if token.is_keyword and token.value.upper() == 'FROM':
                    from_seen = True
                    continue
                
                if from_seen and not token.is_whitespace:
                    if isinstance(token, IdentifierList):
                        for identifier in token.get_identifiers():
                            source_tables.append(str(identifier).strip())
                    elif isinstance(token, Identifier):
                        source_tables.append(str(token).strip())
                    from_seen = False
                
                if token.is_keyword and token.value.upper() in ('JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN'):
                    join_seen = True
                    continue
                
                if join_seen and not token.is_whitespace:
                    if isinstance(token, Identifier):
                        source_tables.append(str(token).strip())
                    join_seen = False
        
        elif query_type == 'INSERT':
            # Extract destination table
            insert_into_seen = False
            for token in parsed.tokens:
                if token.is_keyword and token.value.upper() == 'INTO':
                    insert_into_seen = True
                    continue
                
                if insert_into_seen and not token.is_whitespace:
                    if isinstance(token, Identifier):
                        destination_tables.append(str(token).strip())
                    insert_into_seen = False
                    break
            
            # Check if it's INSERT ... SELECT
            select_seen = False
            from_seen = False
            for token in parsed.tokens:
                if token.is_keyword and token.value.upper() == 'SELECT':
                    select_seen = True
                
                if select_seen and token.is_keyword and token.value.upper() == 'FROM':
                    from_seen = True
                    continue
                
                if from_seen and not token.is_whitespace:
                    if isinstance(token, IdentifierList):
                        for identifier in token.get_identifiers():
                            source_tables.append(str(identifier).strip())
                    elif isinstance(token, Identifier):
                        source_tables.append(str(token).strip())
                    from_seen = False
        
        elif query_type == 'UPDATE':
            # Extract destination table
            update_seen = True  # Because we already identified UPDATE keyword
            for token in parsed.tokens:
                if update_seen and not token.is_whitespace:
                    if isinstance(token, Identifier):
                        destination_tables.append(str(token).strip())
                    update_seen = False
                    break
            
            # Check for tables in FROM clause if any
            from_seen = False
            for token in parsed.tokens:
                if token.is_keyword and token.value.upper() == 'FROM':
                    from_seen = True
                    continue
                
                if from_seen and not token.is_whitespace:
                    if isinstance(token, IdentifierList):
                        for identifier in token.get_identifiers():
                            source_tables.append(str(identifier).strip())
                    elif isinstance(token, Identifier):
                        source_tables.append(str(token).strip())
                    from_seen = False
        
        # Clean up table names
        destination_tables = [self._clean_table_name(t) for t in destination_tables]
        source_tables = [self._clean_table_name(t) for t in source_tables]
        
        # Remove destination tables from source tables (if they appear in both)
        source_tables = [t for t in source_tables if t not in destination_tables]
        
        return source_tables, destination_tables
    
    def _clean_table_name(self, table_name):
        """Clean up table name by removing aliases and quotes"""
        # Remove table alias if present
        if ' as ' in table_name:
            table_name = table_name.split(' as ')[0].strip()
        elif ' ' in table_name:
            # Simple case where alias follows table without AS keyword
            table_name = table_name.split(' ')[0].strip()
        
        # Remove quotes
        table_name = table_name.strip('"\'')
        
        return table_name
    
    def build_lineage_graph(self, expensive_queries_df):
        """
        Build a data lineage graph from the expensive queries
        
        Args:
            expensive_queries_df (pandas.DataFrame): DataFrame with expensive queries
            
        Returns:
            networkx.DiGraph: Data lineage graph
        """
        if expensive_queries_df.empty:
            return nx.DiGraph()
        
        # Create a new graph
        G = nx.DiGraph()
        
        # Process each query to build the graph
        for _, row in expensive_queries_df.iterrows():
            query_text = row['query']
            
            # Extract tables
            source_tables, destination_tables = self.get_table_dependencies(query_text)
            
            # Add query as node with attributes
            query_id = f"Query_{hash(query_text) % 10000}"  # Create a shorter hash for display
            G.add_node(query_id, 
                      type='query',
                      text=query_text[:100] + '...' if len(query_text) > 100 else query_text,
                      calls=row['calls'],
                      total_time=row['total_time'],
                      mean_time=row['mean_time'],
                      rows=row['rows'])
            
            # Add source tables as nodes and connect to query
            for table in source_tables:
                if table and len(table) > 0:  # Skip empty tables
                    # Only get columns if node doesn't exist yet
                    if table not in G:
                        columns = self.get_table_columns(table)
                        # Get schema name
                        schema = 'public'
                        if '.' in table:
                            schema = table.split('.')[0]
                        
                        G.add_node(table, 
                                 type='table', 
                                 columns=columns,
                                 schema=schema,
                                 display_name=table.split('.')[-1] if '.' in table else table)
                    G.add_edge(table, query_id)
            
            # Add destination tables as nodes and connect from query
            for table in destination_tables:
                if table and len(table) > 0:  # Skip empty tables
                    # Only get columns if node doesn't exist yet
                    if table not in G:
                        columns = self.get_table_columns(table)
                        # Get schema name
                        schema = 'public'
                        if '.' in table:
                            schema = table.split('.')[0]
                            
                        G.add_node(table, 
                                 type='table',
                                 columns=columns,
                                 schema=schema,
                                 display_name=table.split('.')[-1] if '.' in table else table)
                    G.add_edge(query_id, table)
        
        # Create direct table-to-table relationships for better lineage visualization
        # This adds edges between tables that are connected through queries
        # For each query node that has both incoming and outgoing edges
        for node in G.nodes():
            # Only process query nodes that act as intermediaries
            if G.nodes[node].get('type') == 'query':
                # Get source tables (predecessors of the query)
                source_tables = [pred for pred in G.predecessors(node) 
                               if G.nodes[pred].get('type') == 'table']
                
                # Get destination tables (successors of the query)
                dest_tables = [succ for succ in G.successors(node)
                             if G.nodes[succ].get('type') == 'table']
                
                # Create direct edges from each source table to each destination table
                for src_table in source_tables:
                    for dst_table in dest_tables:
                        # Add a direct edge from source to destination table
                        # This represents the data lineage relationship
                        G.add_edge(src_table, dst_table, via_query=node)
        
        self.lineage_graph = G
        return G
    
    def visualize_lineage(self, output_file=None):
        """
        Visualize the data lineage graph
        
        Args:
            output_file (str, optional): File path to save the visualization
            
        Returns:
            str: Base64 encoded image data if output_file is None
        """
        if self.lineage_graph.number_of_nodes() == 0:
            print("No lineage graph to visualize.")
            return None
        
        plt.figure(figsize=(15, 10))
        
        # Define node colors based on type
        node_colors = []
        for node in self.lineage_graph.nodes():
            if self.lineage_graph.nodes[node].get('type') == 'query':
                node_colors.append('lightblue')
            else:
                node_colors.append('lightgreen')
        
        # Define node sizes based on query statistics if available
        node_sizes = []
        for node in self.lineage_graph.nodes():
            if self.lineage_graph.nodes[node].get('type') == 'query':
                # Scale by total_time
                total_time = self.lineage_graph.nodes[node].get('total_time', 0)
                node_sizes.append(100 + min(total_time / 10, 1000))
            else:
                node_sizes.append(300)
        
        # Create labels
        labels = {}
        for node in self.lineage_graph.nodes():
            if self.lineage_graph.nodes[node].get('type') == 'query':
                # Short representation for queries
                text = self.lineage_graph.nodes[node].get('text', '')
                text = text.replace('\n', ' ')
                labels[node] = f"{node}\n({text[:30]}...)" if len(text) > 30 else f"{node}\n({text})"
            else:
                labels[node] = node
        
        # Draw the graph
        pos = nx.spring_layout(self.lineage_graph, k=0.15, iterations=50)
        
        nx.draw_networkx_nodes(self.lineage_graph, pos, node_size=node_sizes, node_color=node_colors, alpha=0.8)
        nx.draw_networkx_edges(self.lineage_graph, pos, width=1.0, alpha=0.5, edge_color='gray', arrowsize=15)
        nx.draw_networkx_labels(self.lineage_graph, pos, labels=labels, font_size=8)
        
        plt.title("PostgreSQL Data Lineage Graph")
        plt.axis('off')
        
        if output_file:
            plt.savefig(output_file, bbox_inches='tight')
            plt.close()
            return output_file
        else:
            # Return as base64 encoded image
            img_data = BytesIO()
            plt.savefig(img_data, format='png', bbox_inches='tight')
            plt.close()
            img_data.seek(0)
            return base64.b64encode(img_data.read()).decode('utf-8')
    
    def export_lineage(self, output_file):
        """
        Export the lineage graph to a file in GraphML format
        
        Args:
            output_file (str): File path to save the lineage graph
        """
        if self.lineage_graph.number_of_nodes() == 0:
            print("No lineage graph to export.")
            return False
        
        try:
            # Create a copy of the graph to modify for export
            export_graph = self.lineage_graph.copy()
            
            # Convert non-serializable attributes to serializable format
            for node, attrs in export_graph.nodes(data=True):
                # Convert columns list to JSON string
                if 'columns' in attrs:
                    import json
                    attrs['columns'] = json.dumps(attrs['columns'])
            
            nx.write_graphml(export_graph, output_file)
            return True
        except Exception as e:
            print(f"Error exporting lineage graph: {e}")
            return False

    def get_table_columns(self, table_name):
        """
        Get columns for a specific table
        
        Args:
            table_name (str): Table name in format schema.table or just table
            
        Returns:
            list: List of column information dictionaries
        """
        if not self.conn or self.conn.closed:
            success, msg = self.connect()
            if not success:
                return []
                
        try:
            # Split schema and table
            if '.' in table_name:
                schema, table = table_name.split('.', 1)
            else:
                schema = 'public'
                table = table_name
                
            # Get column information
            self.cursor.execute("""
                SELECT 
                    a.attname as column_name,
                    pg_catalog.format_type(a.atttypid, a.atttypmod) as data_type,
                    a.attnotnull as not_null,
                    CASE 
                        WHEN (SELECT COUNT(*) FROM pg_constraint
                            WHERE conrelid = a.attrelid AND conkey[1] = a.attnum AND contype = 'p') > 0 THEN true
                        ELSE false
                    END as is_primary_key
                FROM pg_catalog.pg_attribute a
                JOIN pg_catalog.pg_class c ON a.attrelid = c.oid
                JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
                WHERE c.relname = %s
                    AND n.nspname = %s
                    AND a.attnum > 0
                    AND NOT a.attisdropped
                ORDER BY a.attnum
            """, (table, schema))
            
            columns = []
            for row in self.cursor.fetchall():
                columns.append({
                    'name': row[0],
                    'type': row[1],
                    'not_null': row[2],
                    'is_primary_key': row[3]
                })
            
            return columns
            
        except Exception as e:
            print(f"Error getting columns for {table_name}: {e}")
            return []
            
    def get_table_query_stats(self):
        """
        Get statistics about which tables are most frequently queried
        
        Returns:
            pandas.DataFrame: DataFrame with table statistics
        """
        if self.lineage_graph.number_of_nodes() == 0:
            print("No lineage graph to analyze.")
            return pd.DataFrame()
        
        table_stats = {}
        
        for node in self.lineage_graph.nodes():
            if self.lineage_graph.nodes[node].get('type') == 'table':
                # Count incoming and outgoing queries
                in_queries = list(self.lineage_graph.predecessors(node))
                out_queries = list(self.lineage_graph.successors(node))
                
                # Calculate total time spent on this table
                total_read_time = sum(self.lineage_graph.nodes[q].get('total_time', 0) for q in in_queries)
                total_write_time = sum(self.lineage_graph.nodes[q].get('total_time', 0) for q in out_queries)
                
                # Get columns for this table
                columns = self.get_table_columns(node)
                
                table_stats[node] = {
                    'table_name': node,
                    'read_queries': len(in_queries),
                    'write_queries': len(out_queries),
                    'total_queries': len(in_queries) + len(out_queries),
                    'total_read_time': total_read_time,
                    'total_write_time': total_write_time,
                    'total_time': total_read_time + total_write_time,
                    'columns': columns
                }
        
        df = pd.DataFrame(list(table_stats.values()))
        if not df.empty:
            return df.sort_values('total_time', ascending=False)
        return df

    def run_complete_analysis(self, limit=20, min_calls=5, output_prefix=None):
        """
        Run a complete analysis and generate reports
        
        Args:
            limit (int): Number of expensive queries to analyze
            min_calls (int): Minimum number of calls to include query
            output_prefix (str, optional): Prefix for output files
        
        Returns:
            dict: Analysis results
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_prefix:
            prefix = f"{output_prefix}_{timestamp}"
        else:
            prefix = f"pg_lineage_{timestamp}"
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(prefix)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Connect to database
        success, msg = self.connect()
        if not success:
            return {'error': msg}
        
        try:
            # Get expensive queries
            expensive_queries = self.get_expensive_queries(limit=limit, min_calls=min_calls)
            
            if expensive_queries.empty:
                return {'error': "No queries found for analysis. Check pg_stat_statements is enabled and collecting data."}
            
            # Save expensive queries to CSV
            queries_file = f"{prefix}_expensive_queries.csv"
            expensive_queries.to_csv(queries_file, index=False)
            
            # Build lineage graph
            self.build_lineage_graph(expensive_queries)
            
            # Get table statistics
            table_stats = self.get_table_query_stats()
            table_stats_file = f"{prefix}_table_stats.csv"
            if not table_stats.empty:
                table_stats.to_csv(table_stats_file, index=False)
            
            # Visualize lineage
            lineage_image = f"{prefix}_lineage.png"
            self.visualize_lineage(lineage_image)
            
            # Export lineage graph
            lineage_graphml = f"{prefix}_lineage.graphml"
            self.export_lineage(lineage_graphml)
            
            return {
                'expensive_queries': expensive_queries,
                'table_stats': table_stats,
                'lineage_graph': self.lineage_graph,
                'files': {
                    'expensive_queries': queries_file,
                    'table_stats': table_stats_file,
                    'lineage_image': lineage_image,
                    'lineage_graphml': lineage_graphml
                }
            }
        
        except Exception as e:
            return {'error': f"Error during analysis: {str(e)}"}
        
        finally:
            # Disconnect from database
            self.disconnect()