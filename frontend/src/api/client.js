/**
 * Base API client for OpsConductor.
 * 
 * Provides centralized API communication with:
 * - Standardized error handling
 * - Response parsing
 * - Request/response interceptors
 */

const API_BASE_URL = '/api';

/**
 * Custom API error class
 */
export class ApiError extends Error {
  constructor(code, message, status, details = null) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

/**
 * Parse API response and handle errors
 */
async function parseResponse(response) {
  const contentType = response.headers.get('content-type');
  
  // Handle non-JSON responses
  if (!contentType || !contentType.includes('application/json')) {
    if (!response.ok) {
      throw new ApiError(
        'NETWORK_ERROR',
        `HTTP ${response.status}: ${response.statusText}`,
        response.status
      );
    }
    return { success: true, data: await response.text() };
  }
  
  const data = await response.json();
  
  // Handle error responses
  if (!response.ok || data.success === false) {
    const error = data.error || {};
    throw new ApiError(
      error.code || 'UNKNOWN_ERROR',
      error.message || `HTTP ${response.status}`,
      response.status,
      error.details
    );
  }
  
  return data;
}

/**
 * Make an API request
 */
async function request(endpoint, options = {}) {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
  
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };
  
  // Serialize body if it's an object
  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body);
  }
  
  try {
    const response = await fetch(url, config);
    return await parseResponse(response);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    // Network or other errors
    throw new ApiError(
      'NETWORK_ERROR',
      error.message || 'Network request failed',
      0
    );
  }
}

/**
 * API client with HTTP method helpers
 */
export const apiClient = {
  /**
   * GET request
   */
  get: (endpoint, params = null) => {
    let url = endpoint;
    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== null && value !== undefined) {
          searchParams.append(key, value);
        }
      });
      const queryString = searchParams.toString();
      if (queryString) {
        url += `?${queryString}`;
      }
    }
    return request(url, { method: 'GET' });
  },
  
  /**
   * POST request
   */
  post: (endpoint, body = null) => {
    return request(endpoint, {
      method: 'POST',
      body,
    });
  },
  
  /**
   * PUT request
   */
  put: (endpoint, body = null) => {
    return request(endpoint, {
      method: 'PUT',
      body,
    });
  },
  
  /**
   * DELETE request
   */
  delete: (endpoint) => {
    return request(endpoint, { method: 'DELETE' });
  },
  
  /**
   * PATCH request
   */
  patch: (endpoint, body = null) => {
    return request(endpoint, {
      method: 'PATCH',
      body,
    });
  },
};

/**
 * Extract data from standardized response
 */
export function extractData(response) {
  return response?.data ?? response;
}

/**
 * Extract list data with count
 */
export function extractList(response) {
  return {
    data: response?.data ?? [],
    count: response?.meta?.count ?? response?.data?.length ?? 0,
  };
}

/**
 * Extract paginated data
 */
export function extractPaginated(response) {
  return {
    data: response?.data ?? [],
    total: response?.meta?.total ?? 0,
    page: response?.meta?.page ?? 1,
    perPage: response?.meta?.per_page ?? 50,
    totalPages: response?.meta?.total_pages ?? 1,
    hasNext: response?.meta?.has_next ?? false,
    hasPrev: response?.meta?.has_prev ?? false,
  };
}

export default apiClient;
