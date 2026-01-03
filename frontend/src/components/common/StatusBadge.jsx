/**
 * StatusBadge component.
 * 
 * Displays a colored badge indicating status.
 */

import React from 'react';

const STATUS_STYLES = {
  // Success states
  success: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  online: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  up: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  enabled: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  yes: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  
  // Error states
  error: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  offline: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  down: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  no: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  
  // Warning states
  warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
  timeout: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
  pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
  
  // Info states
  info: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
  running: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
  queued: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
  
  // Neutral states
  unknown: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
  disabled: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
  default: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
};

const SIZE_STYLES = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-0.5 text-sm',
  lg: 'px-3 py-1 text-base',
};

/**
 * StatusBadge component
 * @param {Object} props
 * @param {string} props.status - Status value (determines color)
 * @param {string} props.label - Display label (defaults to status)
 * @param {string} props.size - Size variant ('sm', 'md', 'lg')
 * @param {string} props.className - Additional CSS classes
 */
export function StatusBadge({ status, label, size = 'md', className = '' }) {
  const normalizedStatus = (status || 'unknown').toLowerCase().trim();
  const styleKey = Object.keys(STATUS_STYLES).find(key => 
    normalizedStatus.includes(key)
  ) || 'default';
  
  const statusStyle = STATUS_STYLES[styleKey];
  const sizeStyle = SIZE_STYLES[size] || SIZE_STYLES.md;
  
  return (
    <span 
      className={`inline-flex items-center font-medium rounded-full ${statusStyle} ${sizeStyle} ${className}`}
    >
      {label || status || 'Unknown'}
    </span>
  );
}

/**
 * Convenience components for common statuses
 */
export function OnlineBadge({ className }) {
  return <StatusBadge status="online" label="Online" className={className} />;
}

export function OfflineBadge({ className }) {
  return <StatusBadge status="offline" label="Offline" className={className} />;
}

export function EnabledBadge({ className }) {
  return <StatusBadge status="enabled" label="Enabled" className={className} />;
}

export function DisabledBadge({ className }) {
  return <StatusBadge status="disabled" label="Disabled" className={className} />;
}

export function SuccessBadge({ label = 'Success', className }) {
  return <StatusBadge status="success" label={label} className={className} />;
}

export function ErrorBadge({ label = 'Error', className }) {
  return <StatusBadge status="error" label={label} className={className} />;
}

export function RunningBadge({ className }) {
  return <StatusBadge status="running" label="Running" className={className} />;
}

export function QueuedBadge({ className }) {
  return <StatusBadge status="queued" label="Queued" className={className} />;
}

export default StatusBadge;
