/**
 * GroupsList Component
 * 
 * Displays credential groups in a grid.
 */

import React from 'react';
import { FolderOpen } from 'lucide-react';

export function GroupsList({ groups, onRefresh }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {groups.length === 0 ? (
        <div className="col-span-full text-center py-12 bg-white rounded-lg border">
          <FolderOpen className="w-12 h-12 mx-auto text-gray-300" />
          <p className="mt-4 text-gray-500">No credential groups</p>
        </div>
      ) : (
        groups.map((group) => (
          <div key={group.id} className="bg-white rounded-lg border p-4">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-medium text-gray-900">{group.name}</h3>
                {group.description && (
                  <p className="text-sm text-gray-500 mt-1">{group.description}</p>
                )}
              </div>
              <FolderOpen className="w-5 h-5 text-gray-400" />
            </div>
            <div className="mt-4 pt-4 border-t">
              <p className="text-sm text-gray-500">
                {group.credentials?.length || 0} credentials
              </p>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
