/**
 * Interactive Data Lineage Visualization using D3.js
 * This script handles the interactive graph visualization of PostgreSQL data lineage.
 */

// Store visualization state
let lineageSimulation;
let lineageZoom;
let lineageSvg;
let lineageGraph;
let topNodes; // Store important nodes that always need labels

// Initialize the visualization when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initializeLineageGraph();
});

/**
 * Initialize the D3 force-directed graph
 */
function initializeLineageGraph() {
    // Check if we have lineage data
    const lineageData = window.lineageData;
    if (!lineageData || !lineageData.nodes || !lineageData.links) {
        console.error('Lineage data not available');
        document.getElementById('lineage-graph').innerHTML = 
            '<div class="alert alert-warning"><i class="bi bi-exclamation-triangle me-2"></i>Lineage data not available</div>';
        return;
    }

    // Get container dimensions
    const container = document.getElementById('lineage-graph');
    const width = container.clientWidth;
    const height = 600; // Fixed height, could be made responsive

    // Create the SVG element
    const svg = d3.select('#lineage-graph')
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .attr('class', 'lineage-svg');
        
    // Add a background rect to handle zoom events
    svg.append('rect')
        .attr('width', width)
        .attr('height', height)
        .attr('fill', 'none')
        .attr('pointer-events', 'all');
    
    // Create a group for the graph that will be transformed by zoom
    const g = svg.append('g')
        .attr('class', 'lineage-container');
    
    // Create zoom behavior
    const zoom = d3.zoom()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => {
            // Update main graph with zoom transform
            g.attr('transform', event.transform);
            
            // Update schema overlay to move horizontally with zoom but stay fixed vertically
            if (d3.select('.schema-overlay').size() > 0 && 
                document.getElementById('floating-labels').checked) {
                // Apply only the horizontal translation and scale to schema labels
                const tx = event.transform.x;
                const scale = event.transform.k;
                d3.selectAll('.schema-label-group')
                    .attr('transform', (d, i) => {
                        const originalX = schemaColumnPositions[i];
                        const scaledX = originalX * scale;
                        const translateX = tx + (scaledX - originalX);
                        return `translate(${translateX}, 0)`;
                    });
            }
        });
    
    // Apply zoom to SVG
    svg.call(zoom);
    
    // Add zoom controls
    addZoomControls(svg, zoom);
    
    // Initialize tooltip
    const tooltip = d3.select('body')
        .append('div')
        .attr('class', 'lineage-tooltip')
        .style('opacity', 0);
    
    // Group nodes by schema for positioning
    const schemas = new Set();
    const tableNodesBySchema = {};
    
    // Collect schemas and group tables by schema
    lineageData.nodes.forEach(node => {
        if (node.type === 'table') {
            const schema = node.schema || 'public';
            schemas.add(schema);
            if (!tableNodesBySchema[schema]) {
                tableNodesBySchema[schema] = [];
            }
            tableNodesBySchema[schema].push(node);
        }
    });
    
    // Convert schemas to array for indexing
    const schemaArray = Array.from(schemas);
    
    // Calculate connection count for each node
    lineageData.nodes.forEach(node => {
        node.connectionCount = 0;
    });
    
    lineageData.links.forEach(link => {
        const source = typeof link.source === 'object' ? link.source.id : link.source;
        const target = typeof link.target === 'object' ? link.target.id : link.target;
        
        const sourceNode = lineageData.nodes.find(n => n.id === source);
        const targetNode = lineageData.nodes.find(n => n.id === target);
        
        if (sourceNode) sourceNode.connectionCount = (sourceNode.connectionCount || 0) + 1;
        if (targetNode) targetNode.connectionCount = (targetNode.connectionCount || 0) + 1;
    });
    
    // Create the force simulation for layout
    const simulation = d3.forceSimulation(lineageData.nodes)
        .force('link', d3.forceLink(lineageData.links).id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-200))
        .force('center', d3.forceCenter(width / 2, height / 2));
    
    // Calculate optimal schema column positions (using the same logic as for the visual elements)
    const schemaColumnPositions = schemaArray.map((schema, i) => 
        width * (0.2 + (i / Math.max(1, schemas.size - 1)) * 0.6)
    );
    
    // Add layout with schema structuring and connectivity-based positioning
    simulation
        .force('x', d3.forceX(d => {
            if (d.type === 'table') {
                // Position tables exactly on their schema column
                const schemaIndex = schemaArray.indexOf(d.schema || 'public');
                return schemaColumnPositions[schemaIndex]; // Use the exact same positions as visual elements
            } else {
                // Position queries based on their connectivity - but still keep schema influence
                // Identify which schema this query is most connected to
                let schemaConnectionCounts = {};
                schemaArray.forEach(schema => schemaConnectionCounts[schema] = 0);
                
                // Count connections to tables in each schema
                lineageData.links.forEach(link => {
                    if ((link.source === d.id || link.target === d.id)) {
                        // Get the other node in the link
                        const otherNodeId = link.source === d.id ? link.target : link.source;
                        const otherNode = lineageData.nodes.find(n => n.id === otherNodeId);
                        
                        // If it's a table, increment its schema count
                        if (otherNode && otherNode.type === 'table') {
                            const schema = otherNode.schema || 'public';
                            schemaConnectionCounts[schema] = (schemaConnectionCounts[schema] || 0) + 1;
                        }
                    }
                });
                
                // Find most connected schema
                let maxCount = 0;
                let mostConnectedSchema = schemaArray[0];
                for (const [schema, count] of Object.entries(schemaConnectionCounts)) {
                    if (count > maxCount) {
                        maxCount = count;
                        mostConnectedSchema = schema;
                    }
                }
                
                // Position query between center and its most connected schema
                const schemaIndex = schemaArray.indexOf(mostConnectedSchema);
                const schemaX = schemaColumnPositions[schemaIndex];
                // Position more toward schema column than center for better alignment
                return (schemaX * 0.7 + width/2 * 0.3); // 70% schema position, 30% center
            }
        }).strength(d => d.type === 'table' ? 0.9 : 0.4)) // Even stronger forces for precise schema centering
        .force('y', d3.forceY(d => {
            if (d.type === 'query') {
                // Position queries vertically, center the most connected ones
                return height * 0.5;
            } else {
                // Position tables along vertical column by schema
                const schema = d.schema || 'public';
                const tableIndex = tableNodesBySchema[schema].indexOf(d);
                const totalTablesInSchema = tableNodesBySchema[schema].length;
                
                // Stagger tables in each schema vertically
                return height * (0.2 + (tableIndex / Math.max(1, totalTablesInSchema - 1)) * 0.6);
            }
        }).strength(d => d.type === 'table' ? 0.7 : 0.3)) // Stronger forces for better schema grouping
        .force('charge', d3.forceManyBody().strength(d => {
            // Adjust repulsion based on node type
            return d.type === 'table' ? -200 : -100;
        }))
        .force('connectivity', d3.forceRadial(d => {
            // Position most connected nodes toward the center
            // Less connected nodes will be pushed outward
            if (d.connectionCount > 0) {
                // Inverse relationship: more connections = closer to center
                return Math.max(50, 300 / Math.sqrt(d.connectionCount));
            }
            return 300; // Default radius for unconnected nodes
        }, width / 2, height / 2).strength(0.1)); // Reduced strength to prioritize schema grouping

    // Classify links into direct table-to-table links and query links
    const tableToTableLinks = lineageData.links.filter(link => 
        (lineageData.nodes.find(n => n.id === link.source)?.type === 'table' && 
         lineageData.nodes.find(n => n.id === link.target)?.type === 'table')
    );
    
    const queryLinks = lineageData.links.filter(link => 
        !(lineageData.nodes.find(n => n.id === link.source)?.type === 'table' && 
          lineageData.nodes.find(n => n.id === link.target)?.type === 'table')
    );
    
    // Create regular query links
    const queryLink = g.append('g')
        .attr('class', 'links')
        .selectAll('line')
        .data(queryLinks)
        .enter()
        .append('line')
        .attr('class', 'lineage-link query-link')
        .attr('stroke-width', 1.5)
        .attr('stroke', '#a8a8a8')
        .attr('marker-end', 'url(#arrowhead)');
    
    // Create table-to-table links with different styling
    const tableLink = g.append('g')
        .attr('class', 'links')
        .selectAll('line')
        .data(tableToTableLinks)
        .enter()
        .append('line')
        .attr('class', 'lineage-link table-link')
        .attr('stroke-width', 2.0)
        .attr('stroke', '#28C76F')  // Use the table color for table-to-table links
        .attr('stroke-dasharray', '5,5')  // Make these links dashed
        .attr('marker-end', 'url(#table-arrowhead)');
    
    // Create arrowhead markers and filters
    const defs = svg.append('defs');
    
    // Add subtle glow filter for highlighting
    const glowFilter = defs.append('filter')
        .attr('id', 'glow')
        .attr('x', '-50%')
        .attr('y', '-50%')
        .attr('width', '200%')
        .attr('height', '200%');
        
    glowFilter.append('feGaussianBlur')
        .attr('stdDeviation', '3')
        .attr('result', 'coloredBlur');
        
    const glowMerge = glowFilter.append('feMerge');
    glowMerge.append('feMergeNode')
        .attr('in', 'coloredBlur');
    glowMerge.append('feMergeNode')
        .attr('in', 'SourceGraphic');
    
    // Regular arrowhead for query links
    defs.append('marker')
        .attr('id', 'arrowhead')
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 20) // Position slightly away from node
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', '#a8a8a8');
        
    // Highlighted arrowhead for query links
    defs.append('marker')
        .attr('id', 'arrowhead-highlight')
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 20)
        .attr('markerWidth', 7)
        .attr('markerHeight', 7)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', '#7367F0');
        
    // Special arrowhead for table-to-table links
    defs.append('marker')
        .attr('id', 'table-arrowhead')
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 20) // Position slightly away from node
        .attr('markerWidth', 8)
        .attr('markerHeight', 8)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', '#28C76F');
        
    // Highlighted arrowhead for table-to-table links
    defs.append('marker')
        .attr('id', 'table-arrowhead-highlight')
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 20)
        .attr('markerWidth', 9)
        .attr('markerHeight', 9)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', '#7367F0');

    // Create nodes
    const node = g.append('g')
        .attr('class', 'nodes')
        .selectAll('g')
        .data(lineageData.nodes)
        .enter()
        .append('g')
        .attr('class', d => 'lineage-node lineage-node-' + d.type)
        .call(d3.drag()
            .on('start', dragStarted)
            .on('drag', dragging)
            .on('end', dragEnded));
    
    // Add circles for nodes with different styles based on type
    node.append('circle')
        .attr('r', d => getNodeRadius(d))
        .attr('fill', d => getNodeColor(d))
        .attr('stroke', '#fff')
        .attr('stroke-width', 1.5);
    
    // Calculate which nodes need labels always visible
    
    // Calculate node importance scores and find top-N nodes
    const importanceScores = lineageData.nodes.map(d => {
        let importance = 0;
        if (d.type === 'query') {
            const timeImportance = d.total_time ? 
                Math.log(d.total_time + 1) / Math.log(10000) : 0;
            const connectionImportance = d.connectionCount ? 
                Math.log(d.connectionCount + 1) / Math.log(20) : 0;
            importance = (timeImportance * 0.7) + (connectionImportance * 0.3);
        } else {
            const queryImportance = d.total_queries ? 
                Math.log(d.total_queries + 1) / Math.log(50) : 0;
            const connectionImportance = d.connectionCount ? 
                Math.log(d.connectionCount + 1) / Math.log(20) : 0;
            importance = (connectionImportance * 0.5) + (queryImportance * 0.5);
        }
        return {node: d, importance: importance};
    });
    
    // Sort by importance descending
    importanceScores.sort((a, b) => b.importance - a.importance);
    
    // Select top N nodes based on graph size
    const totalNodes = lineageData.nodes.length;
    const topNCount = Math.max(5, Math.min(20, Math.ceil(totalNodes * 0.15))); // 15% of nodes or at least 5, max 20
    topNodes = new Set(importanceScores.slice(0, topNCount).map(item => item.node.id)); // Set global topNodes variable
    
    // For remaining nodes, calculate dynamic threshold
    const nodeDensity = totalNodes / (width * height) * 1000000; // Nodes per million pixels
    
    // Determine importance threshold based on node density
    // Higher node density = higher threshold (fewer labels shown)
    const importanceThreshold = Math.min(0.7, Math.max(0.3, nodeDensity / 15));
    
    // Create label containers with background
    const nodeLabels = node.append('g')
        .attr('class', 'node-label-container')
        .style('opacity', d => {
            // Top nodes always have visible labels
            if (topNodes.has(d.id)) {
                return 1.0;
            }
            
            // For other nodes, use dynamic threshold
            let importance = 0;
            if (d.type === 'query') {
                const timeImportance = d.total_time ? 
                    Math.log(d.total_time + 1) / Math.log(10000) : 0;
                const connectionImportance = d.connectionCount ? 
                    Math.log(d.connectionCount + 1) / Math.log(20) : 0;
                importance = (timeImportance * 0.7) + (connectionImportance * 0.3);
            } else {
                const queryImportance = d.total_queries ? 
                    Math.log(d.total_queries + 1) / Math.log(50) : 0;
                const connectionImportance = d.connectionCount ? 
                    Math.log(d.connectionCount + 1) / Math.log(20) : 0;
                importance = (connectionImportance * 0.5) + (queryImportance * 0.5);
            }
            
            // Show labels for important nodes initially
            return importance > importanceThreshold ? 0.9 : 0;
        });
    
    // Add semi-transparent background for better readability
    nodeLabels.append('rect')
        .attr('x', d => {
            const offset = d.type === 'table' ? -5 : 5;
            const radius = getNodeRadius(d);
            return d.type === 'table' ? -(getLabelWidth(getNodeLabel(d)) + radius + 10) : radius + offset;
        })
        .attr('y', -10)
        .attr('width', d => getLabelWidth(getNodeLabel(d)) + 6)
        .attr('height', 20)
        .attr('rx', 3)
        .attr('fill', 'rgba(255, 255, 255, 0.7)')
        .attr('stroke', d => d.type === 'table' ? '#28C76F' : '#00CFE8')
        .attr('stroke-opacity', 0.3)
        .attr('stroke-width', 1);
    
    // Add text labels
    nodeLabels.append('text')
        .attr('dy', '0.35em')
        .attr('x', d => {
            const offset = d.type === 'table' ? -5 : 5;
            const radius = getNodeRadius(d);
            return d.type === 'table' ? -radius - offset : radius + offset;
        })
        .attr('text-anchor', d => d.type === 'table' ? 'end' : 'start')
        .text(d => getNodeLabel(d))
        .attr('font-size', d => Math.min(12, Math.max(9, getNodeRadius(d) * 0.7)) + 'px')
        .attr('fill', '#333');
        
    // Helper function to estimate label width
    function getLabelWidth(text) {
        return text.length * 6; // Rough estimate, can be improved
    }
    
    // Add tooltips
    node.on('mouseover', (event, d) => {
        tooltip.transition()
            .duration(200)
            .style('opacity', .9);
        
        let html = getTooltipContent(d);
        
        tooltip.html(html)
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 28) + 'px');
        
        // Highlight connections
        highlightConnections(d);
    })
    .on('mouseout', () => {
        tooltip.transition()
            .duration(500)
            .style('opacity', 0);
        
        // Reset highlights
        resetHighlights();
    })
    .on('click', (event, d) => {
        // Handle node click - navigate to details page
        if (d.type === 'table') {
            window.location.href = '/table_details/' + d.id;
        } else if (d.type === 'query') {
            // Extract the numeric index from the query's position in the data
            const queryIndex = lineageData.nodes
                .filter(node => node.type === 'query')
                .findIndex(node => node.id === d.id);
            
            if (queryIndex !== -1) {
                window.location.href = '/query_details/' + queryIndex;
            }
        }
    });
    
    // Simulation tick function to update positions
    simulation.on('tick', () => {
        // Update query links positions
        d3.selectAll('.query-link')
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
            
        // Update table-to-table links positions
        d3.selectAll('.table-link')
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
        
        // Update node positions
        node
            .attr('transform', d => `translate(${d.x},${d.y})`);
    });
    
    // Add schema regions and labels when grouping by schema
    if (schemas.size > 1) {
        // Calculate optimal schema column positions
        const schemaColumnPositions = schemaArray.map((schema, i) => 
            width * (0.2 + (i / Math.max(1, schemas.size - 1)) * 0.6)
        );
        
        // Calculate schema region widths based on number of schemas
        const schemaRegionWidth = width * Math.min(0.3, 0.9 / schemas.size);
        
        // Add schema background regions first (before labels so they appear behind)
        const schemaRegions = g.append('g')
            .attr('class', 'schema-regions')
            .selectAll('rect')
            .data(schemaArray)
            .enter()
            .append('rect')
            .attr('class', 'schema-region')
            .attr('x', (schema, i) => schemaColumnPositions[i] - (schemaRegionWidth / 2))
            .attr('y', 30) // Start below the labels
            .attr('width', schemaRegionWidth)
            .attr('height', height - 60) // Fixed height
            .attr('fill', (d, i) => `rgba(115, 103, 240, ${0.03 + (i % 2) * 0.03})`) // Alternate subtle background
            .attr('rx', 10) // Rounded corners
            .attr('ry', 10)
            .attr('stroke', '#7367F0')
            .attr('stroke-width', 0.5)
            .attr('stroke-opacity', 0.1);
            
        // Create overlay layer for schema headings in SVG (outside the zoom group)
        const schemaOverlay = svg.append('g')
            .attr('class', 'schema-overlay')
            .style('pointer-events', 'none') // Non-interactive
            .style('display', 'block'); // Initially visible
            
        // Add schema labels that will move horizontally with zoom but stay at top
        const schemaLabels = schemaOverlay.selectAll('g')
            .data(schemaArray)
            .enter()
            .append('g')
            .attr('class', 'schema-label-group');
            
        // Add schema header background
        schemaLabels.append('rect')
            .attr('x', (schema, i) => schemaColumnPositions[i] - 50) // Center on schema column
            .attr('y', 5)
            .attr('width', 100) // Fixed width
            .attr('height', 25)
            .attr('rx', 12)
            .attr('ry', 12)
            .attr('fill', '#ffffff')
            .attr('stroke', '#7367F0')
            .attr('stroke-width', 1)
            .attr('stroke-opacity', 0.3)
            .attr('filter', 'drop-shadow(0 1px 3px rgba(0,0,0,0.1))');
            
        // Add schema label text
        schemaLabels.append('text')
            .attr('class', 'schema-label')
            .attr('x', (schema, i) => schemaColumnPositions[i])
            .attr('y', 22) // Fixed vertical position at the top
            .attr('text-anchor', 'middle')
            .attr('fill', '#7367F0')
            .attr('font-weight', 'bold')
            .attr('font-size', '12px')
            .text(d => d);
            
        // Add schema counts (number of tables in each schema)
        schemaLabels.append('text')
            .attr('class', 'schema-count')
            .attr('x', (schema, i) => schemaColumnPositions[i])
            .attr('y', 40) // Fixed vertical position at the top
            .attr('text-anchor', 'middle')
            .attr('fill', '#7367F0')
            .attr('font-size', '10px')
            .text(d => {
                const count = tableNodesBySchema[d].length;
                return `${count} table${count !== 1 ? 's' : ''}`;
            });
            
        // Add vertical separator lines between schemas (optional)
        if (schemas.size > 1) {
            const separators = g.append('g')
                .attr('class', 'schema-separators')
                .selectAll('line')
                .data(schemaArray.slice(0, -1)) // One less than schemas (no line after last)
                .enter()
                .append('line')
                .attr('class', 'schema-separator')
                .attr('x1', (schema, i) => (schemaColumnPositions[i] + schemaColumnPositions[i+1]) / 2)
                .attr('x2', (schema, i) => (schemaColumnPositions[i] + schemaColumnPositions[i+1]) / 2)
                .attr('y1', 50)
                .attr('y2', height - 40)
                .attr('stroke', '#7367F0')
                .attr('stroke-width', 0.5)
                .attr('stroke-dasharray', '3,3')
                .attr('opacity', 0.2);
        }
    }
    
    // Setup toggle handlers for layout options
    setupLayoutToggles(simulation, schemas, schemaArray, tableNodesBySchema, width, height);
    
    // Store references for external access
    lineageSimulation = simulation;
    lineageZoom = zoom;
    lineageSvg = svg;
    lineageGraph = g;
    
    // Initially center and zoom to fit content
    zoomToFit();
    
    // Drag functions
    function dragStarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }
    
    function dragging(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }
    
    function dragEnded(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
}

