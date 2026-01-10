/**
 * UI Constants
 * 
 * Styling constants for alerts, categories, and statuses.
 */

import {
  AlertCircle,
  AlertTriangle,
  Info,
  CheckCircle,
  HelpCircle,
  Network,
  Zap,
  Video,
  Wifi,
  Shield,
  Thermometer,
  Server,
  HardDrive,
  Box,
} from 'lucide-react';

/**
 * Severity configuration
 */
export const SEVERITY_CONFIG = {
  critical: {
    color: 'red',
    bgClass: 'bg-red-500',
    textClass: 'text-red-500',
    badgeClass: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    borderClass: 'border-red-500',
    icon: AlertCircle,
    label: 'Critical',
    order: 1,
  },
  major: {
    color: 'orange',
    bgClass: 'bg-orange-500',
    textClass: 'text-orange-500',
    badgeClass: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    borderClass: 'border-orange-500',
    icon: AlertTriangle,
    label: 'Major',
    order: 2,
  },
  minor: {
    color: 'yellow',
    bgClass: 'bg-yellow-500',
    textClass: 'text-yellow-500',
    badgeClass: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    borderClass: 'border-yellow-500',
    icon: AlertTriangle,
    label: 'Minor',
    order: 3,
  },
  warning: {
    color: 'blue',
    bgClass: 'bg-blue-500',
    textClass: 'text-blue-500',
    badgeClass: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    borderClass: 'border-blue-500',
    icon: Info,
    label: 'Warning',
    order: 4,
  },
  info: {
    color: 'gray',
    bgClass: 'bg-gray-500',
    textClass: 'text-gray-500',
    badgeClass: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
    borderClass: 'border-gray-500',
    icon: Info,
    label: 'Info',
    order: 5,
  },
  clear: {
    color: 'green',
    bgClass: 'bg-green-500',
    textClass: 'text-green-500',
    badgeClass: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    borderClass: 'border-green-500',
    icon: CheckCircle,
    label: 'Clear',
    order: 6,
  },
};

/**
 * Category configuration
 */
export const CATEGORY_CONFIG = {
  network: { icon: Network, label: 'Network', color: 'blue' },
  power: { icon: Zap, label: 'Power', color: 'yellow' },
  video: { icon: Video, label: 'Video', color: 'purple' },
  wireless: { icon: Wifi, label: 'Wireless', color: 'cyan' },
  security: { icon: Shield, label: 'Security', color: 'red' },
  environment: { icon: Thermometer, label: 'Environment', color: 'orange' },
  environmental: { icon: Thermometer, label: 'Environmental', color: 'orange' },
  compute: { icon: Server, label: 'Compute', color: 'indigo' },
  storage: { icon: HardDrive, label: 'Storage', color: 'slate' },
  application: { icon: Box, label: 'Application', color: 'pink' },
  availability: { icon: AlertCircle, label: 'Availability', color: 'red' },
  hardware: { icon: Server, label: 'Hardware', color: 'slate' },
  maintenance: { icon: Box, label: 'Maintenance', color: 'blue' },
  performance: { icon: Zap, label: 'Performance', color: 'purple' },
  unknown: { icon: HelpCircle, label: 'Unknown', color: 'gray' },
};

/**
 * Status configuration
 */
export const STATUS_CONFIG = {
  active: {
    color: 'red',
    bgClass: 'bg-red-100 text-red-800',
    label: 'Active',
  },
  acknowledged: {
    color: 'yellow',
    bgClass: 'bg-yellow-100 text-yellow-800',
    label: 'Acknowledged',
  },
  suppressed: {
    color: 'gray',
    bgClass: 'bg-gray-100 text-gray-800',
    label: 'Suppressed',
  },
  resolved: {
    color: 'green',
    bgClass: 'bg-green-100 text-green-800',
    label: 'Resolved',
  },
  expired: {
    color: 'gray',
    bgClass: 'bg-gray-100 text-gray-600',
    label: 'Expired',
  },
};

/**
 * Priority configuration
 */
export const PRIORITY_CONFIG = {
  P1: { color: 'red', label: 'P1 - Critical', description: 'Immediate response required' },
  P2: { color: 'orange', label: 'P2 - High', description: '15 minute response' },
  P3: { color: 'yellow', label: 'P3 - Medium', description: '1 hour response' },
  P4: { color: 'blue', label: 'P4 - Low', description: '4 hour response' },
  P5: { color: 'gray', label: 'P5 - Planning', description: 'Next business day' },
};

/**
 * Connector types
 */
export const CONNECTOR_TYPES = [
  { type: 'prtg', name: 'PRTG Network Monitor', icon: '📊' },
  { type: 'mcp', name: 'Ciena MCP', icon: '🌐' },
  { type: 'snmp_trap', name: 'SNMP Traps', icon: '📡' },
  { type: 'snmp_poll', name: 'SNMP Polling', icon: '🔄' },
  { type: 'eaton', name: 'Eaton UPS', icon: '🔋' },
  { type: 'axis', name: 'Axis Cameras', icon: '📹' },
  { type: 'milestone', name: 'Milestone VMS', icon: '🎬' },
  { type: 'cradlepoint', name: 'Cradlepoint', icon: '📶' },
  { type: 'ubiquiti', name: 'Ubiquiti', icon: '🛜' },
  { type: 'cisco_asa', name: 'Cisco ASA', icon: '🔒' },
];

/**
 * Get severity config with fallback
 */
export function getSeverityConfig(severity) {
  return SEVERITY_CONFIG[severity?.toLowerCase()] || SEVERITY_CONFIG.info;
}

/**
 * Get category config with fallback
 */
export function getCategoryConfig(category) {
  return CATEGORY_CONFIG[category?.toLowerCase()] || CATEGORY_CONFIG.unknown;
}

/**
 * Get status config with fallback
 */
export function getStatusConfig(status) {
  return STATUS_CONFIG[status?.toLowerCase()] || STATUS_CONFIG.active;
}

/**
 * Format relative time
 */
export function formatRelativeTime(dateString) {
  if (!dateString) return '';
  
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  
  return date.toLocaleDateString();
}
