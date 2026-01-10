import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

// API base URL - use relative path so it goes through Nginx proxy
export const API_BASE = "";

/**
 * Get the browser's timezone abbreviation (e.g., "PST", "EST") or UTC offset (e.g., "UTC-08:00")
 */
export function getTimezoneAbbr() {
  const date = new Date();
  const timeZoneName = date.toLocaleTimeString('en-US', { timeZoneName: 'short' }).split(' ').pop();
  return timeZoneName || `UTC${date.getTimezoneOffset() > 0 ? '-' : '+'}${String(Math.abs(Math.floor(date.getTimezoneOffset() / 60))).padStart(2, '0')}:${String(Math.abs(date.getTimezoneOffset() % 60)).padStart(2, '0')}`;
}

/**
 * Normalize an ISO-like timestamp to ensure it has timezone info.
 * If no timezone is present, assumes UTC and appends 'Z'.
 */
function normalizeTimestamp(value) {
  if (!value) return null;
  let iso = String(value);
  const isoLike = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d{1,6})?)?$/;
  const hasZone = /[Zz]|[+-]\d{2}:?\d{2}$/.test(iso);
  if (isoLike.test(iso) && !hasZone) {
    iso = iso + "Z";
  }
  return iso;
}

/**
 * Format a timestamp to local time with timezone indicator.
 * Output: "12/10/2024, 1:45:30 PM PST"
 */
export function formatLocalTime(value) {
  if (!value) return "—";
  try {
    const iso = normalizeTimestamp(value);
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return value;
    return d.toLocaleString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: 'numeric',
      minute: '2-digit',
      second: '2-digit',
      timeZoneName: 'short'
    });
  } catch {
    return value;
  }
}

/**
 * Format a timestamp to a shorter local time format with timezone indicator.
 * Output: "Dec 10, 1:45 PM PST"
 */
export function formatShortTime(value) {
  if (!value) return "—";
  try {
    const iso = normalizeTimestamp(value);
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return value;
    const datePart = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    const timePart = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', timeZoneName: 'short' });
    return `${datePart}, ${timePart}`;
  } catch {
    return value;
  }
}

/**
 * Format a timestamp to time only with timezone indicator.
 * Output: "1:45:30 PM PST"
 */
export function formatTimeOnly(value) {
  if (!value) return "—";
  try {
    const iso = normalizeTimestamp(value);
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return value;
    return d.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      second: '2-digit',
      timeZoneName: 'short'
    });
  } catch {
    return value;
  }
}

/**
 * Format a timestamp for detailed display (e.g., tables) with timezone.
 * Output: "12/10/2024, 13:45:30 PST" (24-hour format)
 */
export function formatDetailedTime(value) {
  if (!value) return "—";
  try {
    const iso = normalizeTimestamp(value);
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return value;
    return d.toLocaleString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
      timeZoneName: 'short'
    });
  } catch {
    return value;
  }
}

/**
 * Format duration between two timestamps.
 */
export function formatDuration(startedAt, finishedAt) {
  if (!startedAt || !finishedAt) return "—";
  try {
    const start = new Date(normalizeTimestamp(startedAt));
    const end = new Date(normalizeTimestamp(finishedAt));
    const diffSec = (end - start) / 1000;
    // Handle negative durations (data inconsistency) gracefully
    if (diffSec < 0) return "—";
    if (diffSec < 1) return `${(diffSec * 1000).toFixed(0)}ms`;
    if (diffSec < 60) return `${diffSec.toFixed(1)}s`;
    return `${Math.floor(diffSec / 60)}m ${Math.floor(diffSec % 60)}s`;
  } catch {
    return "—";
  }
}

/**
 * Format elapsed duration from a start time to now.
 */
export function formatElapsedDuration(startedAt) {
  if (!startedAt) return "—";
  try {
    const start = new Date(normalizeTimestamp(startedAt));
    const now = new Date();
    const diffSec = Math.floor((now - start) / 1000);
    if (diffSec < 60) return `${diffSec}s`;
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ${diffSec % 60}s`;
    return `${Math.floor(diffSec / 3600)}h ${Math.floor((diffSec % 3600) / 60)}m`;
  } catch {
    return "—";
  }
}

/**
 * Format relative time until a future timestamp.
 */
export function formatRelativeTime(value) {
  if (!value) return "—";
  try {
    const d = new Date(normalizeTimestamp(value));
    const now = new Date();
    const diffMs = d - now;
    const diffSec = Math.floor(diffMs / 1000);
    if (diffSec < 0) return "past";
    if (diffSec < 60) return `in ${diffSec}s`;
    if (diffSec < 3600) return `in ${Math.floor(diffSec / 60)}m`;
    return `in ${Math.floor(diffSec / 3600)}h`;
  } catch {
    return value;
  }
}

export async function fetchApi(endpoint, options = {}) {
  // Get auth token from localStorage (matches AuthContext.jsx TOKEN_KEY)
  const token = localStorage.getItem('opsconductor_session_token');
  
  // Build headers - start with defaults, add options, then add auth
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };
  
  // Add Authorization header if token exists (after options.headers to ensure it's not overwritten)
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  // Destructure options to separate headers from other options
  const { headers: _ignoredHeaders, timeout = 8000, ...restOptions } = options;
  
  // Create AbortController for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...restOptions,
      headers,  // Use our merged headers, not options.headers
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);
    
    // Return JSON response even on error status codes so calling code can handle it
    const data = await response.json().catch(() => ({ detail: response.statusText }));
    
    if (!response.ok) {
      // For auth errors, return the data so calling code can handle gracefully
      if (response.status === 401 || response.status === 403) {
        return data;
      }
      throw new Error(`API error: ${response.statusText}`);
    }
    return data;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new Error('Request timeout');
    }
    throw error;
  }
}
