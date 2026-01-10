/**
 * CredentialsList Component
 * 
 * Displays a table of credentials with actions.
 */

import React, { useState, useEffect } from 'react';
import { KeyRound, History, Pencil, Trash2, Server, ChevronDown, ChevronRight } from 'lucide-react';
import { cn, fetchApi } from '../../../lib/utils';
import { CREDENTIAL_TYPES, STATUS_COLORS } from './constants';

function DeviceAssociations({ credentialId, onClick }) {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDevices = async () => {
      try {
        const response = await fetchApi(`/credentials/v1/credentials/${credentialId}/devices`);
        setDevices(response.data?.devices || []);
      } catch (err) {
        console.error('Error fetching device associations:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchDevices();
  }, [credentialId]);

  if (loading) {
    return <span className="text-xs text-gray-400">...</span>;
  }

  return (
    <button
      onClick={onClick}
      className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 hover:underline"
    >
      <Server className="w-3 h-3" />
      <span>{devices.length}</span>
    </button>
  );
}

export function CredentialsList({ credentials, onEdit, onDelete, onViewHistory, onManageDevices, isExpiring }) {
  if (credentials.length === 0) {
    return (
      <div className="text-center py-12 bg-white rounded-lg border">
        <KeyRound className="w-12 h-12 mx-auto text-gray-300" />
        <p className="mt-4 text-gray-500">
          {isExpiring ? 'No credentials expiring soon' : 'No credentials found'}
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border overflow-hidden">
      <table className="w-full">
        <thead className="bg-gray-50 border-b">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Name</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Type</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Username</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Devices</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Expiration</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {credentials.map((cred) => {
            const typeInfo = CREDENTIAL_TYPES[cred.credential_type] || CREDENTIAL_TYPES.password;
            const TypeIcon = typeInfo.icon;
            
            return (
              <tr key={cred.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <div className="font-medium text-gray-900">{cred.name}</div>
                  {cred.description && (
                    <div className="text-sm text-gray-500 truncate max-w-xs">{cred.description}</div>
                  )}
                </td>
                <td className="px-4 py-3">
                  <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border", typeInfo.color)}>
                    <TypeIcon className="w-3 h-3" />
                    {typeInfo.label}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-gray-600">
                  {cred.username || '-'}
                </td>
                <td className="px-4 py-3">
                  <DeviceAssociations credentialId={cred.id} onClick={onManageDevices ? () => onManageDevices(cred) : undefined} />
                </td>
                <td className="px-4 py-3">
                  <span className={cn("px-2 py-1 rounded-full text-xs font-medium", STATUS_COLORS[cred.status] || STATUS_COLORS.active)}>
                    {cred.status || 'active'}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm">
                  {cred.valid_until ? (
                    <div className={cn(
                      cred.expiration_status === 'expired' && 'text-red-600',
                      cred.expiration_status === 'expiring_soon' && 'text-amber-600'
                    )}>
                      <div>{new Date(cred.valid_until).toLocaleDateString()}</div>
                      {cred.days_until_expiration !== null && (
                        <div className="text-xs">
                          {cred.days_until_expiration < 0 
                            ? `Expired ${Math.abs(cred.days_until_expiration)} days ago`
                            : `${cred.days_until_expiration} days left`}
                        </div>
                      )}
                    </div>
                  ) : (
                    <span className="text-gray-400">No expiration</span>
                  )}
                </td>
                <td className="px-4 py-3 text-sm text-gray-500">
                  {cred.last_used_at 
                    ? new Date(cred.last_used_at).toLocaleDateString()
                    : 'Never'}
                </td>
                <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                  <div className="flex items-center justify-end gap-1">
                    <button
                      onClick={() => onViewHistory(cred)}
                      className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded"
                      title="View History"
                    >
                      <History className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => onEdit(cred)}
                      className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded"
                      title="Edit"
                    >
                      <Pencil className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => onDelete(cred.id)}
                      className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
