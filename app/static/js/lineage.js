/**
 * Interactive Data Lineage Visualization
 * This script handles the interactive visualization of the PostgreSQL data lineage.
 */

// Global variables to store visualization state
let selectedTable = null;
let selectedQuery = null;

// Initialize the visualization when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initializeEventHandlers();
    highlightConnections();
});

/**
 * Initialize all event handlers for the visualization
 */
function initializeEventHandlers() {
    // Add event handlers for table elements
    document.querySelectorAll('.table-item').forEach(tableElement => {
        tableElement.addEventListener('click', function(e) {
            e.preventDefault();
            const tableName = this.getAttribute('data-table-name');
            selectTable(tableName);
        });
        
        tableElement.addEventListener('mouseenter', function() {
            const tableName = this.getAttribute('data-table-name');
            highlightTableConnections(tableName);
        });
        
        tableElement.addEventListener('mouseleave', function() {
            resetHighlighting();
            if (selectedTable) {
                highlightTableConnections(selectedTable);
            } else if (selectedQuery) {
                highlightQueryConnections(selectedQuery);
            }
        });
    });
    
    // Add event handlers for query elements
    document.querySelectorAll('.query-item').forEach(queryElement => {
        queryElement.addEventListener('click', function(e) {
            e.preventDefault();
            const queryId = this.getAttribute('data-query-id');
            selectQuery(queryId);
        });
        
        queryElement.addEventListener('mouseenter', function() {
            const queryId = this.getAttribute('data-query-id');
            highlightQueryConnections(queryId);
        });
        
        queryElement.addEventListener('mouseleave', function() {
            resetHighlighting();
            if (selectedTable) {
                highlightTableConnections(selectedTable);
            } else if (selectedQuery) {
                highlightQueryConnections(selectedQuery);
            }
        });
    });
    
    // Add event handler for reset button
    const resetButton = document.getElementById('reset-selection');
    if (resetButton) {
        resetButton.addEventListener('click', function(e) {
            e.preventDefault();
            resetSelection();
        });
    }
    
    // Add event handlers for schema collapsible sections
    document.querySelectorAll('.schema-heading').forEach(heading => {
        heading.addEventListener('click', function() {
            const schemaContent = this.nextElementSibling;
            this.classList.toggle('collapsed');
            if (schemaContent.style.maxHeight) {
                schemaContent.style.maxHeight = null;
            } else {
                schemaContent.style.maxHeight = schemaContent.scrollHeight + "px";
            }
        });
    });
}

/**
 * Handle table selection and highlight its connections
 */
function selectTable(tableName) {
    // Reset previous selection
    if (selectedTable !== tableName) {
        resetSelection();
        selectedTable = tableName;
        
        // Highlight the selected table
        const tableElement = document.querySelector(`.table-item[data-table-name="${tableName}"]`);
        if (tableElement) {
            tableElement.classList.add('selected');
        }
        
        // Highlight its connections
        highlightTableConnections(tableName);
        
        // Update info panel
        updateInfoPanel('table', tableName);
    } else {
        // If clicking the same table again, deselect it
        resetSelection();
    }
}

/**
 * Handle query selection and highlight its connections
 */
function selectQuery(queryId) {
    // Reset previous selection
    if (selectedQuery !== queryId) {
        resetSelection();
        selectedQuery = queryId;
        
        // Highlight the selected query
        const queryElement = document.querySelector(`.query-item[data-query-id="${queryId}"]`);
        if (queryElement) {
            queryElement.classList.add('selected');
        }
        
        // Highlight its connections
        highlightQueryConnections(queryId);
        
        // Update info panel
        updateInfoPanel('query', queryId);
    } else {
        // If clicking the same query again, deselect it
        resetSelection();
    }
}

/**
 * Reset all selections and highlighting
 */
function resetSelection() {
    selectedTable = null;
    selectedQuery = null;
    
    // Reset all highlights
    document.querySelectorAll('.table-item, .query-item').forEach(el => {
        el.classList.remove('selected', 'connected', 'source', 'target');
    });
    
    document.querySelectorAll('.connection-line').forEach(line => {
        line.classList.remove('highlighted');
    });
    
    // Reset info panel
    document.getElementById('info-panel-content').innerHTML = `
        <div class="text-center py-4">
            <i class="bi bi-info-circle fs-2 text-muted"></i>
            <p class="mt-3 text-muted">Select a table or query to see its connections</p>
        </div>
    `;
}

/**
 * Highlight connections for a table
 */
