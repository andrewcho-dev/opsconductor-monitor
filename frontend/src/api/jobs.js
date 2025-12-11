/**
 * Jobs API module.
 * 
 * Provides functions for job definition operations.
 */

import { apiClient, extractData, extractList } from './client';

const BASE_PATH = '/job-definitions';

/**
 * Get all job definitions
 * @param {Object} options - Filter options
 * @param {boolean} options.enabled - Filter by enabled status
 * @param {string} options.search - Search term
 * @returns {Promise<Array>} List of job definitions
 */
export async function getJobs(options = {}) {
  const params = {};
  if (options.enabled !== undefined) params.enabled = options.enabled.toString();
  if (options.search) params.search = options.search;
  
  const response = await apiClient.get(BASE_PATH, params);
  return extractList(response);
}

/**
 * Get a single job definition by ID
 * @param {string} jobId - Job definition UUID
 * @returns {Promise<Object>} Job definition
 */
export async function getJob(jobId) {
  const response = await apiClient.get(`${BASE_PATH}/${jobId}`);
  return extractData(response);
}

/**
 * Create a new job definition
 * @param {Object} job - Job definition data
 * @returns {Promise<Object>} Created job definition
 */
export async function createJob(job) {
  const response = await apiClient.post(BASE_PATH, job);
  return extractData(response);
}

/**
 * Update a job definition
 * @param {string} jobId - Job definition UUID
 * @param {Object} updates - Update data
 * @returns {Promise<Object>} Updated job definition
 */
export async function updateJob(jobId, updates) {
  const response = await apiClient.put(`${BASE_PATH}/${jobId}`, updates);
  return extractData(response);
}

/**
 * Delete a job definition
 * @param {string} jobId - Job definition UUID
 * @returns {Promise<void>}
 */
export async function deleteJob(jobId) {
  await apiClient.delete(`${BASE_PATH}/${jobId}`);
}

/**
 * Enable a job definition
 * @param {string} jobId - Job definition UUID
 * @returns {Promise<Object>} Updated job definition
 */
export async function enableJob(jobId) {
  const response = await apiClient.post(`${BASE_PATH}/${jobId}/enable`);
  return extractData(response);
}

/**
 * Disable a job definition
 * @param {string} jobId - Job definition UUID
 * @returns {Promise<Object>} Updated job definition
 */
export async function disableJob(jobId) {
  const response = await apiClient.post(`${BASE_PATH}/${jobId}/disable`);
  return extractData(response);
}

export default {
  getJobs,
  getJob,
  createJob,
  updateJob,
  deleteJob,
  enableJob,
  disableJob,
};
