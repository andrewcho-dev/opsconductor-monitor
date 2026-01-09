/**
 * Compact Alert Detail Modal
 * Dense, efficient display of alert information
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

  const Row = ({ label, value, mono = false }) => (
    <div className="flex border-b border-gray-100 dark:border-gray-700 py-1">
      <span className="w-24 text-xs text-gray-500 flex-shrink-0">{label}</span>
      <span className={`text-xs text-gray-900 dark:text-white flex-1 break-all ${mono ? 'font-mono' : ''}`}>
        {value || '-'}
      </span>
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div 
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[80vh] overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className={`px-3 py-2 flex items-center justify-between ${severityConfig.bgClass}`}>
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-xs font-bold uppercase">{alert.severity}</span>
            <span className="text-xs truncate">{alert.title}</span>
          </div>
          <button onClick={onClose} className="p-0.5 hover:bg-black/10 rounded">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="px-3 py-2 overflow-y-auto max-h-[calc(80vh-40px)]">
          <Row label="ID" value={alert.id} mono />
          <Row label="Status" value={alert.status?.toUpperCase()} />
          <Row label="Category" value={categoryConfig.label} />
          <Row label="Device IP" value={alert.device_ip} mono />
          <Row label="Device" value={alert.device_name} />
          <Row label="Source" value={alert.source_system?.toUpperCase()} />
          <Row label="Source ID" value={alert.source_alert_id} mono />
          <Row label="Alert Type" value={alert.alert_type} mono />
          <Row label="Occurred" value={formatDate(alert.occurred_at)} mono />
          <Row label="Created" value={formatDate(alert.created_at)} mono />
          <Row label="Updated" value={formatDate(alert.updated_at)} mono />
          {alert.resolved_at && <Row label="Resolved" value={formatDate(alert.resolved_at)} mono />}
          <Row label="Occurrences" value={alert.occurrence_count || 1} />
          <Row label="Fingerprint" value={alert.fingerprint} mono />
          
          {/* Message - full width */}
          <div className="border-b border-gray-100 dark:border-gray-700 py-1">
            <span className="text-xs text-gray-500 block mb-0.5">Message</span>
            <span className="text-xs text-gray-900 dark:text-white font-mono break-all whitespace-pre-wrap">
              {alert.message || '-'}
            </span>
          </div>

          {/* Raw Data if present */}
          {alert.raw_data && Object.keys(alert.raw_data).length > 0 && (
            <div className="py-1">
              <span className="text-xs text-gray-500 block mb-0.5">Raw Data</span>
              <pre className="text-[10px] text-gray-700 dark:text-gray-300 font-mono bg-gray-50 dark:bg-gray-900 p-1 rounded overflow-x-auto max-h-32">
                {JSON.stringify(alert.raw_data, null, 1)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default AlertDetailModal;
