/**
 * Scheduler API module.
 * 
 * Provides functions for scheduler job and execution operations.
 */

import { apiClient, extractData, extractList } from './client';

const BASE_PATH = '/scheduler';

/**
 * Get all scheduler jobs
 * @param {Object} options - Filter options
 * @param {boolean} options.enabled - Filter by enabled status
 * @returns {Promise<Array>} List of scheduler jobs
 */
export async function getSchedulerJobs(options = {}) {
  const params = {};
  if (options.enabled !== undefined) params.enabled = options.enabled.toString();
  
  const response = await apiClient.get(`${BASE_PATH}/jobs`, params);
  return extractList(response);
}

/**
 * Get a single scheduler job by name
 * @param {string} name - Job name
 * @param {Object} options - Options
 * @param {boolean} options.includeExecutions - Include recent executions
 * @param {number} options.executionLimit - Max executions to include
 * @returns {Promise<Object>} Scheduler job
 */
export async function getSchedulerJob(name, options = {}) {
  const params = {};
  if (options.includeExecutions) params.include_executions = 'true';
  if (options.executionLimit) params.execution_limit = options.executionLimit;
  
  const response = await apiClient.get(`${BASE_PATH}/jobs/${encodeURIComponent(name)}`, params);
  return extractData(response);
}

/**
 * Create or update a scheduler job
 * @param {Object} job - Scheduler job data
 * @returns {Promise<Object>} Created/updated job
 */
export async function saveSchedulerJob(job) {
  const response = await apiClient.post(`${BASE_PATH}/jobs`, job);
  return extractData(response);
}

/**
 * Delete a scheduler job
 * @param {string} name - Job name
 * @returns {Promise<void>}
 */
export async function deleteSchedulerJob(name) {
  await apiClient.delete(`${BASE_PATH}/jobs/${encodeURIComponent(name)}`);
}

/**
 * Enable a scheduler job
 * @param {string} name - Job name
 * @returns {Promise<Object>} Updated job
 */
export async function enableSchedulerJob(name) {
  const response = await apiClient.post(`${BASE_PATH}/jobs/${encodeURIComponent(name)}/enable`);
  return extractData(response);
}

/**
 * Disable a scheduler job
 * @param {string} name - Job name
 * @returns {Promise<Object>} Updated job
 */
export async function disableSchedulerJob(name) {
  const response = await apiClient.post(`${BASE_PATH}/jobs/${encodeURIComponent(name)}/disable`);
  return extractData(response);
}

/**
 * Trigger a one-off run of a scheduler job
 * @param {string} name - Job name
 * @returns {Promise<Object>} Task info
 */
export async function runSchedulerJobOnce(name) {
  const response = await apiClient.post(`${BASE_PATH}/jobs/${encodeURIComponent(name)}/run-once`);
  return extractData(response);
}

/**
 * Get executions for a scheduler job
 * @param {string} name - Job name
 * @param {Object} options - Filter options
 * @param {number} options.limit - Max results
 * @param {string} options.status - Filter by status
 * @returns {Promise<Array>} List of executions
 */
export async function getJobExecutions(name, options = {}) {
  const params = {};
  if (options.limit) params.limit = options.limit;
  if (options.status) params.status = options.status;
  
  const response = await apiClient.get(`${BASE_PATH}/jobs/${encodeURIComponent(name)}/executions`, params);
  return extractList(response);
}

/**
 * Clear executions for a scheduler job
 * @param {string} name - Job name
 * @param {Object} options - Filter options
 * @param {string} options.status - Filter by status
 * @returns {Promise<Object>} Result with deleted count
 */
export async function clearJobExecutions(name, options = {}) {
  const response = await apiClient.post(`${BASE_PATH}/jobs/${encodeURIComponent(name)}/executions/clear`, options);
  return extractData(response);
}

/**
 * Get recent executions across all jobs
 * @param {Object} options - Filter options
 * @param {number} options.limit - Max results
 * @param {string} options.status - Filter by status
 * @returns {Promise<Array>} List of executions
 */
export async function getRecentExecutions(options = {}) {
  const params = {};
  if (options.limit) params.limit = options.limit;
  if (options.status) params.status = options.status;
  
  const response = await apiClient.get(`${BASE_PATH}/executions/recent`, params);
  return extractList(response);
}

/**
 * Get execution statistics
 * @param {Object} options - Filter options
 * @param {string} options.jobName - Filter by job name
 * @param {number} options.hours - Time window in hours
 * @returns {Promise<Object>} Statistics
 */
export async function getExecutionStats(options = {}) {
  const params = {};
  if (options.jobName) params.job_name = options.jobName;
  if (options.hours) params.hours = options.hours;
  
  const response = await apiClient.get(`${BASE_PATH}/executions/stats`, params);
  return extractData(response);
}

/**
 * Mark stale executions as timed out
 * @param {number} timeoutSeconds - Timeout threshold
 * @returns {Promise<Object>} Result with marked count
 */
export async function markStaleExecutions(timeoutSeconds = 600) {
  const response = await apiClient.post(`${BASE_PATH}/executions/stale`, { timeout_seconds: timeoutSeconds });
  return extractData(response);
}

export default {
  getSchedulerJobs,
  getSchedulerJob,
  saveSchedulerJob,
  deleteSchedulerJob,
  enableSchedulerJob,
  disableSchedulerJob,
  runSchedulerJobOnce,
  getJobExecutions,
  clearJobExecutions,
  getRecentExecutions,
  getExecutionStats,
  markStaleExecutions,
};
