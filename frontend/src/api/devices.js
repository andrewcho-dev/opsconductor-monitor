/**
 * Device API module.
 * 
 * Provides functions for device-related API operations.
 */

import { apiClient, extractData, extractList } from './client';

const BASE_PATH = '/devices';

/**
 * Get all devices with optional filtering
 * @param {Object} options - Filter options
 * @param {string} options.filterType - Filter type ('network', 'group', 'status')
 * @param {string} options.filterId - Filter value
 * @param {string} options.search - Search term
 * @returns {Promise<Array>} List of devices
 */
export async function getDevices(options = {}) {
  const params = {};
  if (options.filterType) params.filter_type = options.filterType;
  if (options.filterId) params.filter_id = options.filterId;
  if (options.search) params.search = options.search;
  
  const response = await apiClient.get(BASE_PATH, params);
  return extractList(response);
}

/**
 * Get a single device by IP address
 * @param {string} ipAddress - Device IP address
 * @param {Object} options - Options
 * @param {boolean} options.includeGroups - Include group memberships
 * @returns {Promise<Object>} Device record
 */
export async function getDevice(ipAddress, options = {}) {
  const params = {};
  if (options.includeGroups) params.include_groups = 'true';
  
  const response = await apiClient.get(`${BASE_PATH}/${ipAddress}`, params);
  return extractData(response);
}

/**
 * Create or update a device
 * @param {Object} device - Device data
 * @returns {Promise<Object>} Created/updated device
 */
export async function saveDevice(device) {
  const response = await apiClient.post(BASE_PATH, device);
  return extractData(response);
}

/**
 * Delete a device
 * @param {string} ipAddress - Device IP address
 * @returns {Promise<void>}
 */
export async function deleteDevice(ipAddress) {
  await apiClient.delete(`${BASE_PATH}/${ipAddress}`);
}

/**
 * Get network summary (devices grouped by network)
 * @returns {Promise<Array>} Network summaries
 */
export async function getNetworkSummary() {
  const response = await apiClient.get(`${BASE_PATH}/summary/networks`);
  return extractList(response);
}

/**
 * Get device statistics
 * @returns {Promise<Object>} Statistics
 */
export async function getDeviceStats() {
  const response = await apiClient.get(`${BASE_PATH}/summary/stats`);
  return extractData(response);
}

/**
 * Get groups for a device
 * @param {string} ipAddress - Device IP address
 * @returns {Promise<Array>} List of groups
 */
export async function getDeviceGroups(ipAddress) {
  const response = await apiClient.get(`${BASE_PATH}/${ipAddress}/groups`);
  return extractList(response);
}

export default {
  getDevices,
  getDevice,
  saveDevice,
  deleteDevice,
  getNetworkSummary,
  getDeviceStats,
  getDeviceGroups,
};
