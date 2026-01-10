/**
 * OpenAPI 3.x Services - Central Export
 * 
 * All API services organized by domain:
 * - identity: Authentication, users, roles
 * - inventory: Devices, interfaces, topology
 * - monitoring: Metrics, alerts, polling
 * - automation: Workflows, jobs, scheduling
 * - integrations: NetBox, PRTG, MCP
 * - system: Settings, logs, health
 * - credentials: Credential vault
 * - notifications: Notification channels
 */

export { default as identityApi } from './identity';
export { default as inventoryApi } from './inventory';
export { default as monitoringApi } from './monitoring';
export { default as automationApi } from './automation';
export { default as integrationsApi } from './integrations';
export { default as systemApi } from './system';
export { default as credentialsApi } from './credentials';
export { default as notificationsApi } from './notifications';

// Re-export individual service modules
export * from './identity';
export * from './inventory';
export * from './monitoring';
export * from './automation';
export * from './integrations';
export * from './system';
export * from './credentials';
export * from './notifications';
