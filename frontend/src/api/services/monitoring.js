/**
 * Monitoring API Service - OpenAPI 3.x
 * 
 * Endpoints: /monitoring/v1/*
 * - Alerts management
 * - Metrics collection
 * - SNMP polling
 * - Telemetry
 */

import { apiClient, API_DOMAINS } from '../client';

const BASE = API_DOMAINS.MONITORING;

/**
 * Alerts
 */
export const alerts = {
  list: (params = {}) => 
    apiClient.get(`${BASE}/alerts`, params),
  
  get: (alertId) => 
    apiClient.get(`${BASE}/alerts/${alertId}`),
  
  acknowledge: (alertId) => 
    apiClient.post(`${BASE}/alerts/${alertId}/acknowledge`),
  
  resolve: (alertId) => 
    apiClient.post(`${BASE}/alerts/${alertId}/resolve`),
  
  getStats: () => 
    apiClient.get(`${BASE}/alerts/stats`),
  
  getSeverities: () => 
    apiClient.get(`${BASE}/alerts/severities`),
};

/**
 * Metrics
 */
export const metrics = {
  getOptical: (deviceId, params = {}) => 
    apiClient.get(`${BASE}/metrics/optical/${deviceId}`, params),
  
  getInterface: (deviceId, params = {}) => 
    apiClient.get(`${BASE}/metrics/interface/${deviceId}`, params),
  
  getAvailability: (deviceId, params = {}) => 
    apiClient.get(`${BASE}/metrics/availability/${deviceId}`, params),
  
  getPower: (deviceId, params = {}) => 
    apiClient.get(`${BASE}/metrics/power/${deviceId}`, params),
  
  getHistory: (deviceId, metricType, params = {}) => 
    apiClient.get(`${BASE}/metrics/${deviceId}/${metricType}/history`, params),
};

/**
 * Polling
 */
export const polling = {
  getStatus: () => 
    apiClient.get(`${BASE}/polling/status`),
  
  getConfigs: () => 
    apiClient.get(`${BASE}/polling/configs`),
  
  createConfig: (configData) => 
    apiClient.post(`${BASE}/polling/configs`, configData),
  
  updateConfig: (configId, configData) => 
    apiClient.put(`${BASE}/polling/configs/${configId}`, configData),
  
  deleteConfig: (configId) => 
    apiClient.delete(`${BASE}/polling/configs/${configId}`),
  
  trigger: (configId) => 
    apiClient.post(`${BASE}/polling/configs/${configId}/trigger`),
  
  getLogs: (params = {}) => 
    apiClient.get(`${BASE}/polling/logs`, params),
  
  clearLogs: () => 
    apiClient.delete(`${BASE}/polling/logs`),
  
  getStatistics: () => 
    apiClient.get(`${BASE}/polling/statistics`),
};

/**
 * SNMP
 */
export const snmp = {
  poll: (deviceId, params = {}) => 
    apiClient.post(`${BASE}/snmp/poll/${deviceId}`, params),
  
  walk: (deviceId, oid, params = {}) => 
    apiClient.get(`${BASE}/snmp/walk/${deviceId}/${oid}`, params),
  
  get: (deviceId, oids) => 
    apiClient.post(`${BASE}/snmp/get/${deviceId}`, { oids }),
  
  getProfiles: () => 
    apiClient.get(`${BASE}/snmp/profiles`),
  
  getMibMappings: (params = {}) => 
    apiClient.get(`${BASE}/snmp/mib-mappings`, params),
  
  getAlarms: (deviceId) => 
    apiClient.get(`${BASE}/snmp/alarms/${deviceId}`),
};

/**
 * Telemetry
 */
export const telemetry = {
  getStatus: () => 
    apiClient.get(`${BASE}/telemetry/status`),
  
  getStream: (deviceId) => 
    apiClient.get(`${BASE}/telemetry/stream/${deviceId}`),
};

/**
 * Traps
 */
export const traps = {
  list: (params = {}) => 
    apiClient.get(`${BASE}/traps`, params),
  
  get: (trapId) => 
    apiClient.get(`${BASE}/traps/${trapId}`),
  
  acknowledge: (trapId) => 
    apiClient.post(`${BASE}/traps/${trapId}/acknowledge`),
};

export default {
  alerts,
  metrics,
  polling,
  snmp,
  telemetry,
  traps,
};
