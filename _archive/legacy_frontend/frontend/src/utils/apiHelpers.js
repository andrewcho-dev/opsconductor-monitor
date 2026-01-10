/**
 * API Response Helpers
 * 
 * Centralized utilities for handling API responses consistently.
 * Use these instead of duplicating response extraction logic.
 * 
 * Usage:
 *   import { extractData, handleApiError, isSuccess } from '../utils/apiHelpers';
 *   
 *   const data = extractData(response);
 *   if (!isSuccess(response)) handleApiError(response, setError);
 */

/**
 * Extract data from API response, handling various response formats.
 * 
 * Handles:
 * - { data: [...] } wrapper format
 * - { success: true, data: [...] } format
 * - Direct array response
 * - Direct object response
 * 
 * @param {Object|Array} response - API response
 * @param {*} defaultValue - Default value if extraction fails
 * @returns {*} Extracted data
 * 
 * @example
 * const users = extractData(response, []);
 * const user = extractData(response, null);
 */
export function extractData(response, defaultValue = null) {
  if (!response) return defaultValue;
  
  // Handle { data: ... } wrapper
  if (response.data !== undefined) {
    return response.data;
  }
  
  // Handle direct array
  if (Array.isArray(response)) {
    return response;
  }
  
  // Handle direct object (but not error objects)
  if (typeof response === 'object' && !response.error && !response.code) {
    return response;
  }
  
  return defaultValue;
}

/**
 * Extract array data, always returns an array.
 * 
 * @param {Object|Array} response - API response
 * @returns {Array} Extracted array data
 */
export function extractArrayData(response) {
  const data = extractData(response, []);
  return Array.isArray(data) ? data : [];
}

/**
 * Check if API response indicates success.
 * 
 * @param {Object} response - API response
 * @returns {boolean} True if successful
 */
export function isSuccess(response) {
  if (!response) return false;
  
  // Explicit success field
  if (response.success !== undefined) {
    return response.success === true;
  }
  
  // No error field means success
  if (response.error === undefined && response.code === undefined) {
    return true;
  }
  
  return false;
}

/**
 * Extract error message from API response.
 * 
 * @param {Object} response - API response or Error
 * @returns {string} Error message
 */
export function extractError(response) {
  if (!response) return 'Unknown error';
  
  // Handle Error objects
  if (response instanceof Error) {
    return response.message;
  }
  
  // Handle { error: { message: '...' } }
  if (response.error?.message) {
    return response.error.message;
  }
  
  // Handle { error: '...' }
  if (typeof response.error === 'string') {
    return response.error;
  }
  
  // Handle { message: '...' }
  if (response.message) {
    return response.message;
  }
  
  // Handle { detail: { message: '...' } }
  if (response.detail?.message) {
    return response.detail.message;
  }
  
  // Handle { detail: '...' }
  if (typeof response.detail === 'string') {
    return response.detail;
  }
  
  return 'An error occurred';
}

/**
 * Handle API error by extracting message and calling error setter.
 * 
 * @param {Object} response - API response or Error
 * @param {Function} setError - Error state setter function
 * @param {string} fallbackMessage - Fallback message if extraction fails
 */
export function handleApiError(response, setError, fallbackMessage = 'An error occurred') {
  const message = extractError(response) || fallbackMessage;
  if (setError) {
    setError(message);
  }
  console.error('API Error:', message, response);
}

/**
 * Get pagination info from response.
 * 
 * @param {Object} response - API response
 * @returns {Object} Pagination info { total, page, perPage, hasNext, hasPrev }
 */
export function extractPagination(response) {
  const meta = response?.meta || response;
  
  return {
    total: meta?.total || meta?.count || 0,
    page: meta?.page || 1,
    perPage: meta?.per_page || meta?.limit || 50,
    hasNext: meta?.has_next || false,
    hasPrev: meta?.has_prev || false,
    totalPages: meta?.total_pages || 1,
  };
}

/**
 * Format API endpoint with query parameters.
 * 
 * @param {string} endpoint - Base endpoint
 * @param {Object} params - Query parameters (nullish values are omitted)
 * @returns {string} Formatted URL with query string
 * 
 * @example
 * formatEndpoint('/api/users', { status: 'active', role: null })
 * // Returns: '/api/users?status=active'
 */
export function formatEndpoint(endpoint, params = {}) {
  const searchParams = new URLSearchParams();
  
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      searchParams.append(key, value);
    }
  });
  
  const queryString = searchParams.toString();
  return queryString ? `${endpoint}?${queryString}` : endpoint;
}
