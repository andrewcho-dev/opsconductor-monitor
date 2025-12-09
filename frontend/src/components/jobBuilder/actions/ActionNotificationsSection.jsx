import React, { useState } from 'react';

export const ActionNotificationsSection = ({ action, actionIndex, updateAction }) => {
  const notifications = action.notifications || {
    enabled: false,
    on_success: false,
    on_failure: true,
    targets: []
  };

  const [testStatus, setTestStatus] = useState('');
  const [isTesting, setIsTesting] = useState(false);

  const targetsText = (notifications.targets || []).join('\n');

  const updateNotifications = (partial) => {
    const next = { ...notifications, ...partial };
    updateAction(actionIndex, 'notifications', next);
  };

  const handleTargetsChange = (value) => {
    const lines = value
      .split('\n')
      .map((v) => v.trim())
      .filter((v) => v.length > 0);
    updateNotifications({ targets: lines });
  };

  const handleTest = async () => {
    setTestStatus('');
    setIsTesting(true);
    try {
      const resp = await fetch('/api/notify/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          targets: notifications.targets || [],
          title: `Action ${actionIndex + 1} notification test`,
          body: 'This is a test notification from OpsConductor.',
          tag: 'jobbuilder.test'
        })
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        setTestStatus(data.error || 'Notification test failed');
      } else {
        setTestStatus('Notification sent successfully');
      }
    } catch (err) {
      setTestStatus('Notification test failed');
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="space-y-2 text-xs">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold flex items-center gap-1">
          <span>🔔</span>
          <span>Notifications</span>
        </h4>
        <label className="flex items-center gap-1 text-[11px]">
          <input
            type="checkbox"
            checked={!!notifications.enabled}
            onChange={(e) => updateNotifications({ enabled: e.target.checked })}
          />
          <span>Enabled</span>
        </label>
      </div>

      <div className="flex flex-wrap gap-3">
        <label className="flex items-center gap-1 text-[11px]">
          <input
            type="checkbox"
            checked={!!notifications.on_success}
            onChange={(e) => updateNotifications({ on_success: e.target.checked })}
          />
          <span>On success</span>
        </label>
        <label className="flex items-center gap-1 text-[11px]">
          <input
            type="checkbox"
            checked={!!notifications.on_failure}
            onChange={(e) => updateNotifications({ on_failure: e.target.checked })}
          />
          <span>On failure</span>
        </label>
      </div>

      <div className="space-y-1">
        <div className="flex items-center justify-between text-[11px] text-gray-700">
          <span>Apprise target URLs (one per line)</span>
        </div>
        <textarea
          className="w-full rounded border border-gray-300 bg-white p-1 font-mono text-[11px] leading-snug min-h-[60px]"
          value={targetsText}
          onChange={(e) => handleTargetsChange(e.target.value)}
          placeholder="mailtos://...\nslack://...\nmsteams://..."
        />
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleTest}
          disabled={!notifications.targets || notifications.targets.length === 0 || isTesting}
          className="rounded border border-blue-500 px-2 py-1 text-[11px] text-blue-700 hover:bg-blue-50 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {isTesting ? 'Testing...' : 'Send test notification'}
        </button>
        {testStatus && (
          <span className="text-[11px] text-gray-700 truncate" title={testStatus}>
            {testStatus}
          </span>
        )}
      </div>
    </div>
  );
};
