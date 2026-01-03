/**
 * Workflows API Client
 * 
 * API functions for workflow CRUD operations.
 * Follows the same pattern as other API clients in the system.
 */

import { fetchApi } from '../lib/utils';

const BASE_URL = '/api/workflows';

/**
 * Get all workflows with optional filters
 * @param {Object} options - Filter options
 * @param {string} options.folder_id - Filter by folder
 * @param {string[]} options.tags - Filter by tags
 * @param {string} options.search - Search term
 * @returns {Promise<Object>} List of workflows
 */
export async function getWorkflows(options = {}) {
  const params = new URLSearchParams();
  
  if (options.folder_id) params.append('folder_id', options.folder_id);
  if (options.tags?.length) params.append('tags', options.tags.join(','));
  if (options.search) params.append('search', options.search);
  
  const queryString = params.toString();
  const url = queryString ? `${BASE_URL}?${queryString}` : BASE_URL;
  
  return fetchApi(url);
}

/**
 * Get a single workflow by ID
 * @param {string} id - Workflow ID
 * @returns {Promise<Object>} Workflow data
 */
export async function getWorkflow(id) {
  return fetchApi(`${BASE_URL}/${id}`);
}

/**
 * Create a new workflow
 * @param {Object} workflow - Workflow data
 * @returns {Promise<Object>} Created workflow
 */
export async function createWorkflow(workflow) {
  return fetchApi(BASE_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(workflow),
  });
}

/**
 * Update an existing workflow
 * @param {string} id - Workflow ID
 * @param {Object} workflow - Updated workflow data
 * @returns {Promise<Object>} Updated workflow
 */
export async function updateWorkflow(id, workflow) {
  return fetchApi(`${BASE_URL}/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(workflow),
  });
}

/**
 * Delete a workflow
 * @param {string} id - Workflow ID
 * @returns {Promise<Object>} Deletion result
 */
export async function deleteWorkflow(id) {
  return fetchApi(`${BASE_URL}/${id}`, {
    method: 'DELETE',
  });
}

/**
 * Duplicate a workflow
 * @param {string} id - Workflow ID to duplicate
 * @param {string} newName - Name for the duplicate
 * @returns {Promise<Object>} Duplicated workflow
 */
export async function duplicateWorkflow(id, newName) {
  return fetchApi(`${BASE_URL}/${id}/duplicate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: newName }),
  });
}

/**
 * Run a workflow immediately
 * @param {string} id - Workflow ID
 * @param {Object} options - Run options
 * @returns {Promise<Object>} Execution result
 */
export async function runWorkflow(id, options = {}) {
  return fetchApi(`${BASE_URL}/${id}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(options),
  });
}

/**
 * Test run a workflow (dry run)
 * @param {string} id - Workflow ID
 * @returns {Promise<Object>} Test result
 */
export async function testWorkflow(id) {
  return fetchApi(`${BASE_URL}/${id}/test`, {
    method: 'POST',
  });
}

/**
 * Get Celery task status
 * @param {string} taskId - Celery task ID
 * @returns {Promise<Object>} Task status
 */
export async function getTaskStatus(taskId) {
  return fetchApi(`${BASE_URL}/tasks/${taskId}`);
}

/**
 * Get workflow execution history
 * @param {string} id - Workflow ID
 * @param {Object} options - Pagination options
 * @returns {Promise<Object>} Execution history
 */
export async function getWorkflowExecutions(id, options = {}) {
  const params = new URLSearchParams();
  if (options.limit) params.append('limit', options.limit);
  if (options.offset) params.append('offset', options.offset);
  
  const queryString = params.toString();
  const url = queryString 
    ? `${BASE_URL}/${id}/executions?${queryString}` 
    : `${BASE_URL}/${id}/executions`;
  
  return fetchApi(url);
}

/**
 * Move workflow to a folder
 * @param {string} id - Workflow ID
 * @param {string} folderId - Target folder ID (null for root)
 * @returns {Promise<Object>} Updated workflow
 */
export async function moveWorkflow(id, folderId) {
  return fetchApi(`${BASE_URL}/${id}/move`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ folder_id: folderId }),
  });
}

/**
 * Update workflow tags
 * @param {string} id - Workflow ID
 * @param {string[]} tags - New tags array
 * @returns {Promise<Object>} Updated workflow
 */
export async function updateWorkflowTags(id, tags) {
  return fetchApi(`${BASE_URL}/${id}/tags`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tags }),
  });
}

// ============ Folders API ============

/**
 * Get all folders
 * @returns {Promise<Object>} List of folders
 */
export async function getFolders() {
  return fetchApi('/api/workflows/folders');
}

/**
 * Create a folder
 * @param {Object} folder - Folder data
 * @returns {Promise<Object>} Created folder
 */
export async function createFolder(folder) {
  return fetchApi('/api/workflows/folders', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(folder),
  });
}

/**
 * Update a folder
 * @param {string} id - Folder ID
 * @param {Object} folder - Updated folder data
 * @returns {Promise<Object>} Updated folder
 */
export async function updateFolder(id, folder) {
  return fetchApi(`/api/workflows/folders/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(folder),
  });
}

/**
 * Delete a folder
 * @param {string} id - Folder ID
 * @returns {Promise<Object>} Deletion result
 */
export async function deleteFolder(id) {
  return fetchApi(`/api/workflows/folders/${id}`, {
    method: 'DELETE',
  });
}

// ============ Tags API ============

/**
 * Get all tags
 * @returns {Promise<Object>} List of tags
 */
export async function getTags() {
  return fetchApi('/api/workflows/tags');
}

/**
 * Create a tag
 * @param {Object} tag - Tag data
 * @returns {Promise<Object>} Created tag
 */
export async function createTag(tag) {
  return fetchApi('/api/workflows/tags', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(tag),
  });
}

/**
 * Delete a tag
 * @param {string} id - Tag ID
 * @returns {Promise<Object>} Deletion result
 */
export async function deleteTag(id) {
  return fetchApi(`/api/workflows/tags/${id}`, {
    method: 'DELETE',
  });
}

// ============ Packages API ============

/**
 * Get enabled packages
 * @returns {Promise<Object>} List of enabled package IDs
 */
export async function getEnabledPackages() {
  return fetchApi('/api/workflows/packages');
}

/**
 * Enable a package
 * @param {string} packageId - Package ID
 * @returns {Promise<Object>} Result
 */
export async function enablePackage(packageId) {
  return fetchApi(`/api/workflows/packages/${packageId}/enable`, {
    method: 'PUT',
  });
}

/**
 * Disable a package
 * @param {string} packageId - Package ID
 * @returns {Promise<Object>} Result
 */
export async function disablePackage(packageId) {
  return fetchApi(`/api/workflows/packages/${packageId}/disable`, {
    method: 'PUT',
  });
}

export default {
  getWorkflows,
  getWorkflow,
  createWorkflow,
  updateWorkflow,
  deleteWorkflow,
  duplicateWorkflow,
  runWorkflow,
  testWorkflow,
  getWorkflowExecutions,
  moveWorkflow,
  updateWorkflowTags,
  getFolders,
  createFolder,
  updateFolder,
  deleteFolder,
  getTags,
  createTag,
  deleteTag,
  getEnabledPackages,
  enablePackage,
  disablePackage,
};
