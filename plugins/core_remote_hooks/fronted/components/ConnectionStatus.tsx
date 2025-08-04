// plugins/core_remote_hooks/fronted/components/ConnectionStatus.tsx
import React, { useState, useEffect } from 'react';
import { useEvent } from '@hevno/frontend-sdk';

// 简单的SVG图标
const DotIcon = ({ color }: { color: string }) => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="6" cy="6" r="5" fill={color} />
  </svg>
);

export default function ConnectionStatus() {
  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  
  useEvent('websocket:status_changed', (payload) => {
    setStatus(payload.status);
  });

  const statusMap = {
    connecting: { color: 'orange', text: 'Connecting...' },
    connected: { color: 'lightgreen', text: 'Connected' },
    disconnected: { color: 'red', text: 'Disconnected' },
  };

  return (
    <div className="flex items-center space-x-2" title={statusMap[status].text}>
      <DotIcon color={statusMap[status].color} />
      <span>{statusMap[status].text}</span>
    </div>
  );
}