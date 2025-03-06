"""
Route definitions for the PostgreSQL Data Lineage application.
"""

import os
import json
import base64
from flask import render_template, request, jsonify, send_file, redirect, url_for, session, flash
import pandas as pd

from app import app
from app.analyzer import PostgresQueryLineage

# Dictionary to store analysis results during session
@app.route('/')
def index():
    """Render the main dashboard page"""
    return render_template('index.html', version="1.0.0")

@app.route('/connect', methods=['POST'])
def connect():
    """Connect to a PostgreSQL database"""
    try:
        # Get connection parameters from form
        connection_params = {
            'host': request.form.get('host', 'localhost'),
            'database': request.form.get('database'),
            'user': request.form.get('user'),
            'password': request.form.get('password'),
            'port': int(request.form.get('port', 5432))
        }
        
        # Test connection
        lineage_tracker = PostgresQueryLineage(connection_params)
        success, message = lineage_tracker.connect()
        
        if success:
            # Store connection parameters in session
            session['connection_params'] = connection_params
            session.modified = True
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Connection error: {str(e)}'})

@app.route('/analyze', methods=['POST'])
def analyze():
    """Run the lineage analysis"""
    if 'connection_params' not in session:
        return jsonify({'success': False, 'message': 'Not connected to a database'})
    
    try:
        # Get analysis parameters
        limit = int(request.form.get('limit', 20))
        min_calls = int(request.form.get('min_calls', 5))
        
        # Create lineage tracker
        lineage_tracker = PostgresQueryLineage(session['connection_params'])
        
        # Run analysis
        results = lineage_tracker.run_complete_analysis(
            limit=limit,
            min_calls=min_calls,
            output_prefix=os.path.join(app.config['UPLOAD_FOLDER'], 'analysis')
        )
        
        if 'error' in results:
            return jsonify({'success': False, 'message': results['error']})
        
        # Store results in session (store file paths only)
        session['analysis_files'] = results.get('files', {})
        session['has_results'] = True
        session.modified = True
        
        # Create base64 image of the lineage graph for display
        img_data = None
        if 'lineage_image' in results['files'] and os.path.exists(results['files']['lineage_image']):
            with open(results['files']['lineage_image'], 'rb') as img_file:
                img_data = base64.b64encode(img_file.read()).decode('utf-8')
        
        return jsonify({
            'success': True,
            'message': 'Analysis completed successfully',
            'queries_count': len(results['expensive_queries']),
            'tables_count': len(results['table_stats']) if not results['table_stats'].empty else 0,
            'lineage_image': img_data
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Analysis error: {str(e)}'})

@app.route('/expensive_queries')
def expensive_queries():
    """Display expensive queries data"""
    if 'has_results' not in session or 'analysis_files' not in session:
        flash('No analysis results available. Please run an analysis first.', 'warning')
        return redirect(url_for('index'))
    
    # Read the CSV file
    file_path = session['analysis_files'].get('expensive_queries')
    if not file_path or not os.path.exists(file_path):
        flash('Expensive queries data not found.', 'danger')
        return redirect(url_for('index'))
    
    # Load data from CSV
    df = pd.read_csv(file_path)
    
    return render_template(
        'expensive_queries.html',
        queries=df.to_dict('records'),
        columns=df.columns.tolist()
    )

@app.route('/table_stats')
def table_stats():
    """Display table statistics data"""
    if 'has_results' not in session or 'analysis_files' not in session:
        flash('No analysis results available. Please run an analysis first.', 'warning')
        return redirect(url_for('index'))
    
    # Read the CSV file
    file_path = session['analysis_files'].get('table_stats')
    if not file_path or not os.path.exists(file_path):
        flash('Table statistics data not found.', 'danger')
        return redirect(url_for('index'))
    
    # Load data from CSV
    df = pd.read_csv(file_path)
    
    return render_template(
        'table_stats.html',
        stats=df.to_dict('records'),
        columns=df.columns.tolist()
    )

@app.route('/lineage')
def lineage():
    """Display the lineage graph"""
    if 'has_results' not in session or 'analysis_files' not in session:
        flash('No lineage data available. Please run an analysis from the home page first.', 'warning')
        return redirect(url_for('index'))
    
    # Get the GraphML file path
    graphml_path = session['analysis_files'].get('lineage_graphml')
    
    # Also keep the image as a fallback
    img_path = session['analysis_files'].get('lineage_image')
    img_data = None
    if img_path and os.path.exists(img_path):
        with open(img_path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode('utf-8')
    
    # Initialize D3 visualization data
    d3_data = {
        'nodes': [],
        'links': []
    }
    
    try:
        # Read expensive queries data
        queries_file = session['analysis_files'].get('expensive_queries')
        if queries_file and os.path.exists(queries_file):
            df_queries = pd.read_csv(queries_file)
            
            # Load the GraphML file to get the graph structure
            if graphml_path and os.path.exists(graphml_path):
                import networkx as nx
                G = nx.read_graphml(graphml_path)
                
                # Create D3 nodes and links
                for node_id, attrs in G.nodes(data=True):
                    node_type = attrs.get('type', 'unknown')
                    node_data = {
                        'id': node_id,
                        'type': node_type
                    }
                    
                    if node_type == 'table':
                        # Extract schema and table name
                        if '.' in node_id:
                            schema, table_name = node_id.split('.', 1)
                        else:
                            schema = 'public'
                            table_name = node_id
                        
                        # Count connected queries
                        in_queries = list(G.predecessors(node_id))  # queries that write to this table
                        out_queries = list(G.successors(node_id))   # queries that read from this table
                        
                        # Parse columns if they exist as JSON string
                        columns = []
                        if 'columns' in attrs:
                            try:
                                if isinstance(attrs['columns'], str):
                                    import json
                                    columns = json.loads(attrs['columns'])
                                else:
                                    columns = attrs.get('columns', [])
                            except:
                                # If parsing fails, use empty list
                                pass
                        
                        # Add table-specific attributes
                        node_data.update({
                            'display_name': table_name,
                            'schema': schema,
                            'read_queries': len(out_queries),
                            'write_queries': len(in_queries),
                            'total_queries': len(in_queries) + len(out_queries),
                            'columns': columns
                        })
                    
                    elif node_type == 'query':
                        # Add query-specific attributes
                        total_time = float(attrs.get('total_time', 0))
                        calls = int(attrs.get('calls', 0))
                        mean_time = float(attrs.get('mean_time', 0))
                        rows = int(attrs.get('rows', 0)) if 'rows' in attrs else 0
                        
                        # Get query preview text
                        preview = attrs.get('text', 'Query text not available')
                        
                        node_data.update({
                            'preview': preview,
                            'total_time': total_time,
                            'calls': calls,
                            'mean_time': mean_time,
                            'rows': rows
                        })
                    
                    # Add node to D3 data
                    d3_data['nodes'].append(node_data)
                
                # Add links to D3 data
                for source, target in G.edges():
                    d3_data['links'].append({
                        'source': source,
                        'target': target
                    })
    except Exception as e:
        print(f"Error preparing D3 lineage data: {e}")
        flash(f'Error processing lineage data: {str(e)}', 'danger')
    
    # Convert the data to a JSON string for embedding in the template
    import json
    lineage_data_json = json.dumps(d3_data)
    
    return render_template(
        'lineage.html', 
        lineage_image=img_data,
        lineage_data_json=lineage_data_json
    )

@app.route('/query_details/<query_id>')
def query_details(query_id):
    """Display details for a specific query"""
    if 'has_results' not in session or 'analysis_files' not in session:
        flash('No analysis results available. Please run an analysis first.', 'warning')
        return redirect(url_for('index'))
    
    # Read the CSV file
    file_path = session['analysis_files'].get('expensive_queries')
    if not file_path or not os.path.exists(file_path):
        flash('Query data not found.', 'danger')
        return redirect(url_for('index'))
    
    # Load data from CSV
    df = pd.read_csv(file_path)
    
    # Try to convert query_id to an integer index
    try:
        query_index = int(query_id)
        if query_index >= len(df):
            flash('Query not found.', 'danger')
            return redirect(url_for('expensive_queries'))
        query = df.iloc[query_index]
    except ValueError:
        # If query_id is not an integer, it might be a hash or identifier
        # Look for matching queries in the dataframe
        matching_queries = df[df['queryid'].astype(str) == query_id]
        if matching_queries.empty:
            flash('Query not found.', 'danger')
            return redirect(url_for('expensive_queries'))
        query = matching_queries.iloc[0]
        query_index = df.index[df['queryid'].astype(str) == query_id][0]
    
    # We cannot directly access the lineage graph from CSV
    # Instead, we'll display the query and its metrics
    return render_template('query_details.html', query=query, query_id=query_index)

@app.route('/table_details/<table_name>')
def table_details(table_name):
    """Display details for a specific table"""
    if 'has_results' not in session or 'analysis_files' not in session:
        flash('No analysis results available. Please run an analysis first.', 'warning')
        return redirect(url_for('index'))
    
    # Read the CSV file
    file_path = session['analysis_files'].get('table_stats')
    if not file_path or not os.path.exists(file_path):
        flash('Table data not found.', 'danger')
        return redirect(url_for('index'))
    
    # Load data from CSV
    df = pd.read_csv(file_path)
    
    # Get table stats
    table_data = df[df['table_name'] == table_name]
    if table_data.empty:
        flash('Table not found.', 'danger')
        return redirect(url_for('table_stats'))
    
    table_stats = table_data.iloc[0].to_dict()
    
    return render_template('table_details.html', table=table_stats)

@app.route('/download/<file_type>')
def download(file_type):
    """Download analysis files"""
    if 'has_results' not in session or 'analysis_files' not in session:
        flash('No analysis results available. Please run an analysis first.', 'warning')
        return redirect(url_for('index'))
    
    file_mapping = {
        'expensive_queries': 'expensive_queries',
        'table_stats': 'table_stats',
        'lineage_image': 'lineage_image',
        'lineage_graphml': 'lineage_graphml'
    }
    
    if file_type not in file_mapping or file_mapping[file_type] not in session['analysis_files']:
        flash(f'File not found: {file_type}', 'danger')
        return redirect(url_for('index'))
    
    file_path = session['analysis_files'][file_mapping[file_type]]
    if not os.path.exists(file_path):
        flash(f'File not found on disk: {file_type}', 'danger')
        return redirect(url_for('index'))
    
    return send_file(file_path, as_attachment=True)

@app.route('/reset')
def reset():
    """Reset the analysis results"""
    if 'has_results' in session:
        del session['has_results']
    if 'analysis_files' in session:
        del session['analysis_files']
    session.modified = True
    
    flash('Analysis results have been reset.', 'info')
    return redirect(url_for('index'))

@app.route('/disconnect')
def disconnect():
    """Disconnect from the database"""
    if 'connection_params' in session:
        del session['connection_params']
    if 'has_results' in session:
        del session['has_results']
    if 'analysis_files' in session:
        del session['analysis_files']
    session.modified = True
    
    flash('Disconnected from database.', 'info')
    return redirect(url_for('index'))