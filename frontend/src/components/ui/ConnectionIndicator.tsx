import React from 'react';
import { useWebSocket } from '../../contexts/WebSocketContext';
import { Wifi, WifiOff } from 'lucide-react';

export const ConnectionIndicator: React.FC<{ className?: string }> = ({ className = '' }) => {
  const { status } = useWebSocket();

  if (status === 'connected') {
    return (
      <div
        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-pill bg-success-dim/40 border border-success/30 text-[11px] font-medium text-success select-none ${className}`}
        title="Real-time WebSocket connected and receiving live updates"
      >
        <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse shrink-0" />
        <span>Live</span>
      </div>
    );
  }

  if (status === 'reconnecting') {
    return (
      <div
        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-pill bg-warn-dim/40 border border-warn/30 text-[11px] font-medium text-warn select-none ${className}`}
        title="Attempting to re-establish real-time connection..."
      >
        <span className="w-1.5 h-1.5 rounded-full bg-warn animate-ping shrink-0" />
        <span>Reconnecting...</span>
      </div>
    );
  }

  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-pill bg-elevated border border-subtle text-[11px] font-medium text-muted select-none ${className}`}
      title="Real-time updates currently offline"
    >
      <span className="w-1.5 h-1.5 rounded-full bg-muted shrink-0" />
      <span>Offline</span>
    </div>
  );
};
