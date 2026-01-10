/**
 * Credentials API Service - OpenAPI 3.x
 * 
 * Endpoints: /credentials/v1/*
 * - Credential vault
 * - Credential groups
 * - Audit logging
 * - Enterprise auth
 */

import { apiClient, API_DOMAINS } from '../client';

const BASE = API_DOMAINS.CREDENTIALS;

/**
 * Credentials
 */
export const credentials = {
  list: (params = {}) => 
    apiClient.get(`${BASE}/credentials`, params),
  
  get: (credentialId) => 
    apiClient.get(`${BASE}/credentials/${credentialId}`),
  
  create: (credentialData) => 
    apiClient.post(`${BASE}/credentials`, credentialData),
  
  update: (credentialId, credentialData) => 
    apiClient.put(`${BASE}/credentials/${credentialId}`, credentialData),
  
  delete: (credentialId) => 
    apiClient.delete(`${BASE}/credentials/${credentialId}`),
  
  test: (credentialId, deviceId) => 
    apiClient.post(`${BASE}/credentials/${credentialId}/test`, { device_id: deviceId }),
  
  getStatistics: () => 
    apiClient.get(`${BASE}/credentials/statistics`),
  
  getTypes: () => 
    apiClient.get(`${BASE}/credentials/types`),
};

/**
 * Credential Groups
 */
export const groups = {
  list: () => 
    apiClient.get(`${BASE}/credentials/groups`),
  
  get: (groupId) => 
    apiClient.get(`${BASE}/credentials/groups/${groupId}`),
  
  create: (groupData) => 
    apiClient.post(`${BASE}/credentials/groups`, groupData),
  
  update: (groupId, groupData) => 
    apiClient.put(`${BASE}/credentials/groups/${groupId}`, groupData),
  
  delete: (groupId) => 
    apiClient.delete(`${BASE}/credentials/groups/${groupId}`),
};

/**
 * Audit
 */
export const audit = {
  list: (params = {}) => 
    apiClient.get(`${BASE}/credentials/audit`, params),
  
  getForCredential: (credentialId, params = {}) => 
    apiClient.get(`${BASE}/credentials/${credentialId}/audit`, params),
};

/**
 * Device Assignments
 */
export const assignments = {
  list: (credentialId) => 
    apiClient.get(`${BASE}/credentials/${credentialId}/devices`),
  
  assign: (credentialId, deviceIds) => 
    apiClient.post(`${BASE}/credentials/${credentialId}/devices`, { device_ids: deviceIds }),
  
  unassign: (credentialId, deviceIds) => 
    apiClient.delete(`${BASE}/credentials/${credentialId}/devices`, { device_ids: deviceIds }),
};

/**
 * Enterprise Auth
 */
export const enterprise = {
  listConfigs: () => 
    apiClient.get(`${BASE}/credentials/enterprise/configs`),
  
  getConfig: (configId) => 
    apiClient.get(`${BASE}/credentials/enterprise/configs/${configId}`),
  
  createConfig: (configData) => 
    apiClient.post(`${BASE}/credentials/enterprise/configs`, configData),
  
  updateConfig: (configId, configData) => 
    apiClient.put(`${BASE}/credentials/enterprise/configs/${configId}`, configData),
  
  deleteConfig: (configId) => 
    apiClient.delete(`${BASE}/credentials/enterprise/configs/${configId}`),
  
  testConfig: (configId) => 
    apiClient.post(`${BASE}/credentials/enterprise/configs/${configId}/test`),
  
  listUsers: (params = {}) => 
    apiClient.get(`${BASE}/credentials/enterprise/users`, params),
};

export default {
  credentials,
  groups,
  audit,
  assignments,
  enterprise,
};
