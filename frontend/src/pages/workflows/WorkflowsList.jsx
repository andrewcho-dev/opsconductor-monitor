/**
 * WorkflowsList
 * 
 * Workflow list content component with datatable view.
 * Folders are displayed in the sidebar via WorkflowFolderSidebar.
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus,
  Search,
  MoreVertical,
  Play,
  Copy,
  Trash2,
  Edit,
  Clock,
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
  Calendar,
  Tag,
  Folder,
} from 'lucide-react';
import * as workflowsApi from '../../api/workflows';
import { cn } from '../../lib/utils';
import { PageHeader } from '../../components/layout';
import { WorkflowFolderSidebar } from '../../components/workflows';

const WorkflowsList = () => {
  const navigate = useNavigate();
  
  // State
  const [workflows, setWorkflows] = useState([]);
  const [folders, setFolders] = useState([]);
  const [tags, setTags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Filters
  const [selectedFolder, setSelectedFolder] = useState('all');
  const [selectedTags, setSelectedTags] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Table state
  const [sortConfig, setSortConfig] = useState({ key: 'name', direction: 'asc' });
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

  // Filter and sort workflows
  const filteredWorkflows = useMemo(() => {
    let result = workflows.filter(workflow => {
      // Folder filter
      if (selectedFolder !== 'all') {
        if (selectedFolder === null) {
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

    // Sort
    result.sort((a, b) => {
      let aVal = a[sortConfig.key];
      let bVal = b[sortConfig.key];
      
      // Handle dates
      if (sortConfig.key === 'updated_at' || sortConfig.key === 'created_at') {
        aVal = aVal ? new Date(aVal).getTime() : 0;
        bVal = bVal ? new Date(bVal).getTime() : 0;
      }
      
      // Handle strings
      if (typeof aVal === 'string') aVal = aVal.toLowerCase();
      if (typeof bVal === 'string') bVal = bVal.toLowerCase();
      
      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });

    return result;
  }, [workflows, selectedFolder, selectedTags, searchQuery, sortConfig]);

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

  const handleCreateFolder = async (folderData) => {
    try {
      await workflowsApi.createFolder(folderData);
      loadData();
    } catch (err) {
      console.error('Failed to create folder:', err);
    }
  };

  const handleUpdateFolder = async (id, folderData) => {
    try {
      await workflowsApi.updateFolder(id, folderData);
      loadData();
    } catch (err) {
      console.error('Failed to update folder:', err);
    }
  };

  const handleDeleteFolder = async (id) => {
    try {
      await workflowsApi.deleteFolder(id);
      if (selectedFolder === id) setSelectedFolder('all');
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

  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  // Get folder name by ID
  const getFolderName = (folderId) => {
    if (!folderId) return 'Uncategorized';
    const folder = folders.find(f => f.id === folderId);
    return folder?.name || 'Unknown';
  };

  // Sort icon component
  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) {
      return <ChevronsUpDown className="w-4 h-4 text-gray-400" />;
    }
    return sortConfig.direction === 'asc' ? (
      <ChevronUp className="w-4 h-4 text-blue-600" />
    ) : (
      <ChevronDown className="w-4 h-4 text-blue-600" />
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
    <div className="flex h-full">
      {/* Folder Sidebar */}
      <div className="w-56 border-r border-gray-200 bg-white overflow-y-auto flex-shrink-0">
        <WorkflowFolderSidebar
          folders={folders}
          workflows={workflows}
          selectedFolder={selectedFolder}
          onSelectFolder={setSelectedFolder}
          onCreateFolder={handleCreateFolder}
          onUpdateFolder={handleUpdateFolder}
          onDeleteFolder={handleDeleteFolder}
        />
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
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

        <div className="flex-1 overflow-auto p-4">
          {/* Filter Bar */}
          <div className="bg-white rounded-lg border border-gray-200 p-3 mb-4">
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

              {/* Tags */}
              {tags.length > 0 && (
                <div className="flex items-center gap-2">
                  <Tag className="w-4 h-4 text-gray-400" />
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

          {/* Workflows Table */}
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
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
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th
                      className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      onClick={() => handleSort('name')}
                    >
                      <div className="flex items-center gap-1">
                        Name
                        <SortIcon columnKey="name" />
                      </div>
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Description
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Folder
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Tags
                    </th>
                    <th
                      className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      onClick={() => handleSort('updated_at')}
                    >
                      <div className="flex items-center gap-1">
                        Updated
                        <SortIcon columnKey="updated_at" />
                      </div>
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Schedule
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredWorkflows.map(workflow => (
                    <tr
                      key={workflow.id}
                      className="hover:bg-gray-50 transition-colors"
                    >
                      <td className="px-4 py-3">
                        <button
                          onClick={() => handleEditWorkflow(workflow.id)}
                          className="font-medium text-gray-900 hover:text-blue-600 text-left"
                        >
                          {workflow.name}
                        </button>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 max-w-xs truncate">
                        {workflow.description || '-'}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1 text-sm text-gray-600">
                          <Folder className="w-3 h-3" />
                          {getFolderName(workflow.folder_id)}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {workflow.tags?.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {workflow.tags.slice(0, 3).map(tag => (
                              <span
                                key={tag.id}
                                className="px-2 py-0.5 text-xs rounded-full text-white"
                                style={{ backgroundColor: tag.color }}
                              >
                                {tag.name}
                              </span>
                            ))}
                            {workflow.tags.length > 3 && (
                              <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600">
                                +{workflow.tags.length - 3}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-sm text-gray-400">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        <div className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {workflow.updated_at
                            ? new Date(workflow.updated_at).toLocaleDateString()
                            : '-'}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {workflow.schedule ? (
                          <div className="flex items-center gap-1 text-sm text-green-600">
                            <Calendar className="w-3 h-3" />
                            Active
                          </div>
                        ) : (
                          <span className="text-sm text-gray-400">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="relative inline-block">
                          <button
                            onClick={() => setContextMenu(
                              contextMenu === workflow.id ? null : workflow.id
                            )}
                            className="p-1 hover:bg-gray-100 rounded"
                          >
                            <MoreVertical className="w-4 h-4 text-gray-500" />
                          </button>
                          {contextMenu === workflow.id && (
                            <>
                              <div className="fixed inset-0 z-10" onClick={() => setContextMenu(null)} />
                              <div className="absolute right-0 top-8 w-40 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-20">
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
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default WorkflowsList;
