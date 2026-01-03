# OpsConductor Workflow Builder Documentation

The Visual Workflow Builder is a drag-and-drop interface for creating automation workflows without writing code. Built on React Flow, it allows users to compose complex multi-step operations by connecting nodes that represent actions, conditions, and data transformations.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Node Packages](#node-packages)
4. [Components](#components)
5. [Hooks](#hooks)
6. [Data Flow](#data-flow)
7. [Node Definition Schema](#node-definition-schema)
8. [Creating Custom Nodes](#creating-custom-nodes)
9. [Execution Engine](#execution-engine)

---

## Overview

### Key Features

- **Visual Canvas** - Drag-and-drop workflow design with React Flow
- **17 Node Packages** - Pre-built nodes for common operations
- **Platform-Specific Nodes** - Ciena SAOS, Axis Cameras, Windows, NetBox
- **Data Mapping** - Pass data between nodes with expressions
- **Real-time Validation** - Validate workflows before execution
- **Execution Debug View** - Step-by-step execution visualization
- **Undo/Redo** - Full history support

### Workflow Concepts

| Concept | Description |
|---------|-------------|
| **Workflow** | A complete automation definition with nodes and edges |
| **Node** | A single action or operation in the workflow |
| **Edge** | A connection between nodes defining execution order |
| **Package** | A collection of related node types |
| **Trigger** | A node that starts workflow execution |
| **Data Handle** | Input/output ports for passing data between nodes |

---

## Architecture

```
frontend/src/features/workflow-builder/
├── index.jsx                 # Feature export
├── dataTypes.js              # Data type definitions
├── platforms.js              # Platform definitions
│
├── components/               # UI Components
│   ├── WorkflowBuilder.jsx   # Main builder component
│   ├── WorkflowCanvas.jsx    # React Flow canvas
│   ├── WorkflowToolbar.jsx   # Save/run toolbar
│   ├── NodePalette.jsx       # Node selection sidebar
│   ├── NodeEditor.jsx        # Node configuration modal
│   ├── DataMappingPanel.jsx  # Data mapping UI
│   ├── ExpressionInput.jsx   # Expression editor
│   ├── ValidationPanel.jsx   # Validation results
│   ├── ExecutionDebugView.jsx # Execution visualization
│   ├── SaveValidationDialog.jsx # Pre-save validation
│   ├── PrerequisiteWarnings.jsx # Missing prerequisites
│   ├── PlatformBadge.jsx     # Platform indicator
│   ├── DataEdge.jsx          # Custom edge component
│   ├── NetBoxSelectors.jsx   # NetBox dropdown selectors
│   └── NetBoxDeviceSelector.jsx # NetBox device picker
│
├── hooks/                    # Custom Hooks
│   ├── useWorkflow.js        # Workflow state management
│   ├── useNodeEditor.js      # Node editor state
│   ├── useWorkflowValidation.js # Validation logic
│   ├── useWorkflowExecution.js  # Execution handling
│   ├── useDataMapping.js     # Data mapping logic
│   └── useUndoRedo.js        # Undo/redo history
│
├── packages/                 # Node Package Definitions
│   ├── index.js              # Package registry
│   ├── categories.js         # Category definitions
│   ├── core.js               # Core nodes (triggers, variables)
│   ├── network-discovery.js  # Ping, traceroute, port scan
│   ├── snmp.js               # SNMP get/walk
│   ├── ssh.js                # SSH commands
│   ├── database.js           # Database operations
│   ├── notifications.js      # Slack, email, webhook
│   ├── data-transform.js     # Data transformation
│   ├── flow-control.js       # If/else, loops, delays
│   ├── http-api.js           # HTTP requests
│   ├── file-storage.js       # File operations
│   ├── scheduling.js         # Scheduling nodes
│   ├── parser-format.js      # Parsing and formatting
│   ├── debug-utility.js      # Debug and logging
│   ├── ciena-saos.js         # Ciena SAOS platform
│   ├── axis-cameras.js       # Axis camera platform
│   ├── windows-systems.js    # Windows WinRM
│   └── netbox.js             # NetBox integration
│
├── nodes/                    # Custom Node Components
│   └── CustomNode.jsx        # Base custom node
│
├── services/                 # Services
│   └── workflowApi.js        # Workflow API calls
│
└── utils/                    # Utilities
    ├── layout.js             # Auto-layout algorithm
    ├── validation.js         # Validation helpers
    └── expressions.js        # Expression parsing
```

---

## Node Packages

### Package Registry

All packages are registered in `packages/index.js`:

```javascript
import corePackage from './core';
import networkDiscoveryPackage from './network-discovery';
// ... more imports

export const PACKAGES = {
  'core': corePackage,
  'network-discovery': networkDiscoveryPackage,
  'snmp': snmpPackage,
  'ssh': sshPackage,
  'database': databasePackage,
  'notifications': notificationsPackage,
  'ciena-saos': cienaSaosPackage,
  'data-transform': dataTransformPackage,
  'flow-control': flowControlPackage,
  'http-api': httpApiPackage,
  'file-storage': fileStoragePackage,
  'scheduling': schedulingPackage,
  'parser-format': parserFormatPackage,
  'debug-utility': debugUtilityPackage,
  'axis-cameras': axisCamerasPackage,
  'windows-systems': windowsSystemsPackage,
  'netbox': netboxPackage,
};

export const DEFAULT_ENABLED_PACKAGES = [
  'core', 'network-discovery', 'snmp', 'ssh', 'database',
  'notifications', 'ciena-saos', 'data-transform', 'flow-control',
  'http-api', 'file-storage', 'scheduling', 'parser-format',
  'debug-utility', 'axis-cameras', 'windows-systems', 'netbox',
];
```

### Available Packages

#### Core (`core.js`)

Essential workflow nodes:

| Node | Description |
|------|-------------|
| `trigger:manual` | Manual trigger to start workflow |
| `trigger:schedule` | Scheduled trigger (cron) |
| `trigger:webhook` | Webhook trigger |
| `trigger:event` | Event-based trigger |
| `core:set-variable` | Set a workflow variable |
| `core:get-variable` | Get a workflow variable |
| `core:comment` | Add a comment/note |

#### Network Discovery (`network-discovery.js`)

Network discovery and diagnostics:

| Node | Description |
|------|-------------|
| `network:ping` | ICMP ping a host |
| `network:traceroute` | Traceroute to host |
| `network:port-scan` | Scan ports on host |
| `network:dns-lookup` | DNS resolution |
| `network:arp-scan` | ARP network scan |

#### SNMP (`snmp.js`)

SNMP operations:

| Node | Description |
|------|-------------|
| `snmp:get` | SNMP GET operation |
| `snmp:walk` | SNMP WALK operation |
| `snmp:set` | SNMP SET operation |
| `snmp:bulk-get` | SNMP BULK GET |
| `snmp:trap-listener` | Listen for SNMP traps |

#### SSH (`ssh.js`)

SSH command execution:

| Node | Description |
|------|-------------|
| `ssh:command` | Execute SSH command |
| `ssh:script` | Execute multi-line script |
| `ssh:file-transfer` | SCP file transfer |
| `ssh:interactive` | Interactive SSH session |

#### Database (`database.js`)

Database operations:

| Node | Description |
|------|-------------|
| `db:query` | Execute SQL query |
| `db:upsert` | Insert or update record |
| `db:delete` | Delete records |
| `db:transaction` | Transaction wrapper |

#### Notifications (`notifications.js`)

Notification channels:

| Node | Description |
|------|-------------|
| `notify:slack` | Send Slack message |
| `notify:email` | Send email |
| `notify:teams` | Send Teams message |
| `notify:webhook` | Send webhook |
| `notify:sms` | Send SMS |
| `notify:template` | Send templated notification |

#### Data Transform (`data-transform.js`)

Data manipulation:

| Node | Description |
|------|-------------|
| `transform:map` | Map/transform data |
| `transform:filter` | Filter array |
| `transform:reduce` | Reduce array |
| `transform:merge` | Merge objects |
| `transform:split` | Split string/array |
| `transform:json-parse` | Parse JSON |
| `transform:json-stringify` | Stringify to JSON |
| `transform:regex` | Regex extraction |

#### Flow Control (`flow-control.js`)

Control flow nodes:

| Node | Description |
|------|-------------|
| `flow:if` | Conditional branch |
| `flow:switch` | Multi-way branch |
| `flow:loop` | Loop over array |
| `flow:delay` | Wait/delay |
| `flow:parallel` | Parallel execution |
| `flow:retry` | Retry on failure |
| `flow:catch` | Error handler |

#### HTTP API (`http-api.js`)

HTTP operations:

| Node | Description |
|------|-------------|
| `http:get` | HTTP GET request |
| `http:post` | HTTP POST request |
| `http:put` | HTTP PUT request |
| `http:delete` | HTTP DELETE request |
| `http:graphql` | GraphQL query |

#### File Storage (`file-storage.js`)

File operations:

| Node | Description |
|------|-------------|
| `file:read` | Read file |
| `file:write` | Write file |
| `file:delete` | Delete file |
| `file:list` | List directory |
| `file:copy` | Copy file |
| `file:move` | Move file |

#### Scheduling (`scheduling.js`)

Scheduling nodes:

| Node | Description |
|------|-------------|
| `schedule:cron` | Cron expression trigger |
| `schedule:interval` | Interval trigger |
| `schedule:once` | One-time scheduled run |

#### Parser Format (`parser-format.js`)

Parsing and formatting:

| Node | Description |
|------|-------------|
| `parse:csv` | Parse CSV |
| `parse:xml` | Parse XML |
| `parse:yaml` | Parse YAML |
| `format:csv` | Format to CSV |
| `format:xml` | Format to XML |
| `format:template` | Template rendering |

#### Debug Utility (`debug-utility.js`)

Debugging tools:

| Node | Description |
|------|-------------|
| `debug:log` | Log to console |
| `debug:breakpoint` | Pause execution |
| `debug:assert` | Assert condition |
| `debug:inspect` | Inspect data |

### Platform-Specific Packages

#### Ciena SAOS (`ciena-saos.js`)

Ciena SAOS network equipment:

| Node | Description |
|------|-------------|
| `ciena:port-show` | Show port status |
| `ciena:port-xcvr` | Show transceiver info |
| `ciena:port-diagnostics` | Port diagnostics |
| `ciena:lldp-remote` | LLDP neighbor info |
| `ciena:config-backup` | Backup configuration |
| `ciena:software-show` | Show software version |

#### Axis Cameras (`axis-cameras.js`)

Axis IP cameras:

| Node | Description |
|------|-------------|
| `axis:snapshot` | Capture snapshot |
| `axis:ptz-control` | PTZ camera control |
| `axis:get-params` | Get camera parameters |
| `axis:set-params` | Set camera parameters |
| `axis:event-stream` | Subscribe to events |

#### Windows Systems (`windows-systems.js`)

Windows management via WinRM:

| Node | Description |
|------|-------------|
| `winrm:command` | Run command |
| `winrm:powershell` | Run PowerShell |
| `winrm:service-status` | Get service status |
| `winrm:service-control` | Start/stop service |
| `winrm:registry-read` | Read registry |
| `winrm:registry-write` | Write registry |
| `winrm:file-copy` | Copy file |

#### NetBox (`netbox.js`)

NetBox DCIM/IPAM integration:

| Node | Description |
|------|-------------|
| `netbox:get-devices` | List devices |
| `netbox:get-device` | Get device details |
| `netbox:create-device` | Create device |
| `netbox:update-device` | Update device |
| `netbox:delete-device` | Delete device |
| `netbox:get-interfaces` | Get interfaces |
| `netbox:get-ip-addresses` | Get IP addresses |
| `netbox:get-sites` | Get sites |
| `netbox:get-prefixes` | Get prefixes |
| `netbox:autodiscovery` | Auto-discover and sync |

---

## Components

### WorkflowBuilder

Main component that orchestrates the builder:

```jsx
<WorkflowBuilder
  initialWorkflow={workflow}
  onSave={handleSave}
  onRun={handleRun}
  onTest={handleTest}
  onBack={handleBack}
  enabledPackages={['core', 'network-discovery', 'ssh']}
/>
```

Props:
- `initialWorkflow` - Workflow to load
- `onSave` - Save callback
- `onRun` - Run callback
- `onTest` - Test callback
- `onBack` - Back navigation callback
- `enabledPackages` - Array of enabled package IDs

### WorkflowCanvas

React Flow canvas for node manipulation:

```jsx
<WorkflowCanvas
  nodes={nodes}
  edges={edges}
  onNodesChange={onNodesChange}
  onEdgesChange={onEdgesChange}
  onConnect={onConnect}
  onNodeDoubleClick={openEditor}
/>
```

### NodePalette

Sidebar showing available nodes organized by category:

```jsx
<NodePalette
  enabledPackages={enabledPackages}
  onNodeDrag={handleNodeDrag}
/>
```

### NodeEditor

Modal for configuring node parameters:

```jsx
<NodeEditor
  isOpen={isEditorOpen}
  node={editingNode}
  nodeDefinition={nodeDefinition}
  formData={formData}
  errors={errors}
  onClose={closeEditor}
  onSave={saveNode}
  onChange={updateField}
/>
```

### ExecutionDebugView

Visualizes workflow execution results:

```jsx
<ExecutionDebugView
  isOpen={debugViewOpen}
  executionResult={executionResult}
  nodes={nodes}
  onClose={() => setDebugViewOpen(false)}
/>
```

### ValidationPanel

Shows validation errors and warnings:

```jsx
<ValidationPanel
  errors={validationErrors}
  warnings={validationWarnings}
  onErrorClick={focusNode}
/>
```

---

## Hooks

### useWorkflow

Manages workflow state with undo/redo:

```javascript
const {
  workflow,           // Current workflow object
  nodes,              // React Flow nodes
  edges,              // React Flow edges
  viewport,           // Canvas viewport
  isDirty,            // Has unsaved changes
  selectedNodes,      // Currently selected nodes
  selectedEdges,      // Currently selected edges
  canUndo,            // Can undo
  canRedo,            // Can redo
  undo,               // Undo function
  redo,               // Redo function
  onNodesChange,      // Node change handler
  onEdgesChange,      // Edge change handler
  onConnect,          // Connection handler
  addNode,            // Add new node
  updateNode,         // Update node data
  deleteSelected,     // Delete selected
  duplicateSelected,  // Duplicate selected
  updateWorkflowMeta, // Update workflow metadata
  updateViewport,     // Update viewport
  markClean,          // Mark as saved
  loadWorkflow,       // Load workflow
} = useWorkflow(initialWorkflow);
```

### useNodeEditor

Manages node editor state:

```javascript
const {
  isOpen,             // Editor is open
  editingNode,        // Node being edited
  nodeDefinition,     // Node type definition
  formData,           // Current form values
  errors,             // Validation errors
  openEditor,         // Open editor for node
  closeEditor,        // Close editor
  updateField,        // Update form field
  validate,           // Validate form
  getSaveData,        // Get data to save
  shouldShowParameter, // Check parameter visibility
} = useNodeEditor();
```

### useWorkflowValidation

Validates workflow structure:

```javascript
const {
  errors,             // Validation errors
  warnings,           // Validation warnings
  isValid,            // Workflow is valid
  validate,           // Run validation
} = useWorkflowValidation(nodes, edges);
```

### useDataMapping

Manages data mapping between nodes:

```javascript
const {
  availableVariables, // Variables from upstream nodes
  resolveExpression,  // Resolve expression to value
  validateExpression, // Validate expression syntax
} = useDataMapping(nodes, edges, currentNodeId);
```

---

## Data Flow

### Data Handles

Nodes have input and output handles for data flow:

```javascript
{
  inputs: [
    { id: 'target', label: 'Target', type: 'string', required: true },
    { id: 'options', label: 'Options', type: 'object' }
  ],
  outputs: [
    { id: 'result', label: 'Result', type: 'object' },
    { id: 'success', label: 'Success', type: 'boolean' }
  ]
}
```

### Expressions

Data is passed between nodes using expressions:

```javascript
// Reference output from previous node
"{{nodes.ping_1.outputs.result}}"

// Access nested properties
"{{nodes.ssh_1.outputs.stdout.lines[0]}}"

// Use workflow variables
"{{variables.target_host}}"

// Combine with static text
"Device {{nodes.lookup.outputs.hostname}} is {{nodes.ping.outputs.status}}"
```

### Data Types

Defined in `dataTypes.js`:

```javascript
export const DATA_TYPES = {
  string: { label: 'String', color: '#10b981' },
  number: { label: 'Number', color: '#3b82f6' },
  boolean: { label: 'Boolean', color: '#f59e0b' },
  object: { label: 'Object', color: '#8b5cf6' },
  array: { label: 'Array', color: '#ec4899' },
  any: { label: 'Any', color: '#6b7280' },
};
```

---

## Node Definition Schema

Each node type is defined with a schema:

```javascript
{
  // Identification
  id: 'network:ping',
  name: 'Ping',
  description: 'ICMP ping a host to check reachability',
  
  // Categorization
  category: 'discovery',
  package: 'network-discovery',
  
  // Visual
  icon: 'Activity',  // Lucide icon name
  color: '#10b981',
  
  // Platform (optional)
  platform: null,  // or 'ciena-saos', 'windows', etc.
  
  // Parameters
  parameters: [
    {
      id: 'target',
      label: 'Target Host',
      type: 'string',
      required: true,
      placeholder: '192.168.1.1',
      description: 'IP address or hostname to ping',
      validation: {
        pattern: '^[a-zA-Z0-9.-]+$',
        message: 'Invalid hostname or IP'
      }
    },
    {
      id: 'count',
      label: 'Ping Count',
      type: 'number',
      default: 4,
      min: 1,
      max: 100
    },
    {
      id: 'timeout',
      label: 'Timeout (ms)',
      type: 'number',
      default: 1000,
      min: 100,
      max: 30000
    }
  ],
  
  // Data handles
  inputs: [
    { id: 'target', label: 'Target', type: 'string' }
  ],
  outputs: [
    { id: 'success', label: 'Success', type: 'boolean' },
    { id: 'latency', label: 'Latency (ms)', type: 'number' },
    { id: 'packetLoss', label: 'Packet Loss %', type: 'number' },
    { id: 'rawOutput', label: 'Raw Output', type: 'string' }
  ],
  
  // Execution
  executor: 'network.ping',  // Backend executor to use
  
  // Prerequisites
  prerequisites: [
    { type: 'credential', credentialType: 'ssh' }  // Optional
  ],
  
  // Conditional parameters
  conditionalParameters: [
    {
      when: { parameter: 'advanced', equals: true },
      show: ['timeout', 'count']
    }
  ]
}
```

### Parameter Types

| Type | Description | UI Component |
|------|-------------|--------------|
| `string` | Text input | Input field |
| `number` | Numeric input | Number input |
| `boolean` | True/false | Checkbox/toggle |
| `select` | Single selection | Dropdown |
| `multiselect` | Multiple selection | Multi-select |
| `textarea` | Multi-line text | Textarea |
| `code` | Code editor | Monaco editor |
| `json` | JSON editor | JSON editor |
| `credential` | Credential selector | Credential picker |
| `expression` | Expression input | Expression editor |

---

## Creating Custom Nodes

### 1. Define the Node

Create or add to a package file:

```javascript
// packages/my-package.js
export default {
  id: 'my-package',
  name: 'My Package',
  description: 'Custom nodes for my use case',
  version: '1.0.0',
  
  nodes: {
    'my:custom-node': {
      id: 'my:custom-node',
      name: 'Custom Node',
      description: 'Does something custom',
      category: 'custom',
      icon: 'Zap',
      color: '#f59e0b',
      
      parameters: [
        {
          id: 'input',
          label: 'Input',
          type: 'string',
          required: true
        }
      ],
      
      outputs: [
        { id: 'result', label: 'Result', type: 'string' }
      ],
      
      executor: 'my.custom_executor'
    }
  }
};
```

### 2. Register the Package

Add to `packages/index.js`:

```javascript
import myPackage from './my-package';

export const PACKAGES = {
  // ... existing packages
  'my-package': myPackage,
};

export const DEFAULT_ENABLED_PACKAGES = [
  // ... existing packages
  'my-package',
];
```

### 3. Implement Backend Executor

Add executor in `backend/services/node_executors/`:

```python
# backend/services/node_executors/my_executor.py
class CustomExecutor:
    def execute(self, params, context):
        input_value = params.get('input')
        
        # Do something
        result = process(input_value)
        
        return {
            'success': True,
            'outputs': {
                'result': result
            }
        }
```

### 4. Register Backend Executor

Add to workflow engine:

```python
# backend/services/workflow_engine.py
from .node_executors.my_executor import CustomExecutor

self.node_executors['my.custom_executor'] = CustomExecutor()
```

---

## Execution Engine

### Backend Workflow Engine

The workflow engine (`backend/services/workflow_engine.py`) executes workflows:

```python
class WorkflowEngine:
    def execute(self, workflow_id, trigger_data=None):
        """Execute a workflow."""
        workflow = self.load_workflow(workflow_id)
        context = ExecutionContext(
            execution_id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            variables=trigger_data or {}
        )
        
        # Find trigger nodes
        triggers = self.find_trigger_nodes(workflow)
        
        # Execute from each trigger
        for trigger in triggers:
            self.execute_from_node(trigger, context)
        
        return context.to_result()
    
    def execute_from_node(self, node, context):
        """Execute a node and its downstream nodes."""
        # Get executor for node type
        executor = self.node_executors.get(node.executor)
        
        # Resolve input parameters
        params = self.resolve_parameters(node, context)
        
        # Execute
        result = executor.execute(params, context)
        
        # Store result
        context.node_results[node.id] = result
        
        # Execute downstream nodes
        for downstream in self.get_downstream_nodes(node):
            self.execute_from_node(downstream, context)
```

### Execution Context

```python
@dataclass
class ExecutionContext:
    execution_id: str
    workflow_id: str
    variables: Dict[str, Any]
    node_results: Dict[str, NodeResult]
    current_path: List[str]
```

### Node Result

```python
@dataclass
class NodeResult:
    node_id: str
    node_type: str
    status: NodeStatus  # pending, running, success, failure, skipped
    output_data: Dict[str, Any]
    error_message: Optional[str]
    started_at: datetime
    finished_at: datetime
    duration_ms: int
```

### Variable Resolution

The engine resolves expressions in parameters:

```python
def resolve_expression(self, expression, context):
    """Resolve {{...}} expressions."""
    # {{nodes.node_id.outputs.field}}
    # {{variables.name}}
    # {{context.execution_id}}
    
    pattern = r'\{\{([^}]+)\}\}'
    
    def replace(match):
        path = match.group(1)
        return self.get_value_by_path(path, context)
    
    return re.sub(pattern, replace, expression)
```

---

## Validation

### Workflow Validation

The validation system checks:

1. **Structure** - All nodes have required connections
2. **Parameters** - Required parameters are filled
3. **Types** - Data types match between connections
4. **Cycles** - No circular dependencies
5. **Prerequisites** - Required credentials/settings exist

### Validation Errors

```javascript
{
  type: 'error',
  nodeId: 'ssh_1',
  field: 'target',
  message: 'Target is required'
}
```

### Validation Warnings

```javascript
{
  type: 'warning',
  nodeId: 'notify_1',
  message: 'No notification channel configured'
}
```

---

## Best Practices

### Workflow Design

1. **Start with a trigger** - Every workflow needs a trigger node
2. **Use descriptive names** - Name nodes clearly
3. **Add comments** - Use comment nodes to document complex logic
4. **Handle errors** - Add catch nodes for error handling
5. **Test incrementally** - Test small sections before full workflow

### Performance

1. **Limit parallel nodes** - Too many parallel nodes can overwhelm resources
2. **Use appropriate timeouts** - Set realistic timeouts for network operations
3. **Batch operations** - Use batch nodes when operating on many targets
4. **Cache lookups** - Store lookup results in variables

### Security

1. **Use credential vault** - Never hardcode credentials
2. **Limit permissions** - Use least-privilege credentials
3. **Audit sensitive workflows** - Enable logging for sensitive operations
4. **Review before production** - Test workflows in non-production first
