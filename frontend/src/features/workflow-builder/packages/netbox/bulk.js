/**
 * NetBox Bulk Operations Nodes
 * 
 * Bulk update and tagging operations.
 */

import { PLATFORMS, PROTOCOLS } from '../../platforms';

const netboxPlatform = {
  platforms: [PLATFORMS.ANY],
  protocols: [PROTOCOLS.NETBOX],
};

export const bulkNodes = {
  'netbox:bulk-update': {
    name: 'Bulk Update Field',
    description: 'Update a field on multiple devices',
    category: 'configure',
    subcategory: 'netbox',
    ...netboxPlatform,
    icon: '📝',
    color: '#6366F1',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      { id: 'device_ids', type: 'number[]', label: 'Device IDs (override)' },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'updated', type: 'number[]', label: 'Updated Device IDs' },
      { id: 'errors', type: 'object[]', label: 'Errors' },
    ],
    
    parameters: [
      {
        id: 'device_ids',
        type: 'textarea',
        label: 'Device IDs',
        placeholder: '1\n2\n3',
        help: 'One device ID per line',
      },
      {
        id: 'field',
        type: 'select',
        label: 'Field to Update',
        required: true,
        options: [
          { value: 'status', label: 'Status' },
          { value: 'site', label: 'Site' },
          { value: 'role', label: 'Role' },
          { value: 'platform', label: 'Platform' },
          { value: 'description', label: 'Description' },
        ],
      },
      {
        id: 'value',
        type: 'text',
        label: 'New Value',
        required: true,
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'netbox',
      command: 'bulk.update_field',
    },
  },

  'netbox:bulk-tag': {
    name: 'Bulk Tag Devices',
    description: 'Add or remove tags from multiple devices',
    category: 'configure',
    subcategory: 'netbox',
    ...netboxPlatform,
    icon: '🏷️',
    color: '#6366F1',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      { id: 'device_ids', type: 'number[]', label: 'Device IDs (override)' },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'updated', type: 'number[]', label: 'Updated Device IDs' },
      { id: 'errors', type: 'object[]', label: 'Errors' },
    ],
    
    parameters: [
      {
        id: 'device_ids',
        type: 'textarea',
        label: 'Device IDs',
        placeholder: '1\n2\n3',
      },
      {
        id: 'tags',
        type: 'netbox-tags-selector',
        label: 'Tags to Add',
      },
      {
        id: 'remove_tags',
        type: 'netbox-tags-selector',
        label: 'Tags to Remove',
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'netbox',
      command: 'bulk.tag',
    },
  },
};
