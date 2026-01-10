/**
 * Groups API module.
 * 
 * Provides functions for device group operations.
 */

import { apiClient, extractData, extractList } from './client';

const BASE_PATH = '/device_groups';

/**
 * Get all device groups
 * @returns {Promise<Array>} List of groups with device counts
 */
export async function getGroups() {
  const response = await apiClient.get(BASE_PATH);
  return extractList(response);
}

/**
 * Get a single group by ID
 * @param {number} groupId - Group ID
 * @param {Object} options - Options
 * @param {boolean} options.includeDevices - Include device list
 * @returns {Promise<Object>} Group record
 */
export async function getGroup(groupId, options = {}) {
  const params = {};
  if (options.includeDevices) params.include_devices = 'true';
  
  const response = await apiClient.get(`${BASE_PATH}/${groupId}`, params);
  return extractData(response);
}

/**
 * Create a new group
 * @param {Object} group - Group data
 * @param {string} group.group_name - Group name
 * @param {string} group.description - Optional description
 * @returns {Promise<Object>} Created group
 */
export async function createGroup(group) {
  const response = await apiClient.post(BASE_PATH, group);
  return extractData(response);
}

/**
 * Update a group
 * @param {number} groupId - Group ID
 * @param {Object} updates - Update data
 * @returns {Promise<Object>} Updated group
 */
export async function updateGroup(groupId, updates) {
  const response = await apiClient.put(`${BASE_PATH}/${groupId}`, updates);
  return extractData(response);
}

/**
 * Delete a group
 * @param {number} groupId - Group ID
 * @returns {Promise<void>}
 */
export async function deleteGroup(groupId) {
  await apiClient.delete(`${BASE_PATH}/${groupId}`);
}

/**
 * Get devices in a group
 * @param {number} groupId - Group ID
 * @returns {Promise<Array>} List of devices
 */
export async function getGroupDevices(groupId) {
  const response = await apiClient.get(`${BASE_PATH}/${groupId}/devices`);
  return extractList(response);
}

/**
 * Add a device to a group
 * @param {number} groupId - Group ID
 * @param {string} ipAddress - Device IP address
 * @returns {Promise<void>}
 */
export async function addDeviceToGroup(groupId, ipAddress) {
  await apiClient.post(`${BASE_PATH}/${groupId}/devices`, { ip_address: ipAddress });
}

/**
 * Add multiple devices to a group
 * @param {number} groupId - Group ID
 * @param {Array<string>} ipAddresses - List of device IP addresses
 * @returns {Promise<Object>} Result with added count
 */
export async function addDevicesToGroup(groupId, ipAddresses) {
  const response = await apiClient.post(`${BASE_PATH}/${groupId}/devices`, { ip_addresses: ipAddresses });
  return extractData(response);
}

/**
 * Remove a device from a group
 * @param {number} groupId - Group ID
 * @param {string} ipAddress - Device IP address
 * @returns {Promise<void>}
 */
export async function removeDeviceFromGroup(groupId, ipAddress) {
  await apiClient.delete(`${BASE_PATH}/${groupId}/devices/${ipAddress}`);
}

export default {
  getGroups,
  getGroup,
  createGroup,
  updateGroup,
  deleteGroup,
  getGroupDevices,
  addDeviceToGroup,
  addDevicesToGroup,
  removeDeviceFromGroup,
};
