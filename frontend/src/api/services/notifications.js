/**
 * Notifications API Service - OpenAPI 3.x
 * 
 * Endpoints: /notifications/v1/*
 * - Notification channels
 * - Notification rules
 * - Notification templates
 */

import { apiClient, API_DOMAINS } from '../client';

const BASE = API_DOMAINS.NOTIFICATIONS;

/**
 * Channels
 */
export const channels = {
  list: () => 
    apiClient.get(`${BASE}/channels`),
  
  get: (channelId) => 
    apiClient.get(`${BASE}/channels/${channelId}`),
  
  create: (channelData) => 
    apiClient.post(`${BASE}/channels`, channelData),
  
  update: (channelId, channelData) => 
    apiClient.put(`${BASE}/channels/${channelId}`, channelData),
  
  delete: (channelId) => 
    apiClient.delete(`${BASE}/channels/${channelId}`),
  
  test: (channelId) => 
    apiClient.post(`${BASE}/channels/${channelId}/test`),
  
  enable: (channelId) => 
    apiClient.post(`${BASE}/channels/${channelId}/enable`),
  
  disable: (channelId) => 
    apiClient.post(`${BASE}/channels/${channelId}/disable`),
};

/**
 * Rules
 */
export const rules = {
  list: () => 
    apiClient.get(`${BASE}/rules`),
  
  get: (ruleId) => 
    apiClient.get(`${BASE}/rules/${ruleId}`),
  
  create: (ruleData) => 
    apiClient.post(`${BASE}/rules`, ruleData),
  
  update: (ruleId, ruleData) => 
    apiClient.put(`${BASE}/rules/${ruleId}`, ruleData),
  
  delete: (ruleId) => 
    apiClient.delete(`${BASE}/rules/${ruleId}`),
  
  enable: (ruleId) => 
    apiClient.post(`${BASE}/rules/${ruleId}/enable`),
  
  disable: (ruleId) => 
    apiClient.post(`${BASE}/rules/${ruleId}/disable`),
};

/**
 * Templates
 */
export const templates = {
  list: () => 
    apiClient.get(`${BASE}/templates`),
  
  get: (templateId) => 
    apiClient.get(`${BASE}/templates/${templateId}`),
  
  create: (templateData) => 
    apiClient.post(`${BASE}/templates`, templateData),
  
  update: (templateId, templateData) => 
    apiClient.put(`${BASE}/templates/${templateId}`, templateData),
  
  delete: (templateId) => 
    apiClient.delete(`${BASE}/templates/${templateId}`),
  
  preview: (templateId, context = {}) => 
    apiClient.post(`${BASE}/templates/${templateId}/preview`, context),
};

/**
 * History
 */
export const history = {
  list: (params = {}) => 
    apiClient.get(`${BASE}/history`, params),
  
  get: (notificationId) => 
    apiClient.get(`${BASE}/history/${notificationId}`),
};

export default {
  channels,
  rules,
  templates,
  history,
};
