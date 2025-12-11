/**
 * LoadingSpinner component.
 * 
 * Displays a loading indicator.
 */

import React from 'react';
import { Loader2 } from 'lucide-react';

const SIZE_STYLES = {
  sm: 'h-4 w-4',
  md: 'h-6 w-6',
  lg: 'h-8 w-8',
  xl: 'h-12 w-12',
};

/**
 * LoadingSpinner component
 * @param {Object} props
 * @param {string} props.size - Size variant ('sm', 'md', 'lg', 'xl')
 * @param {string} props.className - Additional CSS classes
 * @param {string} props.label - Accessible label
 */
export function LoadingSpinner({ size = 'md', className = '', label = 'Loading...' }) {
  const sizeStyle = SIZE_STYLES[size] || SIZE_STYLES.md;
  
  return (
    <Loader2 
      className={`animate-spin text-blue-500 ${sizeStyle} ${className}`}
      aria-label={label}
    />
  );
}

/**
 * Full page loading overlay
 */
export function LoadingOverlay({ message = 'Loading...' }) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 flex flex-col items-center gap-4">
        <LoadingSpinner size="xl" />
        <p className="text-gray-600 dark:text-gray-300">{message}</p>
      </div>
    </div>
  );
}

/**
 * Inline loading state for content areas
 */
export function LoadingState({ message = 'Loading...', className = '' }) {
  return (
    <div className={`flex items-center justify-center py-8 ${className}`}>
      <div className="flex flex-col items-center gap-3">
        <LoadingSpinner size="lg" />
        <p className="text-gray-500 dark:text-gray-400 text-sm">{message}</p>
      </div>
    </div>
  );
}

/**
 * Skeleton loader for content placeholders
 */
export function Skeleton({ className = '', width, height }) {
  const style = {};
  if (width) style.width = width;
  if (height) style.height = height;
  
  return (
    <div 
      className={`animate-pulse bg-gray-200 dark:bg-gray-700 rounded ${className}`}
      style={style}
    />
  );
}

/**
 * Table row skeleton
 */
export function TableRowSkeleton({ columns = 5 }) {
  return (
    <tr>
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <Skeleton className="h-4 w-full" />
        </td>
      ))}
    </tr>
  );
}

export default LoadingSpinner;
