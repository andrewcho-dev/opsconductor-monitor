/**
 * CredentialHistoryModal Component
 * 
 * Displays the history of a credential.
 */

import React, { useState, useEffect } from 'react';
import { XCircle, RefreshCw } from 'lucide-react';
import { fetchApi } from '../../../lib/utils';

export function CredentialHistoryModal({ credential, onClose }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadHistory();
  }, [credential.id]);

  const loadHistory = async () => {
    try {
      const res = await fetchApi(`/credentials/v1/credentials/${credential.id}/history`);
      if (res.success) {
        setHistory(res.data.history);
      }
    } catch (err) {
      // Error loading history
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4 max-h-[80vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div>
            <h2 className="text-lg font-semibold">Credential History</h2>
            <p className="text-sm text-gray-500">{credential.name}</p>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <XCircle className="w-5 h-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex justify-center py-8">
              <RefreshCw className="w-6 h-6 animate-spin text-blue-600" />
            </div>
          ) : history.length === 0 ? (
            <p className="text-center text-gray-500 py-8">No history found</p>
          ) : (
            <div className="space-y-4">
              {history.map((entry) => (
                <div key={entry.id} className="flex gap-4 pb-4 border-b last:border-0">
                  <div className="flex-shrink-0 w-2 h-2 mt-2 rounded-full bg-blue-500" />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium capitalize">{entry.action}</span>
                      {!entry.success && (
                        <span className="text-xs text-red-600">Failed</span>
                      )}
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{entry.action_detail}</p>
                    <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                      <span>{new Date(entry.performed_at).toLocaleString()}</span>
                      <span>by {entry.performed_by || 'system'}</span>
                      {entry.target_device && <span>→ {entry.target_device}</span>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
