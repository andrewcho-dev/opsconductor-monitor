/**
 * Alert Detail Page
 * 
 * Detailed view of a single alert with history and actions.
 */

import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft, Check, CheckCheck, MessageSquare, Clock, User,
  AlertCircle, Server, Network, RefreshCw
} from 'lucide-react';
import { useAlert, useAlertActions } from '../hooks/useAlerts';
import { SEVERITY_CONFIG, CATEGORY_CONFIG, STATUS_CONFIG, formatRelativeTime } from '../lib/constants';

export function AlertDetailPage() {
  const { alertId } = useParams();
  const navigate = useNavigate();
  const { alert, history, loading, error, refresh } = useAlert(alertId);
  const { acknowledgeAlert, resolveAlert, addNote, loading: actionLoading } = useAlertActions();
  
  const [noteText, setNoteText] = useState('');
  const [showNoteForm, setShowNoteForm] = useState(false);

  const handleAcknowledge = async () => {
    try {
      await acknowledgeAlert(alertId);
      refresh();
    } catch (err) {
      console.error('Failed to acknowledge:', err);
    }
  };

  const handleResolve = async () => {
    try {
      await resolveAlert(alertId);
      refresh();
    } catch (err) {
      console.error('Failed to resolve:', err);
    }
  };

  const handleAddNote = async (e) => {
    e.preventDefault();
    if (!noteText.trim()) return;
    
    try {
      await addNote(alertId, noteText);
      setNoteText('');
      setShowNoteForm(false);
      refresh();
    } catch (err) {
      console.error('Failed to add note:', err);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error || !alert) {
    return (
      <div className="min-h-screen bg-gray-100 dark:bg-gray-900 p-8">
        <div className="max-w-3xl mx-auto">
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
            <h2 className="text-lg font-medium text-red-800 dark:text-red-200">Error</h2>
            <p className="text-red-700 dark:text-red-300">{error || 'Alert not found'}</p>
            <Link to="/alerts" className="mt-4 inline-flex items-center text-blue-600 hover:underline">
              <ArrowLeft className="h-4 w-4 mr-1" />
              Back to alerts
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const severityConfig = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.info;
  const categoryConfig = CATEGORY_CONFIG[alert.category] || CATEGORY_CONFIG.unknown;
  const statusConfig = STATUS_CONFIG[alert.status] || STATUS_CONFIG.active;
  const SeverityIcon = severityConfig.icon;
  const CategoryIcon = categoryConfig.icon;

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Back Link */}
        <Link
          to="/alerts"
          className="inline-flex items-center text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-6"
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to alerts
        </Link>

        {/* Header */}
        <div className={`bg-white dark:bg-gray-800 rounded-lg border-l-4 ${severityConfig.borderClass} shadow-sm mb-6`}>
          <div className="p-6">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4">
                <div className={`p-3 rounded-lg ${severityConfig.badgeClass}`}>
                  <SeverityIcon className="h-6 w-6" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                    {alert.title}
                  </h1>
                  <div className="flex items-center gap-3 mt-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${severityConfig.badgeClass}`}>
                      {severityConfig.label}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusConfig.bgClass}`}>
                      {statusConfig.label}
                    </span>
                    <span className="text-sm text-gray-500 flex items-center gap-1">
                      <CategoryIcon className="h-4 w-4" />
                      {categoryConfig.label}
                    </span>
                  </div>
                </div>
              </div>
              
              {/* Actions */}
              <div className="flex items-center gap-2">
                <button
                  onClick={refresh}
                  className="p-2 text-gray-400 hover:text-gray-600 rounded"
                >
                  <RefreshCw className="h-5 w-5" />
                </button>
                {alert.status === 'active' && (
                  <button
                    onClick={handleAcknowledge}
                    disabled={actionLoading}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                  >
                    <Check className="h-4 w-4" />
                    Acknowledge
                  </button>
                )}
                {(alert.status === 'active' || alert.status === 'acknowledged') && (
                  <button
                    onClick={handleResolve}
                    disabled={actionLoading}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                  >
                    <CheckCheck className="h-4 w-4" />
                    Resolve
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Message */}
            {alert.message && (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
                <h2 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Message</h2>
                <pre className="text-gray-900 dark:text-white whitespace-pre-wrap font-mono text-sm bg-gray-50 dark:bg-gray-900 p-4 rounded">
                  {alert.message}
                </pre>
              </div>
            )}

            {/* Resolution Info - Show for resolved alerts */}
            {alert.status === 'resolved' && (alert.message_before_resolution || alert.resolution_message) && (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 border-l-4 border-green-500">
                <h2 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-4 flex items-center gap-2">
                  <CheckCheck className="h-4 w-4 text-green-500" />
                  Resolution Details
                </h2>
                <div className="space-y-4">
                  {alert.message_before_resolution && (
                    <div>
                      <h3 className="text-xs font-medium text-red-600 dark:text-red-400 uppercase tracking-wide mb-1">Before (Problem State)</h3>
                      <pre className="text-gray-900 dark:text-white whitespace-pre-wrap font-mono text-sm bg-red-50 dark:bg-red-900/20 p-3 rounded border border-red-200 dark:border-red-800">
                        {alert.message_before_resolution}
                      </pre>
                    </div>
                  )}
                  {alert.resolution_message && (
                    <div>
                      <h3 className="text-xs font-medium text-green-600 dark:text-green-400 uppercase tracking-wide mb-1">After (Resolved State)</h3>
                      <pre className="text-gray-900 dark:text-white whitespace-pre-wrap font-mono text-sm bg-green-50 dark:bg-green-900/20 p-3 rounded border border-green-200 dark:border-green-800">
                        {alert.resolution_message}
                      </pre>
                    </div>
                  )}
                  {alert.resolution_source && (
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Resolved by: <span className="font-medium">{alert.resolution_source.replace('_', ' ')}</span>
                      {alert.resolved_at && (
                        <span> at {new Date(alert.resolved_at).toLocaleString()}</span>
                      )}
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* History */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-medium text-gray-500 dark:text-gray-400">History</h2>
                <button
                  onClick={() => setShowNoteForm(!showNoteForm)}
                  className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
                >
                  <MessageSquare className="h-4 w-4" />
                  Add Note
                </button>
              </div>

              {showNoteForm && (
                <form onSubmit={handleAddNote} className="mb-4">
                  <textarea
                    value={noteText}
                    onChange={(e) => setNoteText(e.target.value)}
                    placeholder="Add a note..."
                    className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
                    rows={3}
                  />
                  <div className="flex justify-end gap-2 mt-2">
                    <button
                      type="button"
                      onClick={() => setShowNoteForm(false)}
                      className="px-3 py-1.5 text-gray-600 dark:text-gray-400 text-sm"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={!noteText.trim() || actionLoading}
                      className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
                    >
                      Save Note
                    </button>
                  </div>
                </form>
              )}

              <div className="space-y-4">
                {history.length === 0 ? (
                  <p className="text-gray-500 text-sm">No history entries</p>
                ) : (
                  history.map((entry, index) => (
                    <div key={entry.id || index} className="flex gap-3 text-sm">
                      <div className="flex-shrink-0">
                        <div className="w-8 h-8 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center">
                          {entry.action === 'created' && <AlertCircle className="h-4 w-4 text-gray-500" />}
                          {entry.action === 'acknowledged' && <Check className="h-4 w-4 text-blue-500" />}
                          {entry.action === 'resolved' && <CheckCheck className="h-4 w-4 text-green-500" />}
                          {entry.action === 'note_added' && <MessageSquare className="h-4 w-4 text-gray-500" />}
                        </div>
                      </div>
                      <div className="flex-1">
                        <p className="text-gray-900 dark:text-white">
                          <span className="font-medium capitalize">{entry.action.replace('_', ' ')}</span>
                          {entry.user_id && <span className="text-gray-500"> by {entry.user_id}</span>}
                        </p>
                        {entry.notes && (
                          <p className="text-gray-600 dark:text-gray-400 mt-1">{entry.notes}</p>
                        )}
                        <p className="text-gray-400 text-xs mt-1">
                          {formatRelativeTime(entry.created_at)}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Details */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
              <h2 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-4">Details</h2>
              <dl className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-500">Source</dt>
                  <dd className="text-gray-900 dark:text-white font-medium">{alert.source_system}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Device</dt>
                  <dd className="text-gray-900 dark:text-white">{alert.device_name || alert.device_ip || '-'}</dd>
                </div>
                {alert.device_ip && alert.device_name && (
                  <div className="flex justify-between">
                    <dt className="text-gray-500">IP Address</dt>
                    <dd className="text-gray-900 dark:text-white font-mono">{alert.device_ip}</dd>
                  </div>
                )}
                <div className="flex justify-between">
                  <dt className="text-gray-500">Alert Type</dt>
                  <dd className="text-gray-900 dark:text-white">{alert.alert_type}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-500">Occurrences</dt>
                  <dd className="text-gray-900 dark:text-white">{alert.occurrence_count}</dd>
                </div>
                {alert.priority && (
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Priority</dt>
                    <dd className="text-gray-900 dark:text-white font-medium">{alert.priority}</dd>
                  </div>
                )}
              </dl>
            </div>

            {/* Timestamps */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
              <h2 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-4">Timestamps</h2>
              <dl className="space-y-3 text-sm">
                <div>
                  <dt className="text-gray-500">Occurred</dt>
                  <dd className="text-gray-900 dark:text-white">
                    {new Date(alert.occurred_at).toLocaleString()}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Received</dt>
                  <dd className="text-gray-900 dark:text-white">
                    {new Date(alert.received_at).toLocaleString()}
                  </dd>
                </div>
                {alert.acknowledged_at && (
                  <div>
                    <dt className="text-gray-500">Acknowledged</dt>
                    <dd className="text-gray-900 dark:text-white">
                      {new Date(alert.acknowledged_at).toLocaleString()}
                      {alert.acknowledged_by && <span className="text-gray-500"> by {alert.acknowledged_by}</span>}
                    </dd>
                  </div>
                )}
                {alert.resolved_at && (
                  <div>
                    <dt className="text-gray-500">Resolved</dt>
                    <dd className="text-gray-900 dark:text-white">
                      {new Date(alert.resolved_at).toLocaleString()}
                      {alert.resolved_by && <span className="text-gray-500"> by {alert.resolved_by}</span>}
                    </dd>
                  </div>
                )}
              </dl>
            </div>

            {/* Correlation */}
            {alert.correlated_to_id && (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
                <h2 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-4">Correlation</h2>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                  This alert is suppressed due to upstream failure
                </p>
                <Link
                  to={`/alerts/${alert.correlated_to_id}`}
                  className="text-blue-600 hover:underline text-sm"
                >
                  View parent alert →
                </Link>
                {alert.correlation_rule && (
                  <p className="text-xs text-gray-500 mt-2">{alert.correlation_rule}</p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default AlertDetailPage;
