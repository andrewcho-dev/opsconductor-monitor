/**
 * Alert Statistics Cards
 */

import { AlertCircle, AlertTriangle, Info, CheckCircle } from 'lucide-react';
import { SEVERITY_CONFIG } from '../../lib/constants';

export function AlertStats({ stats = {} }) {
  const {
    total_active = 0,
    by_severity = {},
  } = stats;

  const severityCounts = [
    { key: 'critical', ...SEVERITY_CONFIG.critical, count: by_severity.critical || 0 },
    { key: 'major', ...SEVERITY_CONFIG.major, count: by_severity.major || 0 },
    { key: 'minor', ...SEVERITY_CONFIG.minor, count: by_severity.minor || 0 },
    { key: 'warning', ...SEVERITY_CONFIG.warning, count: by_severity.warning || 0 },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
      {severityCounts.map(({ key, label, bgClass, textClass, icon: Icon, count }) => (
        <div
          key={key}
          className={`rounded-lg border p-4 ${count > 0 ? 'border-l-4 ' + (key === 'critical' ? 'border-l-red-500' : key === 'major' ? 'border-l-orange-500' : key === 'minor' ? 'border-l-yellow-500' : 'border-l-blue-500') : 'border-gray-200 dark:border-gray-700'}`}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                {label}
              </p>
              <p className={`text-2xl font-bold ${count > 0 ? textClass : 'text-gray-400'}`}>
                {count}
              </p>
            </div>
            <Icon className={`h-8 w-8 ${count > 0 ? textClass : 'text-gray-300'}`} />
          </div>
        </div>
      ))}
      
      {/* Total Active */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-800">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Total Active
            </p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {total_active}
            </p>
          </div>
          <AlertCircle className="h-8 w-8 text-gray-400" />
        </div>
      </div>
    </div>
  );
}

export default AlertStats;
