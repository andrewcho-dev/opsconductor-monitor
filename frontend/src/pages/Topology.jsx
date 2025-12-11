import { useState, useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Network, AlertCircle, RefreshCw } from "lucide-react";
import { cn } from "../lib/utils";
import { PageHeader } from "../components/layout";

// We'll use a simple implementation without vis.js for now
// In a real implementation, you'd install vis-network or use a similar library

export function Topology() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [hoveredEdge, setHoveredEdge] = useState(null);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
  const canvasRef = useRef(null);

  useEffect(() => {
    const ipsParam = searchParams.get('ips');
    let ipList = [];
    
    try {
      ipList = JSON.parse(decodeURIComponent(ipsParam || '[]'));
    } catch (e) {
      setError('Invalid IP list');
      setLoading(false);
      return;
    }

    if (ipList.length === 0) {
      setError('No devices selected');
      setLoading(false);
      return;
    }

    loadTopologyData(ipList);
  }, [searchParams]);

  const loadTopologyData = async (ipList) => {
    try {
      setLoading(true);
      const response = await fetch('/topology_data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ip_list: ipList }),
      });
      
      const data = await response.json();
      
      if (data.error) {
        setError(data.error);
      } else {
        setNodes(data.nodes || []);
        setEdges(data.edges || []);
      }
    } catch (err) {
      setError('Error loading topology: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCanvasClick = (event) => {
    // Simple click handling - in a real implementation with vis.js you'd handle this properly
    setSelectedNode(null);
  };

  const handleNodeClick = (node) => {
    setSelectedNode(node);
  };

  const handleEdgeHover = (edge, event) => {
    setHoveredEdge(edge);
    setTooltipPosition({ x: event.clientX + 15, y: event.clientY + 15 });
  };

  const handleEdgeLeave = () => {
    setHoveredEdge(null);
  };

  // Simple node positioning algorithm
  const getNodePosition = (index, total) => {
    const angle = (2 * Math.PI * index) / total;
    const radius = 200;
    const centerX = 400;
    const centerY = 300;
    
    return {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    };
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center gap-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="text-gray-600">Loading topology...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center gap-3 text-red-600">
          <AlertCircle className="w-6 h-6" />
          <span>{error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Network Topology"
        description={`${nodes.length} nodes • ${edges.length} connections`}
        icon={Network}
        actions={
          <button
            onClick={() => {
              const ipsParam = searchParams.get('ips');
              if (ipsParam) {
                try {
                  const ipList = JSON.parse(decodeURIComponent(ipsParam));
                  loadTopologyData(ipList);
                } catch (e) {}
              }
            }}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        }
      />

      {/* Content */}
      <div className="flex-1 relative bg-white m-4 rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        {/* Simple SVG-based topology visualization */}
        <svg
          ref={canvasRef}
          width="100%"
          height="100%"
          className="cursor-move"
          onClick={handleCanvasClick}
        >
          {/* Render edges */}
          {edges.map((edge, index) => {
            const fromNode = nodes.find(n => n.id === edge.from);
            const toNode = nodes.find(n => n.id === edge.to);
            
            if (!fromNode || !toNode) return null;
            
            const fromPos = getNodePosition(nodes.indexOf(fromNode), nodes.length);
            const toPos = getNodePosition(nodes.indexOf(toNode), nodes.length);
            
            return (
              <g key={index}>
                <line
                  x1={fromPos.x}
                  y1={fromPos.y}
                  x2={toPos.x}
                  y2={toPos.y}
                  stroke="#6B7280"
                  strokeWidth="2"
                  className="cursor-pointer hover:stroke-blue-500"
                  onMouseEnter={(e) => handleEdgeHover(edge, e)}
                  onMouseLeave={handleEdgeLeave}
                />
                {/* Edge label */}
                <text
                  x={(fromPos.x + toPos.x) / 2}
                  y={(fromPos.y + toPos.y) / 2}
                  fill="#374151"
                  fontSize="12"
                  textAnchor="middle"
                  className="pointer-events-none"
                >
                  {edge.label || ''}
                </text>
              </g>
            );
          })}
          
          {/* Render nodes */}
          {nodes.map((node, index) => {
            const position = getNodePosition(index, nodes.length);
            const isSelected = selectedNode?.id === node.id;
            
            return (
              <g key={node.id}>
                <rect
                  x={position.x - 60}
                  y={position.y - 25}
                  width="120"
                  height="50"
                  rx="4"
                  fill={isSelected ? "#3B82F6" : "#FFFFFF"}
                  stroke={isSelected ? "#1D4ED8" : "#D1D5DB"}
                  strokeWidth="2"
                  className="cursor-pointer hover:fill-blue-50"
                  onClick={() => handleNodeClick(node)}
                />
                <text
                  x={position.x}
                  y={position.y - 5}
                  fill={isSelected ? "#FFFFFF" : "#111827"}
                  fontSize="14"
                  fontWeight="bold"
                  textAnchor="middle"
                  className="pointer-events-none"
                >
                  {node.label || node.id}
                </text>
                <text
                  x={position.x}
                  y={position.y + 15}
                  fill={isSelected ? "#E5E7EB" : "#6B7280"}
                  fontSize="12"
                  textAnchor="middle"
                  className="pointer-events-none"
                >
                  {node.ip || ''}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Tooltip */}
        {hoveredEdge && (
          <div
            className="absolute bg-gray-800 text-white p-3 rounded-lg text-sm pointer-events-none z-50 max-w-xs"
            style={{
              left: `${tooltipPosition.x}px`,
              top: `${tooltipPosition.y}px`,
            }}
          >
            <div className="font-semibold mb-1">Connection Details</div>
            <div className="text-xs space-y-1">
              <div>From: {hoveredEdge.from}</div>
              <div>To: {hoveredEdge.to}</div>
              {hoveredEdge.title && <div>{hoveredEdge.title}</div>}
            </div>
          </div>
        )}

        {/* Node details panel */}
        {selectedNode && (
          <div className="absolute top-4 right-4 bg-white p-4 rounded-lg shadow-lg border border-gray-200 w-64">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-gray-800">Device Details</h3>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            </div>
            <div className="space-y-2 text-sm">
              <div>
                <span className="font-medium text-gray-600">Name:</span>
                <div className="text-gray-800">{selectedNode.label || selectedNode.id}</div>
              </div>
              <div>
                <span className="font-medium text-gray-600">IP Address:</span>
                <div className="text-gray-800">{selectedNode.ip || 'N/A'}</div>
              </div>
              <div>
                <span className="font-medium text-gray-600">MAC Address:</span>
                <div className="text-gray-800">{selectedNode.mac || 'N/A'}</div>
              </div>
              <div>
                <span className="font-medium text-gray-600">Vendor:</span>
                <div className="text-gray-800">{selectedNode.vendor || 'N/A'}</div>
              </div>
              <div>
                <span className="font-medium text-gray-600">Model:</span>
                <div className="text-gray-800">{selectedNode.model || 'N/A'}</div>
              </div>
            </div>
            <div className="mt-4 pt-3 border-t border-gray-200">
              <button
                onClick={() => navigate(`/device/${selectedNode.ip}`)}
                className="w-full px-3 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
              >
                View Device Details
              </button>
            </div>
          </div>
        )}

        {/* Legend */}
        <div className="absolute bottom-4 left-4 bg-white p-3 rounded-lg shadow-lg border border-gray-200">
          <h4 className="font-semibold text-gray-800 mb-2 text-sm">Legend</h4>
          <div className="space-y-1 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-white border-2 border-gray-300 rounded"></div>
              <span>Network Device</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-blue-500 border-2 border-blue-700 rounded"></div>
              <span>Selected Device</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-0 border-t-2 border-gray-500"></div>
              <span>LLDP Connection</span>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="absolute top-4 left-4 bg-white p-3 rounded-lg shadow-lg border border-gray-200">
          <h4 className="font-semibold text-gray-800 mb-2 text-sm">Topology Stats</h4>
          <div className="space-y-1 text-xs">
            <div className="flex justify-between gap-4">
              <span className="text-gray-600">Devices:</span>
              <span className="font-medium">{nodes.length}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-gray-600">Connections:</span>
              <span className="font-medium">{edges.length}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