/**
 * Get radius for a node based on its type, properties, and screen size
 */
function getNodeRadius(d) {
    // Get the container dimensions to adapt to screen size
    const container = document.getElementById('lineage-graph');
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    // Base sizing factors based on screen size
    const screenFactor = Math.min(width, height) / 1000;
    const baseSizeFactor = Math.max(1, screenFactor);
    
    // Calculate node importance - more connected nodes should be larger
    const connectionImportance = d.connectionCount ? 
        Math.log(d.connectionCount + 1) / Math.log(20) : 0; // Logarithmic scaling for connection count
    
    if (d.type === 'query') {
        // Size queries by their total_time and connection count
        const timeImportance = d.total_time ? 
            Math.log(d.total_time + 1) / Math.log(10000) : 0; // Logarithmic scaling for query time
        
        // Combined importance score (weighted)
        const importance = (timeImportance * 0.7) + (connectionImportance * 0.3);
        
        // Scale radius based on importance and screen size
        const minRadius = 4 * baseSizeFactor;
        const maxRadius = 18 * baseSizeFactor;
        return minRadius + (importance * (maxRadius - minRadius));
    } else {
        // Size tables by their connection count and query count
        const queryImportance = d.total_queries ? 
            Math.log(d.total_queries + 1) / Math.log(50) : 0; // Logarithmic scaling for queries
        
        // Combined importance score (weighted)
        const importance = (connectionImportance * 0.5) + (queryImportance * 0.5);
        
        // Scale radius based on importance and screen size
        const minRadius = 5 * baseSizeFactor;
        const maxRadius = 16 * baseSizeFactor;
        return minRadius + (importance * (maxRadius - minRadius));
    }
}