function highlightTableConnections(tableName) {
    // Get all queries connected to this table
    const sourceQueries = getQueriesFromTable(tableName, 'source');
    const targetQueries = getQueriesFromTable(tableName, 'target');
    
    // Highlight the table
    const tableElement = document.querySelector(`.table-item[data-table-name="${tableName}"]`);
    if (tableElement) {
        tableElement.classList.add('highlighted');
    }
    
    // Highlight source queries (table → query)
    sourceQueries.forEach(queryId => {
        const queryElement = document.querySelector(`.query-item[data-query-id="${queryId}"]`);
        if (queryElement) {
            queryElement.classList.add('connected', 'target');
        }
        
        // Highlight connection line
        const connectionLine = document.querySelector(`.connection-line[data-source="${tableName}"][data-target="${queryId}"]`);
        if (connectionLine) {
            connectionLine.classList.add('highlighted');
        }
    });
    
    // Highlight target queries (query → table)
    targetQueries.forEach(queryId => {
        const queryElement = document.querySelector(`.query-item[data-query-id="${queryId}"]`);
        if (queryElement) {
            queryElement.classList.add('connected', 'source');
        }
        
        // Highlight connection line
        const connectionLine = document.querySelector(`.connection-line[data-source="${queryId}"][data-target="${tableName}"]`);
        if (connectionLine) {
            connectionLine.classList.add('highlighted');
        }
    });
}

/**
 * Highlight connections for a query
 */
function highlightQueryConnections(queryId) {
    // Get all tables connected to this query
    const sourceTables = getTablesFromQuery(queryId, 'source');
    const targetTables = getTablesFromQuery(queryId, 'target');
    
    // Highlight the query
    const queryElement = document.querySelector(`.query-item[data-query-id="${queryId}"]`);
    if (queryElement) {
        queryElement.classList.add('highlighted');
    }
    
    // Highlight source tables (table → query)
    sourceTables.forEach(tableName => {
        const tableElement = document.querySelector(`.table-item[data-table-name="${tableName}"]`);
        if (tableElement) {
            tableElement.classList.add('connected', 'source');
        }
        
        // Highlight connection line
        const connectionLine = document.querySelector(`.connection-line[data-source="${tableName}"][data-target="${queryId}"]`);
        if (connectionLine) {
            connectionLine.classList.add('highlighted');
        }
    });
    
    // Highlight target tables (query → table)
    targetTables.forEach(tableName => {
        const tableElement = document.querySelector(`.table-item[data-table-name="${tableName}"]`);
        if (tableElement) {
            tableElement.classList.add('connected', 'target');
        }
        
        // Highlight connection line
        const connectionLine = document.querySelector(`.connection-line[data-source="${queryId}"][data-target="${tableName}"]`);
        if (connectionLine) {
            connectionLine.classList.add('highlighted');
        }
    });
}

/**
 * Get queries connected to a table
 */
function getQueriesFromTable(tableName, direction) {
    const result = [];
    
    if (direction === 'source' || direction === 'both') {
        // Find queries where the table is the source (table → query)
        document.querySelectorAll(`.connection-line[data-source="${tableName}"]`).forEach(line => {
            const targetId = line.getAttribute('data-target');
            if (targetId && targetId.startsWith('Query_')) {
                result.push(targetId);
            }
        });
    }
    
    if (direction === 'target' || direction === 'both') {
        // Find queries where the table is the target (query → table)
        document.querySelectorAll(`.connection-line[data-target="${tableName}"]`).forEach(line => {
            const sourceId = line.getAttribute('data-source');
            if (sourceId && sourceId.startsWith('Query_')) {
                result.push(sourceId);
            }
        });
    }
    
    return result;
}

/**
 * Get tables connected to a query
 */
function getTablesFromQuery(queryId, direction) {
    const result = [];
    
    if (direction === 'source' || direction === 'both') {
        // Find tables where the query is the source (query → table)
        document.querySelectorAll(`.connection-line[data-source="${queryId}"]`).forEach(line => {
            const targetId = line.getAttribute('data-target');
            if (targetId && !targetId.startsWith('Query_')) {
                result.push(targetId);
            }
        });
    }
    
    if (direction === 'target' || direction === 'both') {
        // Find tables where the query is the target (table → query)
        document.querySelectorAll(`.connection-line[data-target="${queryId}"]`).forEach(line => {
            const sourceId = line.getAttribute('data-source');
            if (sourceId && !sourceId.startsWith('Query_')) {
                result.push(sourceId);
            }
        });
    }
    
    return result;
}

/**
 * Reset all highlighting
 */
function resetHighlighting() {
    document.querySelectorAll('.table-item, .query-item').forEach(el => {
        el.classList.remove('highlighted', 'connected', 'source', 'target');
    });
    
    document.querySelectorAll('.connection-line').forEach(line => {
        line.classList.remove('highlighted');
    });
}

/**
 * Update the info panel with details about the selected item
 */
