/**
 * WebSocket Hook for Real-Time Alert Updates
 * 
 * Provides instant updates when alerts are created, updated, or cleared.
 * Automatically reconnects on disconnection.
 */

import { useEffect, useRef, useCallback, useState, useMemo } from 'react';

const RECONNECT_DELAY = 3000; // 3 seconds
const PING_INTERVAL = 30000; // 30 seconds

/**
 * Hook for real-time alert updates via WebSocket
 * 
 * @param {Object} options - Configuration options
 * @param {Function} options.onAlertCreated - Called when a new alert is created
 * @param {Function} options.onAlertUpdated - Called when an alert is updated
 * @param {Function} options.onAlertCleared - Called when an alert is cleared
 * @param {Function} options.onAlertDeleted - Called when an alert is deleted
 * @param {Function} options.onPollComplete - Called when a polling cycle completes
 * @param {Function} options.onConnected - Called when WebSocket connects
 * @param {Function} options.onDisconnected - Called when WebSocket disconnects
 * @param {boolean} options.enabled - Whether to enable the WebSocket connection
 * @returns {Object} - WebSocket state and controls
 */
export function useAlertWebSocket({
  onAlertCreated,
  onAlertUpdated,
  onAlertCleared,
  onAlertDeleted,
  onPollComplete,
  onConnected,
  onDisconnected,
  enabled = true,
} = {}) {
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const pingIntervalRef = useRef(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [connectionAttempts, setConnectionAttempts] = useState(0);

  // Build WebSocket URL
  const getWebSocketUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return `${protocol}//${host}/ws/alerts`;
  }, []);

  // Handle incoming messages
  const handleMessage = useCallback((event) => {
    // Ignore pong responses (plain text, not JSON)
    if (event.data === 'pong') {
      return;
    }
    
    try {
      const message = JSON.parse(event.data);
      setLastMessage(message);

      switch (message.type) {
        case 'connected':
          console.log('[WebSocket] Connected to alert stream');
          break;

        case 'alert_event':
          const { event: alertEvent, alert } = message;
          
          switch (alertEvent) {
            case 'created':
              console.log('[WebSocket] Alert created:', alert.id);
              onAlertCreated?.(alert);
              break;
            case 'updated':
              console.log('[WebSocket] Alert updated:', alert.id);
              onAlertUpdated?.(alert);
              break;
            case 'cleared':
              console.log('[WebSocket] Alert cleared:', alert.id);
              onAlertCleared?.(alert);
              break;
            case 'deleted':
              console.log('[WebSocket] Alert deleted:', alert.id);
              onAlertDeleted?.(alert.id);
              break;
            default:
              console.log('[WebSocket] Unknown alert event:', alertEvent);
          }
          break;

        case 'system_event':
          if (message.event === 'poll_complete') {
            console.log('[WebSocket] Poll complete:', message.data);
            onPollComplete?.(message.data);
          }
          break;

        default:
          console.log('[WebSocket] Unknown message type:', message.type);
      }
    } catch (error) {
      console.error('[WebSocket] Error parsing message:', error);
    }
  }, [onAlertCreated, onAlertUpdated, onAlertCleared, onAlertDeleted, onPollComplete]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const url = getWebSocketUrl();
    console.log('[WebSocket] Connecting to:', url);

    try {
      wsRef.current = new WebSocket(url);

      wsRef.current.onopen = () => {
        console.log('[WebSocket] Connection established');
        setIsConnected(true);
        setConnectionAttempts(0);
        onConnected?.();

        // Start ping interval to keep connection alive
        pingIntervalRef.current = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send('ping');
          }
        }, PING_INTERVAL);
      };

      wsRef.current.onmessage = handleMessage;

      wsRef.current.onclose = (event) => {
        console.log('[WebSocket] Connection closed:', event.code, event.reason);
        setIsConnected(false);
        onDisconnected?.();

        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        // Attempt to reconnect if enabled
        if (enabled) {
          setConnectionAttempts(prev => prev + 1);
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('[WebSocket] Attempting to reconnect...');
            connect();
          }, RECONNECT_DELAY);
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
      };
    } catch (error) {
      console.error('[WebSocket] Failed to create connection:', error);
    }
  }, [enabled, getWebSocketUrl, handleMessage, onConnected, onDisconnected]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
  }, []);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    if (enabled) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  return {
    isConnected,
    lastMessage,
    connectionAttempts,
    connect,
    disconnect,
  };
}

/**
 * Hook that combines WebSocket updates with a refetch function
 * 
 * This is the recommended way to use WebSocket updates - it will
 * automatically refetch data when relevant events occur.
 * 
 * @param {Function} refetch - Function to call to refetch data
 * @param {Object} options - Additional options
 * @returns {Object} - WebSocket state
 */
export function useAlertWebSocketRefresh(refetch, options = {}) {
  // Use a ref to always have access to the latest refetch function
  // This prevents stale closure issues when refetch changes
  const refetchRef = useRef(refetch);
  
  // Keep the ref updated with the latest refetch function
  useEffect(() => {
    refetchRef.current = refetch;
  }, [refetch]);

  // Stable callback that always calls the latest refetch
  const handleAlertChange = useCallback(() => {
    console.log('[WebSocket] Alert change detected, triggering refresh');
    refetchRef.current?.();
  }, []); // No dependencies - uses ref instead

  return useAlertWebSocket({
    onAlertCreated: handleAlertChange,
    onAlertUpdated: handleAlertChange,
    onAlertCleared: handleAlertChange,
    onAlertDeleted: handleAlertChange,
    onPollComplete: handleAlertChange,
    ...options,
  });
}

export default useAlertWebSocket;
