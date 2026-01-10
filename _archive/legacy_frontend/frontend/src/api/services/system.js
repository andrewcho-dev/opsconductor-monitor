/**
 * System API Service - OpenAPI 3.x
 * 
 * Endpoints: /system/v1/*
 * - Health checks
 * - System settings
 * - Logging
 * - Cache management
 */

import { apiClient, API_DOMAINS } from '../client';

const BASE = API_DOMAINS.SYSTEM;

/**
 * Health
 */
export const health = {
  check: () => 
    apiClient.get(`${BASE}/health`),
  
  getServices: () => 
    apiClient.get(`${BASE}/health/services`),
};

/**
 * System Info
 */
export const info = {
  get: () => 
    apiClient.get(`${BASE}/info`),
  
  getVersion: () => 
    apiClient.get(`${BASE}/info/version`),
  
  getUsageStats: (params = {}) => 
    apiClient.get(`${BASE}/usage/stats`, params),
};

/**
 * Settings
 */
export const settings = {
  get: () => 
    apiClient.get(`${BASE}/settings`),
  
  update: (category, key, value) => 
    apiClient.put(`${BASE}/settings`, { category, key, value }),
  
  getDatabase: () => 
    apiClient.get(`${BASE}/settings/database`),
  
  testDatabase: (config) => 
    apiClient.post(`${BASE}/settings/database/test`, config),
};

/**
 * Logging
 */
export const logs = {
  list: (params = {}) => 
    apiClient.get(`${BASE}/logs`, params),
  
  getStats: (params = {}) => 
    apiClient.get(`${BASE}/logs/stats`, params),
  
  getSources: () => 
    apiClient.get(`${BASE}/logs/sources`),
  
  getLevels: () => 
    apiClient.get(`${BASE}/logs/levels`),
  
  cleanup: (params) => 
    apiClient.post(`${BASE}/logs/cleanup`, params),
  
  getSettings: () => 
    apiClient.get(`${BASE}/logging/settings`),
  
  updateSettings: (settings) => 
    apiClient.put(`${BASE}/logging/settings`, settings),
};

/**
 * Cache
 */
export const cache = {
  clear: (cacheType = 'all') => 
    apiClient.delete(`${BASE}/cache`, { cache_type: cacheType }),
  
  getStatus: () => 
    apiClient.get(`${BASE}/cache/status`),
};

export default {
  health,
  info,
  settings,
  logs,
  cache,
};
