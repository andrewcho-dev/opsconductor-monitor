/**
 * ErrorMessage component.
 * 
 * Displays error messages with optional retry action.
 */

import React from 'react';
import { AlertTriangle, XCircle, RefreshCw } from 'lucide-react';

/**
 * ErrorMessage component
 * @param {Object} props
 * @param {string|Error} props.error - Error message or Error object
 * @param {string} props.title - Error title
 * @param {Function} props.onRetry - Retry callback
 * @param {string} props.className - Additional CSS classes
 */
export function ErrorMessage({ error, title = 'Error', onRetry, className = '' }) {
  const message = error instanceof Error ? error.message : error;
  
  return (
    <div className={`bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 ${className}`}>
      <div className="flex items-start gap-3">
        <XCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h3 className="text-sm font-medium text-red-800 dark:text-red-300">
            {title}
          </h3>
          <p className="mt-1 text-sm text-red-700 dark:text-red-400">
            {message || 'An unexpected error occurred'}
          </p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300"
            >
              <RefreshCw className="h-4 w-4" />
              Try again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Warning message variant
 */
export function WarningMessage({ message, title = 'Warning', className = '' }) {
  return (
    <div className={`bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 ${className}`}>
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 text-yellow-500 flex-shrink-0 mt-0.5" />
        <div>
          <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-300">
            {title}
          </h3>
          <p className="mt-1 text-sm text-yellow-700 dark:text-yellow-400">
            {message}
          </p>
        </div>
      </div>
    </div>
  );
}

/**
 * Empty state component
 */
export function EmptyState({ 
  icon: Icon, 
  title = 'No data', 
  message = 'No items to display',
  action,
  actionLabel,
  className = '' 
}) {
  return (
    <div className={`text-center py-12 ${className}`}>
      {Icon && (
        <Icon className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" />
      )}
      <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">
        {title}
      </h3>
      <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
        {message}
      </p>
      {action && actionLabel && (
        <button
          onClick={action}
          className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}

export default ErrorMessage;