/**
 * Get color for a node based on its type
 */
function getNodeColor(d) {
    if (d.type === 'query') {
        // Expensive queries are more red - using Materio colors
        const intensity = Math.min(1, d.total_time / 10000);
        return d3.interpolateRgb('#00CFE8', '#EA5455')(intensity); // Info to Error colors
    } else {
        return '#28C76F'; // Success color for tables
    }
}

/**
 * Get label for a node
 */
function getNodeLabel(d) {
    if (d.type === 'table') {
        // For tables, show the table name (or display name if available)
        return d.display_name || d.id;
    } else {
        // For queries, show a short preview or ID
        return d.id.split('_')[0];
    }
}

/**
 * Get tooltip content for a node
 */
function getTooltipContent(d) {
    if (d.type === 'table') {
        // Format table columns
        let columnsHTML = '';
        if (d.columns && d.columns.length > 0) {
            columnsHTML = `
                <div class="tooltip-section">
                    <div class="tooltip-subtitle">Schema</div>
                    <table class="tooltip-columns">
                        <tr>
                            <th>Column</th>
                            <th>Type</th>
                            <th>PK</th>
                        </tr>
                        ${d.columns.slice(0, 5).map(col => `
                            <tr>
                                <td>${col.name}</td>
                                <td>${col.type}</td>
                                <td>${col.is_primary_key ? '✓' : ''}</td>
                            </tr>
                        `).join('')}
                        ${d.columns.length > 5 ? `<tr><td colspan="3">+ ${d.columns.length - 5} more columns...</td></tr>` : ''}
                    </table>
                </div>
            `;
        }
        
        // Get connected tables through queries (for column relationships)
        const connectedTables = getConnectedTableColumnRelationships(d);
        let relationshipsHTML = '';
        
        if (connectedTables.length > 0) {
            relationshipsHTML = `
                <div class="tooltip-section">
                    <div class="tooltip-subtitle">Related Tables</div>
                    <div class="tooltip-relationships">
                        ${connectedTables.map(rel => `
                            <div class="tooltip-relationship">
                                ${rel.table} ${rel.direction === 'from' ? '→' : '←'} ${d.display_name || d.id}
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        return `
            <div class="tooltip-header">${d.display_name || d.id}</div>
            <div class="tooltip-schema">Schema: ${d.schema || 'public'}</div>
            <div class="tooltip-stat">Read queries: ${d.read_queries || 0}</div>
            <div class="tooltip-stat">Write queries: ${d.write_queries || 0}</div>
            <div class="tooltip-stat">Total queries: ${d.total_queries || 0}</div>
            ${columnsHTML}
            ${relationshipsHTML}
            <div class="tooltip-footer">Click for details</div>
        `;
    } else {
        return `
            <div class="tooltip-header">Query ${d.id}</div>
            <div class="tooltip-query">${d.preview || ''}</div>
            <div class="tooltip-stat">Total time: ${d.total_time.toFixed(2)} ms</div>
            <div class="tooltip-stat">Calls: ${d.calls}</div>
            <div class="tooltip-stat">Rows: ${d.rows}</div>
            <div class="tooltip-footer">Click for details</div>
        `;
    }
}

/**
 * Get related tables columns for table relationships
 */
function getConnectedTableColumnRelationships(tableNode) {
    const relationships = [];
    const tableId = tableNode.id;
    
    // Find tables that are directly connected to this table
    // (if there's a direct edge in the graph)
    lineageData.links.forEach(link => {
        if (link.source === tableId && link.target !== tableId 
            && !link.target.startsWith('Query_')) {
            // This table points to another table
            relationships.push({
                table: link.target,
                direction: 'to'
            });
        } else if (link.target === tableId && link.source !== tableId
                  && !link.source.startsWith('Query_')) {
            // Another table points to this table
            relationships.push({
                table: link.source,
                direction: 'from'
            });
        }
    });
    
    return relationships;
}

/**
 * Highlight connections for a node
 */
function highlightConnections(d) {
    // Get all nodes and links
    const allNodes = d3.selectAll('.lineage-node');
    const queryLinks = d3.selectAll('.query-link');
    const tableLinks = d3.selectAll('.table-link');
    const nodeLabels = d3.selectAll('.node-label-container');
    
    // Dim all nodes and links
    allNodes.style('opacity', 0.2);
    queryLinks.style('opacity', 0.1);
    tableLinks.style('opacity', 0.1);
    
    // Hide all labels initially
    nodeLabels.style('opacity', 0);
    
    // Get direct connections - nodes that are directly connected
    const directConnections = new Set();
    
    // First-level connections: Get all directly connected nodes
    queryLinks.each(function(l) {
        if (l.source.id === d.id) {
            directConnections.add(l.target.id);
        } else if (l.target.id === d.id) {
            directConnections.add(l.source.id);
        }
    });
    
    tableLinks.each(function(l) {
        if (l.source.id === d.id) {
            directConnections.add(l.target.id);
        } else if (l.target.id === d.id) {
            directConnections.add(l.source.id);
        }
    });
    
    // Create array from Set
    const connectedNodeIds = Array.from(directConnections);
    
    // Highlight the selected node
    allNodes.filter(n => n.id === d.id)
        .style('opacity', 1)
        .select('circle')
        .style('stroke-width', 3)
        .style('filter', 'url(#glow)');
    
    // Show label for the selected node
    nodeLabels.filter(function(n) { 
        return n.id === d.id; 
    }).style('opacity', 1);
    
    // Highlight directly connected nodes
    allNodes.filter(n => connectedNodeIds.includes(n.id))
        .style('opacity', 1)
        .select('circle')
        .style('stroke-width', 2.5)
        .style('filter', 'url(#glow)');
    
    // Show labels for connected nodes
    nodeLabels.filter(function(n) { 
        return connectedNodeIds.includes(n.id); 
    }).style('opacity', 0.9);
    
    // Highlight connected query links - all links that connect to this node
    queryLinks.filter(l => l.source.id === d.id || l.target.id === d.id)
        .style('opacity', 1)
        .style('stroke', '#7367F0') // Materio primary color
        .style('stroke-width', 2.5)
        .attr('marker-end', 'url(#arrowhead-highlight)');
    
    // Highlight connected table links
    tableLinks.filter(l => l.source.id === d.id || l.target.id === d.id)
        .style('opacity', 1)
        .style('stroke', '#7367F0') // Materio primary color
        .style('stroke-width', 2.5)
        .style('stroke-dasharray', '5,5') // Maintain dashed style
        .attr('marker-end', 'url(#table-arrowhead-highlight)');
}

/**
 * Reset all highlights
 */
function resetHighlights() {
    // Get all elements
    const allNodes = d3.selectAll('.lineage-node');
    const queryLinks = d3.selectAll('.query-link');
    const tableLinks = d3.selectAll('.table-link');
    const nodeLabels = d3.selectAll('.node-label-container');
    
    // Calculate label visibility threshold - only show labels for important nodes by default
    const totalNodes = lineageData.nodes.length;
    const container = document.getElementById('lineage-graph');
    const width = container.clientWidth;
    const height = container.clientHeight;
    const nodeDensity = totalNodes / (width * height) * 1000000; // Nodes per million pixels
    const importanceThreshold = Math.min(0.7, Math.max(0.3, nodeDensity / 15));
    
    // Reset node opacity, stroke and remove glow
    allNodes.style('opacity', 1)
        .select('circle')
        .style('stroke-width', 1.5)
        .style('filter', null);
    
    // Reset label visibility based on importance and top node status
    nodeLabels.style('opacity', function(d) {
        // Top nodes always have visible labels - reuse the topNodes set from initialization
        if (topNodes.has(d.id)) {
            return 1.0;
        }
        
        // For other nodes, use dynamic threshold
        // Recalculate normalized importance (0-1)
        let importance = 0;
        if (d.type === 'query') {
            const timeImportance = d.total_time ? 
                Math.log(d.total_time + 1) / Math.log(10000) : 0;
            const connectionImportance = d.connectionCount ? 
                Math.log(d.connectionCount + 1) / Math.log(20) : 0;
            importance = (timeImportance * 0.7) + (connectionImportance * 0.3);
        } else {
            const queryImportance = d.total_queries ? 
                Math.log(d.total_queries + 1) / Math.log(50) : 0;
            const connectionImportance = d.connectionCount ? 
                Math.log(d.connectionCount + 1) / Math.log(20) : 0;
            importance = (connectionImportance * 0.5) + (queryImportance * 0.5);
        }
        
        // Only show labels for important nodes
        return importance > importanceThreshold ? 0.9 : 0;
    });
    
    // Reset query links
    queryLinks.style('opacity', 0.6)
        .style('stroke', '#a8a8a8') // Lighter gray
        .style('stroke-width', 1.5)
        .attr('marker-end', 'url(#arrowhead)');
    
    // Reset table links
    tableLinks.style('opacity', 0.6)
        .style('stroke', '#28C76F') // Green
        .style('stroke-width', 2.0)
        .style('stroke-dasharray', '5,5') // Dashed
        .attr('marker-end', 'url(#table-arrowhead)');
}

/**
 * Add zoom controls to the visualization
 */
function addZoomControls(svg, zoom) {
    const controls = d3.select('#lineage-controls');
    
    controls.select('#zoom-in').on('click', () => {
        zoom.scaleBy(svg.transition().duration(750), 1.3);
    });
    
    controls.select('#zoom-out').on('click', () => {
        zoom.scaleBy(svg.transition().duration(750), 1 / 1.3);
    });
    
    controls.select('#zoom-reset').on('click', () => {
        zoomToFit();
    });
}

/**
 * Setup toggle handlers for layout options
 */
function setupLayoutToggles(simulation, schemas, schemaArray, tableNodesBySchema, width, height) {
    const schemaGroupingToggle = document.getElementById('schema-grouping');
    const connectivityLayoutToggle = document.getElementById('connectivity-layout');
    const floatingLabelsToggle = document.getElementById('floating-labels');
    
    // Handler for schema grouping toggle
    if (schemaGroupingToggle) {
        schemaGroupingToggle.addEventListener('change', function() {
            const useSchemaGrouping = this.checked;
            
            // Update schema visual elements visibility - excluding the overlay labels
            d3.selectAll('.schema-regions, .schema-separators').style('opacity', useSchemaGrouping ? 1 : 0);
            d3.selectAll('.schema-region').style('fill-opacity', useSchemaGrouping ? 1 : 0);
            
            // Update forces
            if (useSchemaGrouping) {
                // Enable schema-based positioning
                // Calculate column positions same as in initialization
                const schemaColumnPositions = schemaArray.map((schema, i) => 
                    width * (0.2 + (i / Math.max(1, schemas.size - 1)) * 0.6)
                );
                
                simulation.force('x', d3.forceX(d => {
                    if (d.type === 'table') {
                        // Position tables exactly on their schema column
                        const schemaIndex = schemaArray.indexOf(d.schema || 'public');
                        return schemaColumnPositions[schemaIndex]; // Use the exact same positions as visual elements
                    } else {
                        // Position queries based on their connectivity - but still keep schema influence
                        // Identify which schema this query is most connected to
                        let schemaConnectionCounts = {};
                        schemaArray.forEach(schema => schemaConnectionCounts[schema] = 0);
                        
                        // Count connections to tables in each schema
                        lineageData.links.forEach(link => {
                            if ((link.source === d.id || link.target === d.id)) {
                                // Get the other node in the link
                                const otherNodeId = link.source === d.id ? link.target : link.source;
                                const otherNode = lineageData.nodes.find(n => n.id === otherNodeId);
                                
                                // If it's a table, increment its schema count
                                if (otherNode && otherNode.type === 'table') {
                                    const schema = otherNode.schema || 'public';
                                    schemaConnectionCounts[schema] = (schemaConnectionCounts[schema] || 0) + 1;
                                }
                            }
                        });
                        
                        // Find most connected schema
                        let maxCount = 0;
                        let mostConnectedSchema = schemaArray[0];
                        for (const [schema, count] of Object.entries(schemaConnectionCounts)) {
                            if (count > maxCount) {
                                maxCount = count;
                                mostConnectedSchema = schema;
                            }
                        }
                        
                        // Position query between center and its most connected schema
                        const schemaIndex = schemaArray.indexOf(mostConnectedSchema);
                        const schemaX = schemaColumnPositions[schemaIndex];
                        // Position more toward schema column than center for better alignment
                        return (schemaX * 0.7 + width/2 * 0.3); // 70% schema position, 30% center
                    }
                }).strength(d => d.type === 'table' ? 0.9 : 0.4)); // Stronger forces for precise schema grouping
                
                simulation.force('y', d3.forceY(d => {
                    if (d.type === 'query') {
                        // Position queries vertically, center the most connected ones
                        return height * 0.5;
                    } else {
                        // Position tables along vertical column by schema
                        const schema = d.schema || 'public';
                        const tableIndex = tableNodesBySchema[schema].indexOf(d);
                        const totalTablesInSchema = tableNodesBySchema[schema].length;
                        
                        // Stagger tables in each schema vertically
                        return height * (0.2 + (tableIndex / Math.max(1, totalTablesInSchema - 1)) * 0.6);
                    }
                }).strength(d => d.type === 'table' ? 0.7 : 0.3));
                
                // Adjust charge for schema-based layout
                simulation.force('charge', d3.forceManyBody().strength(d => {
                    // Adjust repulsion based on node type
                    return d.type === 'table' ? -200 : -100;
                }));
            } else {
                // Disable schema-based positioning, use simpler type-based layout
                simulation.force('x', d3.forceX(d => {
                    // Position tables on the left, queries on the right
                    return d.type === 'table' ? width * 0.3 : width * 0.7;
                }).strength(0.1));
                
                simulation.force('y', d3.forceY(height / 2).strength(0.1));
                
                // Reset charge to default value
                simulation.force('charge', d3.forceManyBody().strength(-200));
            }
            
            // Restart simulation
            simulation.alpha(0.3).restart();
        });
    }
    
    // Handler for connectivity layout toggle
    if (connectivityLayoutToggle) {
        connectivityLayoutToggle.addEventListener('change', function() {
            const useConnectivityLayout = this.checked;
            
            if (useConnectivityLayout) {
                // Enable connectivity-based positioning
                simulation.force('connectivity', d3.forceRadial(d => {
                    // Position most connected nodes toward the center
                    if (d.connectionCount > 0) {
                        // Inverse relationship: more connections = closer to center
                        return Math.max(50, 300 / Math.sqrt(d.connectionCount));
                    }
                    return 300; // Default radius for unconnected nodes
                }, width / 2, height / 2).strength(0.3));
            } else {
                // Disable connectivity-based positioning
                simulation.force('connectivity', null);
            }
            
            // Restart simulation
            simulation.alpha(0.3).restart();
        });
    }
    
    // Handler for floating labels toggle
    if (floatingLabelsToggle) {
        floatingLabelsToggle.addEventListener('change', function() {
            const useFloatingLabels = this.checked;
            
            // Toggle visibility of floating schema labels
            d3.select('.schema-overlay').style('display', useFloatingLabels ? 'block' : 'none');
        });
    }
}

/**
 * Zoom to fit all content in the viewport
 */
function zoomToFit() {
    if (!lineageGraph || !lineageSvg || !lineageZoom) return;
    
    // Get the bounds of the graph
    const bounds = lineageGraph.node().getBBox();
    
    // Get the dimensions of the SVG container
    const container = document.getElementById('lineage-graph');
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    // Calculate scale and translation to fit all content
    // Increase the initial zoom level by using a higher factor (1.5 instead of 0.95)
    const scale = 1.5 / Math.max(
        bounds.width / width,
        bounds.height / height
    );
    
    const translateX = width / 2 - scale * (bounds.x + bounds.width / 2);
    const translateY = height / 2 - scale * (bounds.y + bounds.height / 2);
    
    // Apply the transform
    lineageSvg.transition()
        .duration(750)
        .call(
            lineageZoom.transform,
            d3.zoomIdentity
                .translate(translateX, translateY)
                .scale(scale)
        );
}