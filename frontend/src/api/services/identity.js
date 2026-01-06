/**
 * Identity API Service - OpenAPI 3.x
 * 
 * Endpoints: /identity/v1/* and /auth/*
 * - Authentication (login/logout)
 * - User management
 * - Role management
 * - Password policies
 */

import { apiClient, API_DOMAINS } from '../client';

const BASE = API_DOMAINS.IDENTITY;
const AUTH = API_DOMAINS.AUTH;

/**
 * Authentication
 */
export const auth = {
  login: (username, password, configId = null) => 
    apiClient.post(`${AUTH}/login`, { username, password, config_id: configId }),
  
  logout: () => 
    apiClient.post(`${AUTH}/logout`),
  
  refresh: () => 
    apiClient.post(`${AUTH}/refresh`),
  
  getCurrentUser: () => 
    apiClient.get(`${BASE}/users/me`),
};

/**
 * User Management
 */
export const users = {
  list: (params = {}) => 
    apiClient.get(`${BASE}/users`, params),
  
  get: (userId) => 
    apiClient.get(`${BASE}/users/${userId}`),
  
  create: (userData) => 
    apiClient.post(`${BASE}/users`, userData),
  
  update: (userId, userData) => 
    apiClient.put(`${BASE}/users/${userId}`, userData),
  
  delete: (userId) => 
    apiClient.delete(`${BASE}/users/${userId}`),
  
  resetPassword: (userId, newPassword) => 
    apiClient.post(`${BASE}/users/${userId}/password`, { new_password: newPassword }),
};

/**
 * Role Management
 */
export const roles = {
  list: (params = {}) => 
    apiClient.get(`${BASE}/roles`, params),
  
  get: (roleId) => 
    apiClient.get(`${BASE}/roles/${roleId}`),
  
  getMembers: (roleId) => 
    apiClient.get(`${BASE}/roles/${roleId}/members`),
  
  create: (roleData) => 
    apiClient.post(`${BASE}/roles`, roleData),
  
  update: (roleId, roleData) => 
    apiClient.put(`${BASE}/roles/${roleId}`, roleData),
  
  delete: (roleId) => 
    apiClient.delete(`${BASE}/roles/${roleId}`),
};

/**
 * Password Policy
 */
export const passwordPolicy = {
  get: () => 
    apiClient.get(`${BASE}/password-policy`),
  
  update: (policyData) => 
    apiClient.put(`${BASE}/password-policy`, policyData),
};

/**
 * Enterprise Authentication
 */
export const enterprise = {
  listConfigs: () => 
    apiClient.get(`${BASE}/enterprise/configs`),
  
  getConfig: (configId) => 
    apiClient.get(`${BASE}/enterprise/configs/${configId}`),
  
  createConfig: (configData) => 
    apiClient.post(`${BASE}/enterprise/configs`, configData),
  
  updateConfig: (configId, configData) => 
    apiClient.put(`${BASE}/enterprise/configs/${configId}`, configData),
  
  deleteConfig: (configId) => 
    apiClient.delete(`${BASE}/enterprise/configs/${configId}`),
  
  testConfig: (configId) => 
    apiClient.post(`${BASE}/enterprise/configs/${configId}/test`),
  
  listUsers: (params = {}) => 
    apiClient.get(`${BASE}/enterprise/users`, params),
};

export default {
  auth,
  users,
  roles,
  passwordPolicy,
  enterprise,
};
