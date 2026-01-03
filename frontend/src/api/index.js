/**
 * API module index.
 * 
 * Re-exports all API modules for convenient imports.
 */

export { apiClient, ApiError, extractData, extractList, extractPaginated } from './client';
export * as devicesApi from './devices';
export * as groupsApi from './groups';
export * as jobsApi from './jobs';
export * as schedulerApi from './scheduler';
export * as scansApi from './scans';

// Default export with all APIs
import devicesApi from './devices';
import groupsApi from './groups';
import jobsApi from './jobs';
import schedulerApi from './scheduler';
import scansApi from './scans';

export default {
  devices: devicesApi,
  groups: groupsApi,
  jobs: jobsApi,
  scheduler: schedulerApi,
  scans: scansApi,
};
