import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useAuth } from '../stores/authStore';
import { wsClient, ConnectionStatus, WebSocketEnvelope, EventCallback } from '../services/websocket/wsClient';

export interface WebSocketContextType {
  status: ConnectionStatus;
  subscribe: (event: string, callback: EventCallback) => () => void;
  subscribeToApplication: (
    applicationId: string,
    callback: (envelope: WebSocketEnvelope) => void
  ) => () => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isInitializing } = useAuth();
  const [status, setStatus] = useState<ConnectionStatus>(wsClient.currentStatus);

  useEffect(() => {
    const unsub = wsClient.onStatusChange((newStatus) => {
      setStatus(newStatus);
    });
    return unsub;
  }, []);

  useEffect(() => {
    if (isInitializing) return;

    if (isAuthenticated) {
      wsClient.connect();
    } else {
      wsClient.disconnect();
    }

    return () => {
      wsClient.disconnect();
    };
  }, [isAuthenticated, isInitializing]);

  const subscribe = useCallback((event: string, callback: EventCallback) => {
    return wsClient.subscribe(event, callback);
  }, []);

  const subscribeToApplication = useCallback(
    (applicationId: string, callback: (envelope: WebSocketEnvelope) => void) => {
      const handler: EventCallback = (envelope) => {
        if (
          envelope.data &&
          String(envelope.data.application_id).toLowerCase() === String(applicationId).toLowerCase()
        ) {
          callback(envelope);
        }
      };

      const unsubs = [
        wsClient.subscribe('clarification.created', handler),
        wsClient.subscribe('clarification.responded', handler),
        wsClient.subscribe('clarification.accepted', handler),
        wsClient.subscribe('clarification.rejected', handler),
        wsClient.subscribe('clarification.further_requested', handler),
      ];

      return () => {
        unsubs.forEach((unsub) => unsub());
      };
    },
    []
  );

  return (
    <WebSocketContext.Provider value={{ status, subscribe, subscribeToApplication }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};
