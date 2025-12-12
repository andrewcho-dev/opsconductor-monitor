/**
 * WorkflowsList
 * 
 * Workflow list content component with folders, tags, and workflow cards.
 * Used inside PageLayout wrapper.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus,
  Folder,
  FolderOpen,
  Tag,
  Search,
  MoreVertical,
  Play,
  Copy,
  Trash2,
  Edit,
  Clock,
  ChevronRight,
  ChevronDown,
  Settings,
} from 'lucide-react';
import * as workflowsApi from '../../api/workflows';
import { cn } from '../../lib/utils';
import { PageHeader } from '../../components/layout';

const WorkflowsList = () => {
  const navigate = useNavigate();
  
  // State
  const [workflows, setWorkflows] = useState([]);
  const [folders, setFolders] = useState([]);
  const [tags, setTags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Filters
  const [selectedFolder, setSelectedFolder] = useState(null);
  const [selectedTags, setSelectedTags] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  
  // UI state
  const [expandedFolders, setExpandedFolders] = useState(new Set());
  const [showNewFolderInput, setShowNewFolderInput] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [contextMenu, setContextMenu] = useState(null);

  // Load data
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [workflowsRes, foldersRes, tagsRes] = await Promise.all([
        workflowsApi.getWorkflows(),
        workflowsApi.getFolders(),
        workflowsApi.getTags(),
      ]);
      
      setWorkflows(workflowsRes.data || []);
      setFolders(foldersRes.data || []);
      setTags(tagsRes.data || []);
    } catch (err) {
      console.error('Failed to load data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Filter workflows
  const filteredWorkflows = workflows.filter(workflow => {
    // Folder filter
    if (selectedFolder !== null) {
      if (selectedFolder === 'root') {
        if (workflow.folder_id) return false;
      } else if (workflow.folder_id !== selectedFolder) {
        return false;
      }
    }
    
    // Tag filter
    if (selectedTags.length > 0) {
      const workflowTagIds = (workflow.tags || []).map(t => t.id);
      if (!selectedTags.some(tagId => workflowTagIds.includes(tagId))) {
        return false;
      }
    }
    
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      if (!workflow.name.toLowerCase().includes(query) &&
          !workflow.description?.toLowerCase().includes(query)) {
        return false;
      }
    }
    
    return true;
  });

  // Handlers
  const handleCreateWorkflow = () => {
    navigate('/workflows/new');
  };

  const handleEditWorkflow = (id) => {
    navigate(`/workflows/${id}`);
  };

  const handleRunWorkflow = async (id) => {
    try {
      await workflowsApi.runWorkflow(id);
      // Could show toast notification
    } catch (err) {
      console.error('Failed to run workflow:', err);
    }
  };

  const handleDuplicateWorkflow = async (workflow) => {
    try {
      const newName = `${workflow.name} (Copy)`;
      await workflowsApi.duplicateWorkflow(workflow.id, newName);
      loadData();
    } catch (err) {
      console.error('Failed to duplicate workflow:', err);
    }
  };

  const handleDeleteWorkflow = async (id) => {
    if (!confirm('Are you sure you want to delete this workflow?')) return;
    
    try {
      await workflowsApi.deleteWorkflow(id);
      loadData();
    } catch (err) {
      console.error('Failed to delete workflow:', err);
    }
  };

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return;
    
    try {
      await workflowsApi.createFolder({ name: newFolderName.trim() });
      setNewFolderName('');
      setShowNewFolderInput(false);
      loadData();
    } catch (err) {
      console.error('Failed to create folder:', err);
    }
  };

  const handleDeleteFolder = async (id) => {
    if (!confirm('Are you sure you want to delete this folder?')) return;
    
    try {
      await workflowsApi.deleteFolder(id);
      if (selectedFolder === id) setSelectedFolder(null);
      loadData();
    } catch (err) {
      console.error('Failed to delete folder:', err);
    }
  };

  const toggleTag = (tagId) => {
    setSelectedTags(prev => 
      prev.includes(tagId)
        ? prev.filter(id => id !== tagId)
        : [...prev, tagId]
    );
  };

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

  // Build folder tree
  const buildFolderTree = (parentId = null) => {
    return folders
      .filter(f => f.parent_id === parentId)
      .map(folder => ({
        ...folder,
        children: buildFolderTree(folder.id),
      }));
  };

  const folderTree = buildFolderTree();

  // Render folder item
  const renderFolderItem = (folder, depth = 0) => {
    const isSelected = selectedFolder === folder.id;
    const isExpanded = expandedFolders.has(folder.id);
    const hasChildren = folder.children?.length > 0;

    return (
      <div key={folder.id}>
        <div
          className={cn(
            'flex items-center gap-2 px-3 py-2 cursor-pointer rounded-md transition-colors',
            isSelected ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-100',
          )}
          style={{ paddingLeft: `${12 + depth * 16}px` }}
          onClick={() => setSelectedFolder(folder.id)}
        >
          {hasChildren ? (
            <button
              onClick={(e) => { e.stopPropagation(); toggleFolder(folder.id); }}
              className="p-0.5 hover:bg-gray-200 rounded"
            >
              {isExpanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </button>
          ) : (
            <span className="w-5" />
          )}
          {isSelected ? (
            <FolderOpen className="w-4 h-4" style={{ color: folder.color }} />
          ) : (
            <Folder className="w-4 h-4" style={{ color: folder.color }} />
          )}
          <span className="flex-1 truncate text-sm">{folder.name}</span>
          <span className="text-xs text-gray-400">{folder.workflow_count || 0}</span>
        </div>
        {hasChildren && isExpanded && (
          <div>
            {folder.children.map(child => renderFolderItem(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading workflows...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <PageHeader
        title="Workflows"
        description={`${filteredWorkflows.length} of ${workflows.length} workflows`}
        actions={
          <button
            onClick={handleCreateWorkflow}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-5 h-5" />
            New Workflow
          </button>
        }
      />

      <div className="p-4">
        {/* Filter Bar */}
        <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4">
          <div className="flex items-center gap-4 flex-wrap">
            {/* Search */}
            <div className="relative flex-1 min-w-[200px] max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search workflows..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Folder Filter */}
            <select
              value={selectedFolder === null ? 'all' : selectedFolder}
              onChange={(e) => setSelectedFolder(e.target.value === 'all' ? null : e.target.value)}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Folders ({workflows.length})</option>
              <option value="root">Uncategorized ({workflows.filter(w => !w.folder_id).length})</option>
              {folders.map(folder => (
                <option key={folder.id} value={folder.id}>{folder.name}</option>
              ))}
            </select>

            {/* Tags */}
            {tags.length > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">Tags:</span>
                {tags.map(tag => (
                  <button
                    key={tag.id}
                    onClick={() => toggleTag(tag.id)}
                    className={cn(
                      'px-2 py-1 text-xs rounded-full transition-colors',
                      selectedTags.includes(tag.id)
                        ? 'text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200',
                    )}
                    style={selectedTags.includes(tag.id) ? { backgroundColor: tag.color } : {}}
                  >
                    {tag.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Workflows Grid */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden p-6">
          {filteredWorkflows.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-gray-400 text-5xl mb-4">📋</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No workflows found</h3>
              <p className="text-gray-500 mb-4">
                {searchQuery || selectedTags.length > 0
                  ? 'Try adjusting your filters'
                  : 'Create your first workflow to get started'}
              </p>
              {!searchQuery && selectedTags.length === 0 && (
                <button
                  onClick={handleCreateWorkflow}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  <Plus className="w-5 h-5" />
                  Create Workflow
                </button>
              )}
            </div>
          ) : (
            <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
              {filteredWorkflows.map(workflow => (
                <div
                  key={workflow.id}
                  className="bg-white rounded-lg border border-gray-200 hover:shadow-md transition-shadow"
                >
                  <div className="p-4">
                    <div className="flex items-start justify-between mb-2">
                      <h3
                        className="font-semibold text-gray-900 cursor-pointer hover:text-blue-600"
                        onClick={() => handleEditWorkflow(workflow.id)}
                      >
                        {workflow.name}
                      </h3>
                      <div className="relative">
                        <button
                          onClick={() => setContextMenu(
                            contextMenu === workflow.id ? null : workflow.id
                          )}
                          className="p-1 hover:bg-gray-100 rounded"
                        >
                          <MoreVertical className="w-4 h-4 text-gray-500" />
                        </button>
                        {contextMenu === workflow.id && (
                          <div className="absolute right-0 top-8 w-40 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-10">
                            <button
                              onClick={() => { handleEditWorkflow(workflow.id); setContextMenu(null); }}
                              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
                            >
                              <Edit className="w-4 h-4" />
                              Edit
                            </button>
                            <button
                              onClick={() => { handleRunWorkflow(workflow.id); setContextMenu(null); }}
                              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
                            >
                              <Play className="w-4 h-4" />
                              Run
                            </button>
                            <button
                              onClick={() => { handleDuplicateWorkflow(workflow); setContextMenu(null); }}
                              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
                            >
                              <Copy className="w-4 h-4" />
                              Duplicate
                            </button>
                            <hr className="my-1" />
                            <button
                              onClick={() => { handleDeleteWorkflow(workflow.id); setContextMenu(null); }}
                              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
                            >
                              <Trash2 className="w-4 h-4" />
                              Delete
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                    
                    {workflow.description && (
                      <p className="text-sm text-gray-500 mb-3 line-clamp-2">
                        {workflow.description}
                      </p>
                    )}
                    
                    {/* Tags */}
                    {workflow.tags?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mb-3">
                        {workflow.tags.map(tag => (
                          <span
                            key={tag.id}
                            className="px-2 py-0.5 text-xs rounded-full text-white"
                            style={{ backgroundColor: tag.color }}
                          >
                            {tag.name}
                          </span>
                        ))}
                      </div>
                    )}
                    
                    {/* Footer */}
                    <div className="flex items-center justify-between text-xs text-gray-400">
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {workflow.updated_at
                          ? new Date(workflow.updated_at).toLocaleDateString()
                          : 'Never'}
                      </div>
                      {workflow.schedule && (
                        <span className="text-green-600">Scheduled</span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Click outside to close context menu */}
      {contextMenu && (
        <div
          className="fixed inset-0 z-0"
          onClick={() => setContextMenu(null)}
        />
      )}
    </>
  );
};

export default WorkflowsList;