function updateInfoPanel(type, id) {
    const infoPanel = document.getElementById('info-panel-content');
    
    if (type === 'table') {
        // Get table details
        const tableElement = document.querySelector(`.table-item[data-table-name="${id}"]`);
        if (!tableElement) return;
        
        const tableName = tableElement.getAttribute('data-display-name');
        const schema = tableElement.getAttribute('data-schema');
        const readQueries = parseInt(tableElement.getAttribute('data-read-queries') || 0);
        const writeQueries = parseInt(tableElement.getAttribute('data-write-queries') || 0);
        
        // Get connected queries
        const sourceQueries = getQueriesFromTable(id, 'source');
        const targetQueries = getQueriesFromTable(id, 'target');
        
        infoPanel.innerHTML = `
            <div class="mb-3">
                <h5 class="border-bottom pb-2"><i class="bi bi-table me-2"></i>Table: ${tableName}</h5>
                <div class="mb-2"><strong>Schema:</strong> ${schema}</div>
                <div class="mb-2"><strong>Reads:</strong> ${readQueries} queries</div>
                <div class="mb-2"><strong>Writes:</strong> ${writeQueries} queries</div>
                <div class="mb-3"><strong>Total:</strong> ${readQueries + writeQueries} queries</div>
                <a href="/table_details/${id}" class="btn btn-sm btn-primary">
                    <i class="bi bi-info-circle me-1"></i>View Table Details
                </a>
            </div>
            
            <div class="mt-4">
                <h6 class="border-bottom pb-2">Connected Queries</h6>
                <div class="small">
                    <div class="mb-2"><strong>Read from this table (${sourceQueries.length}):</strong></div>
                    <ul class="list-unstyled ms-3 mb-3">
                        ${sourceQueries.map(q => `
                            <li class="mb-1">
                                <a href="#${q}" class="text-decoration-none" onclick="selectQuery('${q}'); return false;">
                                    <i class="bi bi-arrow-right-short me-1 text-muted"></i>${q}
                                </a>
                            </li>
                        `).join('')}
                        ${sourceQueries.length === 0 ? '<li class="text-muted">No reading queries</li>' : ''}
                    </ul>
                    
                    <div class="mb-2"><strong>Write to this table (${targetQueries.length}):</strong></div>
                    <ul class="list-unstyled ms-3">
                        ${targetQueries.map(q => `
                            <li class="mb-1">
                                <a href="#${q}" class="text-decoration-none" onclick="selectQuery('${q}'); return false;">
                                    <i class="bi bi-arrow-left-short me-1 text-muted"></i>${q}
                                </a>
                            </li>
                        `).join('')}
                        ${targetQueries.length === 0 ? '<li class="text-muted">No writing queries</li>' : ''}
                    </ul>
                </div>
            </div>
        `;
        
    } else if (type === 'query') {
        // Get query details
        const queryElement = document.querySelector(`.query-item[data-query-id="${id}"]`);
        if (!queryElement) return;
        
        const hash = queryElement.getAttribute('data-hash');
        const preview = queryElement.getAttribute('data-preview');
        const totalTime = parseFloat(queryElement.getAttribute('data-total-time') || 0).toFixed(2);
        const calls = queryElement.getAttribute('data-calls');
        const meanTime = parseFloat(queryElement.getAttribute('data-mean-time') || 0).toFixed(2);
        const rows = queryElement.getAttribute('data-rows');
        
        // Get connected tables
        const sourceTables = getTablesFromQuery(id, 'source');
        const targetTables = getTablesFromQuery(id, 'target');
        
        infoPanel.innerHTML = `
            <div class="mb-3">
                <h5 class="border-bottom pb-2"><i class="bi bi-lightning me-2"></i>Query: ${id}</h5>
                <div class="mb-2 small sql-container p-2">
                    <code>${preview}</code>
                </div>
                <div class="d-flex flex-wrap">
                    <div class="me-3 mb-2"><strong>Total Time:</strong> ${totalTime}ms</div>
                    <div class="me-3 mb-2"><strong>Calls:</strong> ${calls}</div>
                    <div class="me-3 mb-2"><strong>Avg Time:</strong> ${meanTime}ms</div>
                    <div class="mb-2"><strong>Rows:</strong> ${rows}</div>
                </div>
                <a href="/query_details/${id.replace('Query_', '')}" class="btn btn-sm btn-primary">
                    <i class="bi bi-info-circle me-1"></i>View Query Details
                </a>
            </div>
            
            <div class="mt-4">
                <h6 class="border-bottom pb-2">Connected Tables</h6>
                <div class="small">
                    <div class="mb-2"><strong>Reads from (${sourceTables.length}):</strong></div>
                    <ul class="list-unstyled ms-3 mb-3">
                        ${sourceTables.map(t => `
                            <li class="mb-1">
                                <a href="#${t}" class="text-decoration-none" onclick="selectTable('${t}'); return false;">
                                    <i class="bi bi-arrow-left-short me-1 text-muted"></i>${t}
                                </a>
                            </li>
                        `).join('')}
                        ${sourceTables.length === 0 ? '<li class="text-muted">No source tables</li>' : ''}
                    </ul>
                    
                    <div class="mb-2"><strong>Writes to (${targetTables.length}):</strong></div>
                    <ul class="list-unstyled ms-3">
                        ${targetTables.map(t => `
                            <li class="mb-1">
                                <a href="#${t}" class="text-decoration-none" onclick="selectTable('${t}'); return false;">
                                    <i class="bi bi-arrow-right-short me-1 text-muted"></i>${t}
                                </a>
                            </li>
                        `).join('')}
                        ${targetTables.length === 0 ? '<li class="text-muted">No target tables</li>' : ''}
                    </ul>
                </div>
            </div>
        `;
    }
}

/**
 * Draw connection lines between tables and queries
 */
function highlightConnections() {
    // To be implemented if we want to draw actual SVG lines between elements
    // Currently we're just using CSS to highlight the connected elements
}