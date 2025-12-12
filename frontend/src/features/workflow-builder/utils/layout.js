/**
 * Auto-layout utilities for workflow nodes
 * 
 * Provides functions to automatically arrange nodes in a readable layout.
 */

/**
 * Calculate auto-layout positions for nodes based on their connections
 * Uses a simple left-to-right hierarchical layout
 * 
 * @param {Array} nodes - Array of nodes
 * @param {Array} edges - Array of edges
 * @param {Object} options - Layout options
 * @returns {Array} Nodes with updated positions
 */
export function autoLayout(nodes, edges, options = {}) {
  const {
    nodeWidth = 220,
    nodeHeight = 100,
    horizontalSpacing = 100,
    verticalSpacing = 60,
    startX = 50,
    startY = 50,
  } = options;

  if (nodes.length === 0) return nodes;

  // Build adjacency maps
  const outgoingEdges = new Map(); // nodeId -> [targetNodeIds]
  const incomingEdges = new Map(); // nodeId -> [sourceNodeIds]
  
  nodes.forEach(node => {
    outgoingEdges.set(node.id, []);
    incomingEdges.set(node.id, []);
  });

  edges.forEach(edge => {
    const outgoing = outgoingEdges.get(edge.source);
    if (outgoing) outgoing.push(edge.target);
    
    const incoming = incomingEdges.get(edge.target);
    if (incoming) incoming.push(edge.source);
  });

  // Find root nodes (nodes with no incoming edges)
  const rootNodes = nodes.filter(node => 
    incomingEdges.get(node.id)?.length === 0
  );

  // If no root nodes found, use the first node
  if (rootNodes.length === 0 && nodes.length > 0) {
    rootNodes.push(nodes[0]);
  }

  // Assign levels using BFS
  const levels = new Map(); // nodeId -> level
  const visited = new Set();
  const queue = [];

  // Start with root nodes at level 0
  rootNodes.forEach(node => {
    levels.set(node.id, 0);
    queue.push(node.id);
    visited.add(node.id);
  });

  // BFS to assign levels
  while (queue.length > 0) {
    const nodeId = queue.shift();
    const currentLevel = levels.get(nodeId);
    
    const targets = outgoingEdges.get(nodeId) || [];
    targets.forEach(targetId => {
      if (!visited.has(targetId)) {
        visited.add(targetId);
        levels.set(targetId, currentLevel + 1);
        queue.push(targetId);
      } else {
        // Update level if we found a longer path
        const existingLevel = levels.get(targetId);
        if (currentLevel + 1 > existingLevel) {
          levels.set(targetId, currentLevel + 1);
        }
      }
    });
  }

  // Handle disconnected nodes
  nodes.forEach(node => {
    if (!levels.has(node.id)) {
      levels.set(node.id, 0);
    }
  });

  // Group nodes by level
  const nodesByLevel = new Map();
  nodes.forEach(node => {
    const level = levels.get(node.id);
    if (!nodesByLevel.has(level)) {
      nodesByLevel.set(level, []);
    }
    nodesByLevel.get(level).push(node);
  });

  // Calculate positions
  const maxLevel = Math.max(...levels.values());
  const positionedNodes = nodes.map(node => {
    const level = levels.get(node.id);
    const nodesAtLevel = nodesByLevel.get(level);
    const indexAtLevel = nodesAtLevel.indexOf(node);
    const countAtLevel = nodesAtLevel.length;

    // Calculate x based on level (left to right)
    const x = startX + level * (nodeWidth + horizontalSpacing);

    // Calculate y to center nodes at each level
    const totalHeight = countAtLevel * nodeHeight + (countAtLevel - 1) * verticalSpacing;
    const levelStartY = startY + (maxLevel > 0 ? 0 : 0);
    const y = levelStartY + indexAtLevel * (nodeHeight + verticalSpacing);

    return {
      ...node,
      position: { x, y },
    };
  });

  return positionedNodes;
}

/**
 * Center the viewport on the nodes
 * 
 * @param {Array} nodes - Array of nodes
 * @param {Object} viewportSize - { width, height } of the viewport
 * @returns {Object} Viewport state { x, y, zoom }
 */
export function centerViewport(nodes, viewportSize = { width: 1200, height: 800 }) {
  if (nodes.length === 0) {
    return { x: 0, y: 0, zoom: 1 };
  }

  // Calculate bounding box
  let minX = Infinity, minY = Infinity;
  let maxX = -Infinity, maxY = -Infinity;

  nodes.forEach(node => {
    const { x, y } = node.position;
    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    maxX = Math.max(maxX, x + 220); // Approximate node width
    maxY = Math.max(maxY, y + 100); // Approximate node height
  });

  const contentWidth = maxX - minX;
  const contentHeight = maxY - minY;

  // Calculate zoom to fit
  const padding = 100;
  const zoomX = (viewportSize.width - padding * 2) / contentWidth;
  const zoomY = (viewportSize.height - padding * 2) / contentHeight;
  const zoom = Math.min(Math.max(Math.min(zoomX, zoomY), 0.25), 1.5);

  // Calculate center position
  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;

  const x = viewportSize.width / 2 - centerX * zoom;
  const y = viewportSize.height / 2 - centerY * zoom;

  return { x, y, zoom };
}

/**
 * Snap a position to a grid
 * 
 * @param {Object} position - { x, y }
 * @param {number} gridSize - Grid cell size
 * @returns {Object} Snapped position
 */
export function snapToGrid(position, gridSize = 20) {
  return {
    x: Math.round(position.x / gridSize) * gridSize,
    y: Math.round(position.y / gridSize) * gridSize,
  };
}

export default {
  autoLayout,
  centerViewport,
  snapToGrid,
};
