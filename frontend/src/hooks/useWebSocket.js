import { useEffect, useRef, useCallback } from 'react'
import { io } from 'socket.io-client'

export default function useSocketIO(onMessage) {
  const socketRef = useRef(null)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) return

    // Connect to Socket.IO server on backend port
    const socket = io(`http://${window.location.hostname}:5001`, {
      auth: { token },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
    })

    socket.on('connect', () => {
      console.log('Socket.IO connected')
    })

    socket.on('disconnect', (reason) => {
      console.log('Socket.IO disconnected:', reason)
    })

    socket.on('connect_error', (error) => {
      // Silent - Socket.IO will auto-reconnect
    })

    // Listen for alert events
    socket.on('alert_created', (data) => {
      onMessage?.({ type: 'alert_created', ...data })
    })

    socket.on('alert_updated', (data) => {
      onMessage?.({ type: 'alert_updated', ...data })
    })

    socket.on('alert_resolved', (data) => {
      onMessage?.({ type: 'alert_resolved', ...data })
    })

    socket.on('connected', (data) => {
      console.log('Socket.IO welcome:', data)
    })

    socketRef.current = socket

    return () => {
      socket.disconnect()
    }
  }, [onMessage])

  return socketRef.current
}
