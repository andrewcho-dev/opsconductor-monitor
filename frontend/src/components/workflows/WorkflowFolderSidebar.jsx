/**
 * WorkflowFolderSidebar
 * 
 * Sidebar component for workflow folder navigation.
 * Shows folder tree with counts, +New Folder, and edit/delete controls.
 */

import React, { useState } from 'react';
import {
  Folder,
  FolderOpen,
  FolderPlus,
  ChevronRight,
  ChevronDown,
  MoreVertical,
  Edit,
  Trash2,
  Check,
  X,
} from 'lucide-react';
import { cn } from '../../lib/utils';

export function WorkflowFolderSidebar({
  folders = [],
  workflows = [],
  selectedFolder,
  onSelectFolder,
  onCreateFolder,
  onUpdateFolder,
  onDeleteFolder,
}) {
  const [expandedFolders, setExpandedFolders] = useState(new Set());
  const [showNewFolderInput, setShowNewFolderInput] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [editingFolder, setEditingFolder] = useState(null);
  const [editFolderName, setEditFolderName] = useState('');
  const [contextMenu, setContextMenu] = useState(null);

  // Calculate workflow counts per folder
  const getWorkflowCount = (folderId) => {
    if (folderId === null) {
      return workflows.filter(w => !w.folder_id).length;
    }
    return workflows.filter(w => w.folder_id === folderId).length;
  };

  const totalCount = workflows.length;
  const uncategorizedCount = getWorkflowCount(null);

  // Build folder tree
  const buildFolderTree = (parentId = null) => {
    return folders
      .filter(f => f.parent_id === parentId)
      .map(folder => ({
        ...folder,
        children: buildFolderTree(folder.id),
        workflowCount: getWorkflowCount(folder.id),
      }));
  };

  const folderTree = buildFolderTree();

  const toggleFolder = (folderId) => {
    setExpandedFolders(prev => {
      const next = new Set(prev);
      if (next.has(folderId)) {
        next.delete(folderId);
      } else {
        next.add(folderId);
      }
      return next;
    });
  };

  const handleCreateFolder = () => {
    if (!newFolderName.trim()) return;
    onCreateFolder({ name: newFolderName.trim() });
    setNewFolderName('');
    setShowNewFolderInput(false);
  };

  const handleStartEdit = (folder) => {
    setEditingFolder(folder.id);
    setEditFolderName(folder.name);
    setContextMenu(null);
  };

  const handleSaveEdit = () => {
    if (!editFolderName.trim()) return;
    onUpdateFolder(editingFolder, { name: editFolderName.trim() });
    setEditingFolder(null);
    setEditFolderName('');
  };

  const handleCancelEdit = () => {
    setEditingFolder(null);
    setEditFolderName('');
  };

  const handleDeleteFolder = (folderId) => {
    if (!confirm('Are you sure you want to delete this folder? Workflows will be moved to uncategorized.')) return;
    onDeleteFolder(folderId);
    setContextMenu(null);
    if (selectedFolder === folderId) {
      onSelectFolder(null);
    }
  };

  // Render folder item
  const renderFolderItem = (folder, depth = 0) => {
    const isSelected = selectedFolder === folder.id;
    const isExpanded = expandedFolders.has(folder.id);
    const hasChildren = folder.children?.length > 0;
    const isEditing = editingFolder === folder.id;

    return (
      <div key={folder.id}>
        <div
          className={cn(
            'group flex items-center gap-1 px-2 py-1.5 cursor-pointer rounded-md transition-colors text-sm',
            isSelected ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-100 text-gray-700',
          )}
          style={{ paddingLeft: `${8 + depth * 12}px` }}
          onClick={() => !isEditing && onSelectFolder(folder.id)}
        >
          {hasChildren ? (
            <button
              onClick={(e) => { e.stopPropagation(); toggleFolder(folder.id); }}
              className="p-0.5 hover:bg-gray-200 rounded flex-shrink-0"
            >
              {isExpanded ? (
                <ChevronDown className="w-3 h-3" />
              ) : (
                <ChevronRight className="w-3 h-3" />
              )}
            </button>
          ) : (
            <span className="w-4 flex-shrink-0" />
          )}
          
          {isSelected ? (
            <FolderOpen className="w-4 h-4 flex-shrink-0" style={{ color: folder.color || '#6b7280' }} />
          ) : (
            <Folder className="w-4 h-4 flex-shrink-0" style={{ color: folder.color || '#6b7280' }} />
          )}
          
          {isEditing ? (
            <div className="flex-1 flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
              <input
                type="text"
                value={editFolderName}
                onChange={(e) => setEditFolderName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSaveEdit();
                  if (e.key === 'Escape') handleCancelEdit();
                }}
                className="flex-1 px-1 py-0.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                autoFocus
              />
              <button onClick={handleSaveEdit} className="p-0.5 text-green-600 hover:bg-green-100 rounded">
                <Check className="w-3 h-3" />
              </button>
              <button onClick={handleCancelEdit} className="p-0.5 text-gray-500 hover:bg-gray-200 rounded">
                <X className="w-3 h-3" />
              </button>
            </div>
          ) : (
            <>
              <span className="flex-1 truncate">{folder.name}</span>
              <span className="text-xs text-gray-400 mr-1">{folder.workflowCount}</span>
              
              {/* Context menu button */}
              <div className="relative">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setContextMenu(contextMenu === folder.id ? null : folder.id);
                  }}
                  className="p-0.5 opacity-0 group-hover:opacity-100 hover:bg-gray-200 rounded transition-opacity"
                >
                  <MoreVertical className="w-3 h-3 text-gray-500" />
                </button>
                
                {contextMenu === folder.id && (
                  <>
                    <div className="fixed inset-0 z-10" onClick={() => setContextMenu(null)} />
                    <div className="absolute right-0 top-6 w-32 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-20">
                      <button
                        onClick={(e) => { e.stopPropagation(); handleStartEdit(folder); }}
                        className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100"
                      >
                        <Edit className="w-3 h-3" />
                        Rename
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDeleteFolder(folder.id); }}
                        className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50"
                      >
                        <Trash2 className="w-3 h-3" />
                        Delete
                      </button>
                    </div>
                  </>
                )}
              </div>
            </>
          )}
        </div>
        
        {hasChildren && isExpanded && (
          <div>
            {folder.children.map(child => renderFolderItem(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="py-2">
      {/* Section header */}
      <div className="px-4 py-1 mb-1">
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
          Folders
        </span>
      </div>

      {/* All Workflows */}
      <div
        className={cn(
          'flex items-center gap-2 px-4 py-2 cursor-pointer rounded-md mx-2 transition-colors text-sm',
          selectedFolder === 'all' ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-100 text-gray-700',
        )}
        onClick={() => onSelectFolder('all')}
      >
        <Folder className="w-4 h-4 text-gray-500" />
        <span className="flex-1">All Workflows</span>
        <span className="text-xs text-gray-400">{totalCount}</span>
      </div>

      {/* Uncategorized */}
      <div
        className={cn(
          'flex items-center gap-2 px-4 py-2 cursor-pointer rounded-md mx-2 transition-colors text-sm',
          selectedFolder === null ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-100 text-gray-700',
        )}
        onClick={() => onSelectFolder(null)}
      >
        <Folder className="w-4 h-4 text-gray-400" />
        <span className="flex-1">Uncategorized</span>
        <span className="text-xs text-gray-400">{uncategorizedCount}</span>
      </div>

      {/* Folder tree */}
      <div className="mx-2 mt-1">
        {folderTree.map(folder => renderFolderItem(folder))}
      </div>

      {/* New folder input */}
      {showNewFolderInput ? (
        <div className="mx-2 mt-2 flex items-center gap-1 px-2">
          <Folder className="w-4 h-4 text-gray-400 flex-shrink-0" />
          <input
            type="text"
            value={newFolderName}
            onChange={(e) => setNewFolderName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleCreateFolder();
              if (e.key === 'Escape') {
                setShowNewFolderInput(false);
                setNewFolderName('');
              }
            }}
            placeholder="Folder name..."
            className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
            autoFocus
          />
          <button onClick={handleCreateFolder} className="p-1 text-green-600 hover:bg-green-100 rounded">
            <Check className="w-4 h-4" />
          </button>
          <button
            onClick={() => { setShowNewFolderInput(false); setNewFolderName(''); }}
            className="p-1 text-gray-500 hover:bg-gray-200 rounded"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      ) : (
        <button
          onClick={() => setShowNewFolderInput(true)}
          className="flex items-center gap-2 px-4 py-2 mx-2 mt-2 text-sm text-gray-600 hover:bg-gray-100 rounded-md transition-colors w-[calc(100%-16px)]"
        >
          <FolderPlus className="w-4 h-4" />
          <span>New Folder</span>
        </button>
      )}
    </div>
  );
}

export default WorkflowFolderSidebar;
