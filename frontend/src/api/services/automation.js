/**
 * Automation API Service - OpenAPI 3.x
 * 
 * Endpoints: /automation/v1/*
 * - Workflow management
 * - Job execution
 * - Scheduling
 */

import { apiClient, API_DOMAINS } from '../client';

const BASE = API_DOMAINS.AUTOMATION;

/**
 * Workflows
 */
export const workflows = {
  list: (params = {}) => 
    apiClient.get(`${BASE}/workflows`, params),
  
  get: (workflowId) => 
    apiClient.get(`${BASE}/workflows/${workflowId}`),
  
  create: (workflowData) => 
    apiClient.post(`${BASE}/workflows`, workflowData),
  
  update: (workflowId, workflowData) => 
    apiClient.put(`${BASE}/workflows/${workflowId}`, workflowData),
  
  delete: (workflowId) => 
    apiClient.delete(`${BASE}/workflows/${workflowId}`),
  
  execute: (workflowId, params = {}) => 
    apiClient.post(`${BASE}/workflows/${workflowId}/execute`, params),
  
  getVersions: (workflowId) => 
    apiClient.get(`${BASE}/workflows/${workflowId}/versions`),
  
  duplicate: (workflowId) => 
    apiClient.post(`${BASE}/workflows/${workflowId}/duplicate`),
};

/**
 * Jobs (Executions)
 */
export const jobs = {
  list: (params = {}) => 
    apiClient.get(`${BASE}/jobs`, params),
  
  get: (jobId) => 
    apiClient.get(`${BASE}/jobs/${jobId}`),
  
  cancel: (jobId) => 
    apiClient.post(`${BASE}/jobs/${jobId}/cancel`),
  
  retry: (jobId) => 
    apiClient.post(`${BASE}/jobs/${jobId}/retry`),
  
  getLogs: (jobId) => 
    apiClient.get(`${BASE}/jobs/${jobId}/logs`),
  
  getStatistics: (params = {}) => 
    apiClient.get(`${BASE}/jobs/statistics`, params),
  
  getActive: () => 
    apiClient.get(`${BASE}/jobs/active`),
  
  getHistory: (params = {}) => 
    apiClient.get(`${BASE}/jobs/history`, params),
};

/**
 * Schedules
 */
export const schedules = {
  list: (params = {}) => 
    apiClient.get(`${BASE}/schedules`, params),
  
  get: (scheduleId) => 
    apiClient.get(`${BASE}/schedules/${scheduleId}`),
  
  create: (scheduleData) => 
    apiClient.post(`${BASE}/schedules`, scheduleData),
  
  update: (scheduleId, scheduleData) => 
    apiClient.put(`${BASE}/schedules/${scheduleId}`, scheduleData),
  
  delete: (scheduleId) => 
    apiClient.delete(`${BASE}/schedules/${scheduleId}`),
  
  enable: (scheduleId) => 
    apiClient.post(`${BASE}/schedules/${scheduleId}/enable`),
  
  disable: (scheduleId) => 
    apiClient.post(`${BASE}/schedules/${scheduleId}/disable`),
  
  trigger: (scheduleId) => 
    apiClient.post(`${BASE}/schedules/${scheduleId}/trigger`),
};

/**
 * Folders (Workflow Organization)
 */
export const folders = {
  list: () => 
    apiClient.get(`${BASE}/folders`),
  
  get: (folderId) => 
    apiClient.get(`${BASE}/folders/${folderId}`),
  
  create: (folderData) => 
    apiClient.post(`${BASE}/folders`, folderData),
  
  update: (folderId, folderData) => 
    apiClient.put(`${BASE}/folders/${folderId}`, folderData),
  
  delete: (folderId) => 
    apiClient.delete(`${BASE}/folders/${folderId}`),
};

/**
 * Tags
 */
export const tags = {
  list: () => 
    apiClient.get(`${BASE}/tags`),
  
  create: (tagData) => 
    apiClient.post(`${BASE}/tags`, tagData),
  
  delete: (tagId) => 
    apiClient.delete(`${BASE}/tags/${tagId}`),
};

export default {
  workflows,
  jobs,
  schedules,
  folders,
  tags,
};
