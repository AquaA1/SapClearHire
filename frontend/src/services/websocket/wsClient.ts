/**
 * ClearHire Robust Real-Time WebSocket Client.
 * 
 * Features:
 * - Single-use ticket authentication (never exposes long-lived JWTs in URLs).
 * - Per-tab isolation with automatic lifecycle management.
 * - Exponential backoff reconnection with fresh ticket acquisition.
 * - Heartbeat keepalive ping/pong.
 * - Event-based subscription bus for clarification workflows.
 */

import { authService } from '../api/authService';

export type ConnectionStatus = 'connected' | 'reconnecting' | 'offline';

export interface WebSocketEnvelope<T = { application_id?: string; clarification_id?: string; [key: string]: unknown }> {
  event_id: string;
  event: string;
  timestamp: string;
  data: T;
}

export type EventCallback = (envelope: WebSocketEnvelope) => void;
export type StatusCallback = (status: ConnectionStatus) => void;

function getWebSocketUrl(ticket: string): string {
  const envUrl = (import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000/api/v1';
  try {
    const url = new URL(envUrl);
    const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    const basePath = url.pathname.replace(/\/+$/, '');
    return `${protocol}//${url.host}${basePath}/ws?ticket=${encodeURIComponent(ticket)}`;
  } catch {
    const isHttps = window.location.protocol === 'https:';
    const protocol = isHttps ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.hostname}:8000/api/v1/ws?ticket=${encodeURIComponent(ticket)}`;
  }
}

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private status: ConnectionStatus = 'offline';
  private statusListeners: Set<StatusCallback> = new Set();
  private eventListeners: Map<string, Set<EventCallback>> = new Map();
  private reconnectTimeout: number | null = null;
  private heartbeatInterval: number | null = null;
  private reconnectAttempts = 0;
  private maxReconnectDelay = 15000;
  private isExplicitDisconnect = false;

  public get currentStatus(): ConnectionStatus {
    return this.status;
  }

  public onStatusChange(callback: StatusCallback): () => void {
    this.statusListeners.add(callback);
    callback(this.status);
    return () => this.statusListeners.delete(callback);
  }

  private setStatus(newStatus: ConnectionStatus): void {
    if (this.status !== newStatus) {
      this.status = newStatus;
      this.statusListeners.forEach((cb) => cb(newStatus));
    }
  }

  public subscribe(event: string, callback: EventCallback): () => void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, new Set());
    }
    this.eventListeners.get(event)!.add(callback);

    return () => {
      const set = this.eventListeners.get(event);
      if (set) {
        set.delete(callback);
        if (set.size === 0) this.eventListeners.delete(event);
      }
    };
  }

  public async connect(): Promise<void> {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.isExplicitDisconnect = false;
    this.clearTimers();

    try {
      this.setStatus('reconnecting');
      const ticketRes = await authService.getWsTicket();
      if (!ticketRes || !ticketRes.ticket) {
        throw new Error('Failed to obtain WebSocket connection ticket');
      }

      const wsUrl = getWebSocketUrl(ticketRes.ticket);
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.setStatus('connected');
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          if (event.data === 'pong') return;
          const envelope: WebSocketEnvelope = JSON.parse(event.data);
          if (envelope && envelope.event) {
            // Dispatch to specific event listeners
            const listeners = this.eventListeners.get(envelope.event);
            if (listeners) {
              listeners.forEach((cb) => cb(envelope));
            }
            // Dispatch to wildcard '*' listeners
            const wildcards = this.eventListeners.get('*');
            if (wildcards) {
              wildcards.forEach((cb) => cb(envelope));
            }
          }
        } catch (err) {
          console.debug('Failed to parse WebSocket message:', err);
        }
      };

      this.ws.onerror = (err) => {
        console.debug('WebSocket error encountered:', err);
      };

      this.ws.onclose = (event) => {
        this.clearHeartbeat();
        this.ws = null;

        if (this.isExplicitDisconnect) {
          this.setStatus('offline');
          return;
        }

        // If ticket was rejected with 4401, immediately try to obtain fresh ticket on next attempt
        this.scheduleReconnect();
      };
    } catch (err) {
      console.debug('WebSocket connection attempt failed:', err);
      this.scheduleReconnect();
    }
  }

  public disconnect(): void {
    this.isExplicitDisconnect = true;
    this.clearTimers();
    if (this.ws) {
      try {
        this.ws.close();
      } catch {}
      this.ws = null;
    }
    this.setStatus('offline');
    this.reconnectAttempts = 0;
  }

  private scheduleReconnect(): void {
    if (this.isExplicitDisconnect) return;

    this.setStatus('reconnecting');
    const delay = Math.min(1000 * Math.pow(1.8, this.reconnectAttempts), this.maxReconnectDelay);
    this.reconnectAttempts += 1;

    if (this.reconnectTimeout) {
      window.clearTimeout(this.reconnectTimeout);
    }

    this.reconnectTimeout = window.setTimeout(() => {
      this.connect();
    }, delay);
  }

  private startHeartbeat(): void {
    this.clearHeartbeat();
    this.heartbeatInterval = window.setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        try {
          this.ws.send('ping');
        } catch {}
      }
    }, 25000);
  }

  private clearHeartbeat(): void {
    if (this.heartbeatInterval) {
      window.clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  private clearTimers(): void {
    this.clearHeartbeat();
    if (this.reconnectTimeout) {
      window.clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }
}

export const wsClient = new WebSocketClient();
