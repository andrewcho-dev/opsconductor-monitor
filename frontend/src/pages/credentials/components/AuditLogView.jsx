/**
 * AuditLogView Component
 * 
 * Displays credential audit log entries in a table.
 */

import React from 'react';
import { CheckCircle, XCircle } from 'lucide-react';
import { cn } from '../../../lib/utils';

const getActionColor = (action) => {
  switch (action) {
    case 'created': return 'bg-green-100 text-green-700';
    case 'updated': return 'bg-blue-100 text-blue-700';
    case 'deleted': return 'bg-red-100 text-red-700';
    case 'accessed': return 'bg-purple-100 text-purple-700';
    case 'used': return 'bg-cyan-100 text-cyan-700';
    case 'expired': return 'bg-amber-100 text-amber-700';
    default: return 'bg-gray-100 text-gray-700';
  }
};

export function AuditLogView({ entries }) {
  return (
    <div className="bg-white rounded-lg border overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Time</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Action</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Credential</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Performed By</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Target</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {entries.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-gray-500">
                  No audit entries found
                </td>
              </tr>
            ) : (
              entries.map((entry) => (
                <tr key={entry.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">
                    {new Date(entry.performed_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn("px-2 py-1 rounded-full text-xs font-medium", getActionColor(entry.action))}>
                      {entry.action}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{entry.credential_name}</div>
                    <div className="text-xs text-gray-500">{entry.credential_type}</div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {entry.performed_by || 'system'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {entry.target_device || '-'}
                  </td>
                  <td className="px-4 py-3">
                    {entry.success ? (
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-500" title={entry.error_message} />
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
