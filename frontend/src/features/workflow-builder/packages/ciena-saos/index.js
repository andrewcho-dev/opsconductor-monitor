/**
 * Ciena SAOS Package
 * 
 * Nodes for Ciena SAOS switch operations:
 * - Show Interface, Optics, LLDP, Alarms, Version, Port, XCVR
 * - Port Configuration (enable, disable, description)
 * - VLAN Management
 * - Service Configuration
 * - System Commands
 * - Traffic Profiles
 * - Ring Protection
 */

import { showNodes } from './show';
import { portConfigNodes } from './port-config';
import { vlanNodes } from './vlan';
import { serviceNodes } from './service';
import { systemNodes } from './system';
import { trafficNodes } from './traffic';
import { ringNodes } from './ring';

export default {
  id: 'ciena-saos',
  name: 'Ciena SAOS',
  description: 'Ciena SAOS 8.x switch commands for optical network management',
  version: '1.0.0',
  icon: '🔷',
  color: '#0066CC',
  vendor: 'Ciena',
  
  nodes: {
    ...showNodes,
    ...portConfigNodes,
    ...vlanNodes,
    ...serviceNodes,
    ...systemNodes,
    ...trafficNodes,
    ...ringNodes,
  },
};
