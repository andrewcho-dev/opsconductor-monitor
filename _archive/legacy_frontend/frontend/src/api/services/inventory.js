/**
 * Inventory API Service - OpenAPI 3.x
 * 
 * Endpoints: /inventory/v1/*
 * - Device management
 * - Interface management
 * - Network topology
 * - Sites, racks, modules
 */

import { apiClient, API_DOMAINS } from '../client';

const BASE = API_DOMAINS.INVENTORY;

/**
 * Device Management
 */
export const devices = {
  list: (params = {}) => 
    apiClient.get(`${BASE}/devices`, params),
  
  get: (deviceId) => 
    apiClient.get(`${BASE}/devices/${deviceId}`),
  
  create: (deviceData) => 
    apiClient.post(`${BASE}/devices`, deviceData),
  
  update: (deviceId, deviceData) => 
    apiClient.put(`${BASE}/devices/${deviceId}`, deviceData),
  
  delete: (deviceId) => 
    apiClient.delete(`${BASE}/devices/${deviceId}`),
  
  getInterfaces: (deviceId) => 
    apiClient.get(`${BASE}/devices/${deviceId}/interfaces`),
  
  getMetrics: (deviceId, params = {}) => 
    apiClient.get(`${BASE}/devices/${deviceId}/metrics`, params),
};

/**
 * Interface Management
 */
export const interfaces = {
  list: (params = {}) => 
    apiClient.get(`${BASE}/interfaces`, params),
  
  get: (interfaceId) => 
    apiClient.get(`${BASE}/interfaces/${interfaceId}`),
  
  getStatus: (interfaceId) => 
    apiClient.get(`${BASE}/interfaces/${interfaceId}/status`),
};

/**
 * Network Topology
 */
export const topology = {
  get: (params = {}) => 
    apiClient.get(`${BASE}/topology`, params),
  
  getLinks: (params = {}) => 
    apiClient.get(`${BASE}/topology/links`, params),
  
  getNodes: (params = {}) => 
    apiClient.get(`${BASE}/topology/nodes`, params),
};

/**
 * Sites
 */
export const sites = {
  list: (params = {}) => 
    apiClient.get(`${BASE}/sites`, params),
  
  get: (siteId) => 
    apiClient.get(`${BASE}/sites/${siteId}`),
  
  getDevices: (siteId, params = {}) => 
    apiClient.get(`${BASE}/sites/${siteId}/devices`, params),
};

/**
 * Racks
 */
export const racks = {
  list: (params = {}) => 
    apiClient.get(`${BASE}/racks`, params),
  
  get: (rackId) => 
    apiClient.get(`${BASE}/racks/${rackId}`),
  
  getDevices: (rackId) => 
    apiClient.get(`${BASE}/racks/${rackId}/devices`),
};

/**
 * Modules
 */
export const modules = {
  list: (params = {}) => 
    apiClient.get(`${BASE}/modules`, params),
  
  get: (moduleId) => 
    apiClient.get(`${BASE}/modules/${moduleId}`),
};

/**
 * Device Groups
 */
export const groups = {
  list: (params = {}) => 
    apiClient.get(`${BASE}/groups`, params),
  
  get: (groupId) => 
    apiClient.get(`${BASE}/groups/${groupId}`),
  
  create: (groupData) => 
    apiClient.post(`${BASE}/groups`, groupData),
  
  update: (groupId, groupData) => 
    apiClient.put(`${BASE}/groups/${groupId}`, groupData),
  
  delete: (groupId) => 
    apiClient.delete(`${BASE}/groups/${groupId}`),
  
  getDevices: (groupId) => 
    apiClient.get(`${BASE}/groups/${groupId}/devices`),
  
  addDevices: (groupId, deviceIds) => 
    apiClient.post(`${BASE}/groups/${groupId}/devices`, { device_ids: deviceIds }),
  
  removeDevices: (groupId, deviceIds) => 
    apiClient.delete(`${BASE}/groups/${groupId}/devices`, { device_ids: deviceIds }),
};

export default {
  devices,
  interfaces,
  topology,
  sites,
  racks,
  modules,
  groups,
};
