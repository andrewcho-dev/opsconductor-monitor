/**
 * Compact Alert Detail Modal
 * Dense, organized display of alert information
 */

import { X } from 'lucide-react';
import { SEVERITY_CONFIG, CATEGORY_CONFIG } from '../../lib/constants';

export function AlertDetailModal({ alert, onClose }) {
  if (!alert) return null;

  const severityConfig = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.info;
  const categoryConfig = CATEGORY_CONFIG[alert.category] || CATEGORY_CONFIG.unknown;

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const d = new Date(dateStr);
    return d.toLocaleString('en-US', { 
      month: '2-digit', day: '2-digit', year: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
  };

  const Field = ({ label, value, mono = false, className = '' }) => (
    <div className={`${className}`}>
      <span className="text-[10px] text-gray-400 uppercase tracking-wide">{label}</span>
      <div className={`text-xs text-gray-900 dark:text-white ${mono ? 'font-mono' : ''}`}>
        {value || '-'}
      </div>
    </div>
  );

  const Section = ({ title, children }) => (
    <div className="mb-3">
      <div className="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider border-b border-gray-200 dark:border-gray-700 pb-1 mb-2">
        {title}
      </div>
      {children}
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div 
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-3xl w-full mx-4 max-h-[85vh] overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className={`px-4 py-2.5 flex items-center justify-between ${severityConfig.bgClass}`}>
          <div className="flex items-center gap-3 min-w-0">
            <span className="text-xs font-bold uppercase px-2 py-0.5 bg-black/10 rounded">{alert.severity}</span>
            <span className="text-sm font-medium truncate">{alert.title}</span>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-black/10 rounded">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="px-4 py-3 overflow-y-auto max-h-[calc(85vh-52px)]">
          
          {/* Status & Classification */}
          <Section title="Classification">
            <div className="grid grid-cols-4 gap-3">
              <Field label="Status" value={alert.status?.toUpperCase()} />
              <Field label="Severity" value={alert.severity?.toUpperCase()} />
              <Field label="Category" value={categoryConfig.label} />
              <Field label="Count" value={alert.occurrence_count || 1} />
            </div>
          </Section>

          {/* Device Information */}
          <Section title="Device">
            <div className="grid grid-cols-2 gap-3">
              <Field label="IP Address" value={alert.device_ip} mono />
              <Field label="Name" value={alert.device_name} />
            </div>
          </Section>

          {/* Source Information */}
          <Section title="Source">
            <div className="grid grid-cols-3 gap-3">
              <Field label="System" value={alert.source_system?.toUpperCase()} />
              <Field label="Alert Type" value={alert.alert_type} mono />
              <Field label="Source ID" value={alert.source_alert_id} mono />
            </div>
          </Section>

          {/* Timestamps */}
          <Section title="Timeline">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Occurred" value={formatDate(alert.occurred_at)} mono />
              <Field label="Created" value={formatDate(alert.created_at)} mono />
              <Field label="Updated" value={formatDate(alert.updated_at)} mono />
              {alert.resolved_at && <Field label="Resolved" value={formatDate(alert.resolved_at)} mono />}
            </div>
          </Section>

          {/* Message */}
          <Section title="Message">
            <div className="bg-gray-50 dark:bg-gray-900 rounded p-2 text-xs font-mono text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-all max-h-24 overflow-y-auto">
              {alert.message || '-'}
            </div>
          </Section>

          {/* Source Description - explains what this alert type means */}
          {alert.source_description && (
            <Section title="What This Means">
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded p-2 text-xs text-blue-800 dark:text-blue-200">
                {alert.source_description}
              </div>
            </Section>
          )}

          {/* Identifiers */}
          <Section title="Identifiers">
            <div className="space-y-1">
              <Field label="Alert ID" value={alert.id} mono />
              <Field label="Fingerprint" value={alert.fingerprint} mono />
            </div>
          </Section>

          {/* Raw Data if present */}
          {alert.raw_data && Object.keys(alert.raw_data).length > 0 && (
            <Section title="Raw Data">
              <pre className="text-[10px] text-gray-700 dark:text-gray-300 font-mono bg-gray-50 dark:bg-gray-900 p-2 rounded overflow-x-auto max-h-28">
                {JSON.stringify(alert.raw_data, null, 2)}
              </pre>
            </Section>
          )}
        </div>
      </div>
    </div>
  );
}

export default AlertDetailModal;
