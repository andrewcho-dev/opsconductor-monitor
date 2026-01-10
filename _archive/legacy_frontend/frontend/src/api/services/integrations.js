/**
 * Integrations API Service - OpenAPI 3.x
 * 
 * Endpoints: /integrations/v1/*
 * - NetBox integration
 * - PRTG integration
 * - Ciena MCP integration
 */

import { apiClient, API_DOMAINS } from '../client';

const BASE = API_DOMAINS.INTEGRATIONS;

/**
 * Integration Management
 */
export const integrations = {
  list: (params = {}) => 
    apiClient.get(`${BASE}/list`, params),
  
  get: (integrationId) => 
    apiClient.get(`${BASE}/${integrationId}`),
  
  create: (integrationData) => 
    apiClient.post(`${BASE}`, integrationData),
  
  update: (integrationId, integrationData) => 
    apiClient.put(`${BASE}/${integrationId}`, integrationData),
  
  delete: (integrationId) => 
    apiClient.delete(`${BASE}/${integrationId}`),
};

/**
 * NetBox
 */
export const netbox = {
  getSettings: () => 
    apiClient.get(`${BASE}/netbox/settings`),
  
  updateSettings: (settings) => 
    apiClient.put(`${BASE}/netbox/settings`, settings),
  
  testConnection: (config) => 
    apiClient.post(`${BASE}/netbox/test`, config),
  
  getStatus: () => 
    apiClient.get(`${BASE}/netbox/status`),
  
  sync: (integrationId) => 
    apiClient.post(`${BASE}/netbox/sync`, { integration_id: integrationId }),
  
  getDevices: (params = {}) => 
    apiClient.get(`${BASE}/netbox/devices`, params),
  
  getSites: (params = {}) => 
    apiClient.get(`${BASE}/netbox/sites`, params),
  
  getInterfaces: (deviceId) => 
    apiClient.get(`${BASE}/netbox/devices/${deviceId}/interfaces`),
  
  getIpAddresses: (params = {}) => 
    apiClient.get(`${BASE}/netbox/ip-addresses`, params),
  
  getPrefixes: (params = {}) => 
    apiClient.get(`${BASE}/netbox/prefixes`, params),
};

/**
 * PRTG
 */
export const prtg = {
  getSettings: () => 
    apiClient.get(`${BASE}/prtg/settings`),
  
  updateSettings: (settings) => 
    apiClient.put(`${BASE}/prtg/settings`, settings),
  
  testConnection: (config) => 
    apiClient.post(`${BASE}/prtg/test`, config),
  
  getStatus: () => 
    apiClient.get(`${BASE}/prtg/status`),
  
  syncPreview: (config) => 
    apiClient.post(`${BASE}/prtg/sync/preview`, config),
  
  getDevices: (params = {}) => 
    apiClient.get(`${BASE}/prtg/devices`, params),
  
  getSensors: (deviceId) => 
    apiClient.get(`${BASE}/prtg/devices/${deviceId}/sensors`),
};

/**
 * Ciena MCP
 */
export const mcp = {
  getSettings: () => 
    apiClient.get(`${BASE}/mcp/settings`),
  
  updateSettings: (settings) => 
    apiClient.put(`${BASE}/mcp/settings`, settings),
  
  testConnection: (config) => 
    apiClient.post(`${BASE}/mcp/test`, config),
  
  getServices: () => 
    apiClient.get(`${BASE}/mcp/services`),
  
  getServicesSummary: () => 
    apiClient.get(`${BASE}/mcp/services/summary`),
  
  getServicesRings: () => 
    apiClient.get(`${BASE}/mcp/services/rings`),
  
  getDevices: () => 
    apiClient.get(`${BASE}/mcp/devices`),
  
  syncEquipment: (config) => 
    apiClient.post(`${BASE}/mcp/sync/equipment`, config),
  
  syncToNetBox: (config) => 
    apiClient.post(`${BASE}/mcp/sync/netbox`, config),
};

export default {
  integrations,
  netbox,
  prtg,
  mcp,
};
