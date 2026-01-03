/**
 * Scans API module.
 * 
 * Provides functions for interface scans and optical power data.
 */

import { apiClient, extractData, extractList } from './client';

const BASE_PATH = '/scans';

/**
 * Get interfaces for a device
 * @param {string} ipAddress - Device IP address
 * @returns {Promise<Array>} List of interfaces
 */
export async function getDeviceInterfaces(ipAddress) {
  const response = await apiClient.get(`${BASE_PATH}/interfaces/${ipAddress}`);
  return extractList(response);
}

/**
 * Get all optical interfaces
 * @param {string} ipAddress - Optional device filter
 * @returns {Promise<Array>} List of optical interfaces
 */
export async function getOpticalInterfaces(ipAddress = null) {
  const params = {};
  if (ipAddress) params.ip_address = ipAddress;
  
  const response = await apiClient.get(`${BASE_PATH}/optical`, params);
  return extractList(response);
}

/**
 * Get optical power history
 * @param {string} ipAddress - Device IP address
 * @param {Object} options - Options
 * @param {number} options.interfaceIndex - Interface index
 * @param {number} options.hours - Time window in hours
 * @returns {Promise<Array>} List of power readings
 */
export async function getOpticalPowerHistory(ipAddress, options = {}) {
  const params = { ip_address: ipAddress };
  if (options.interfaceIndex !== undefined) params.interface_index = options.interfaceIndex;
  if (options.hours) params.hours = options.hours;
  
  const response = await apiClient.get(`${BASE_PATH}/optical/power-history`, params);
  return extractList(response);
}

/**
 * Get optical power history for multiple devices
 * @param {Array<string>} ipAddresses - List of device IP addresses
 * @param {Object} options - Options
 * @param {number} options.interfaceIndex - Interface index
 * @param {number} options.hours - Time window in hours
 * @returns {Promise<Object>} Dictionary mapping IP to power readings
 */
export async function getOpticalPowerHistoryBulk(ipAddresses, options = {}) {
  const body = { ip_addresses: ipAddresses };
  if (options.interfaceIndex !== undefined) body.interface_index = options.interfaceIndex;
  if (options.hours) body.hours = options.hours;
  
  const response = await apiClient.post(`${BASE_PATH}/optical/power-history`, body);
  return extractData(response);
}

/**
 * Get optical power trends
 * @param {string} ipAddress - Device IP address
 * @param {number} interfaceIndex - Interface index
 * @param {number} days - Time window in days
 * @returns {Promise<Object>} Trend statistics
 */
export async function getOpticalPowerTrends(ipAddress, interfaceIndex, days = 7) {
  const params = {
    ip_address: ipAddress,
    interface_index: interfaceIndex,
    days,
  };
  
  const response = await apiClient.get(`${BASE_PATH}/optical/trends`, params);
  return extractData(response);
}

/**
 * Clean up old scan data
 * @param {number} opticalDays - Age threshold for optical data
 * @returns {Promise<Object>} Cleanup statistics
 */
export async function cleanupOldData(opticalDays = 90) {
  const response = await apiClient.post(`${BASE_PATH}/cleanup`, { optical_days: opticalDays });
  return extractData(response);
}

/**
 * Get scan progress
 * @returns {Promise<Object>} Scan progress status
 */
export async function getProgress() {
  const response = await apiClient.get('/progress');
  return response;
}

/**
 * Start a network scan
 * @returns {Promise<Object>} Scan start result
 */
export async function startScan() {
  const response = await apiClient.post('/scan');
  return response;
}

/**
 * Cancel running scan
 * @returns {Promise<Object>} Cancel result
 */
export async function cancelScan() {
  const response = await apiClient.post('/cancel_scan');
  return response;
}

export default {
  getDeviceInterfaces,
  getOpticalInterfaces,
  getOpticalPowerHistory,
  getOpticalPowerHistoryBulk,
  getOpticalPowerTrends,
  cleanupOldData,
  getProgress,
  startScan,
  cancelScan,
};
