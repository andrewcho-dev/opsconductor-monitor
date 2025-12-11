import React from 'react';
import { cn } from '../../lib/utils';

/**
 * PageHeader - Consistent page header with title, description, and actions
 * 
 * @param {string} title - Page title
 * @param {string} description - Optional description
 * @param {React.ReactNode} icon - Optional icon component
 * @param {React.ReactNode} actions - Optional action buttons
 * @param {string} className - Additional classes
 */
export function PageHeader({ title, description, icon: Icon, actions, className }) {
  return (
    <div className={cn(
      "bg-white border-b border-gray-200 px-6 py-4",
      className
    )}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {Icon && (
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <Icon className="w-5 h-5 text-blue-600" />
            </div>
          )}
          <div>
            <h1 className="text-xl font-bold text-gray-900">{title}</h1>
            {description && (
              <p className="text-sm text-gray-500 mt-0.5">{description}</p>
            )}
          </div>
        </div>
        {actions && (
          <div className="flex items-center gap-2">
            {actions}
          </div>
        )}
      </div>
    </div>
  );
}

export default PageHeader;
