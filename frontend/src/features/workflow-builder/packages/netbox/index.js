/**
 * NetBox Package
 * 
 * Nodes for NetBox integration:
 * - Device CRUD operations
 * - VM CRUD operations
 * - Interface management
 * - IP address management
 * - Discovery functions
 * - Bulk operations
 * - Lookup/reference data
 * - Autodiscovery
 * - SNMP Walker Discovery
 */

import { deviceNodes } from './device';
import { vmNodes } from './vm';
import { interfaceNodes } from './interface';
import { ipNodes } from './ip';
import { discoveryNodes } from './discovery';
import { bulkNodes } from './bulk';
import { lookupNodes } from './lookup';
import { autodiscoveryNodes } from './autodiscovery';
import { snmpWalkerNodes } from './snmp-walker';

export default {
  id: 'netbox',
  name: 'NetBox',
  description: 'NetBox DCIM/IPAM integration for device inventory management',
  version: '1.0.0',
  icon: '🗄️',
  color: '#00A4E4',
  
  nodes: {
    ...deviceNodes,
    ...vmNodes,
    ...interfaceNodes,
    ...ipNodes,
    ...discoveryNodes,
    ...bulkNodes,
    ...lookupNodes,
    ...autodiscoveryNodes,
    ...snmpWalkerNodes,
  },
};
