// plugins/core_statusbar_item/src/ConnectionStatus.jsx

import React, { useState, useEffect, useCallback } from 'react';

export function ConnectionStatus() {
    // 【修改】通过全局服务定位器主动“拉取”所需的服务
    const hookManager = window.Hevno.services.get('hookManager');
    const remoteProxy = window.Hevno.services.get('remoteProxy');
    
    console.log('[ConnectionStatus] Services retrieved:', { hookManager, remoteProxy });

    // 1. 初始状态同步：从 remoteProxy 获取当前连接状态
    const [isConnected, setIsConnected] = useState(remoteProxy?.isConnected || false);

    console.log(`[ConnectionStatus] Initial state set to: ${isConnected}`);

    useEffect(() => {
        console.log('[ConnectionStatus] useEffect running.');
        if (!hookManager || !remoteProxy) {
            console.warn('[ConnectionStatus] useEffect: core services not available!');
            return;
        }

        const handleConnected = () => {
            console.log('[ConnectionStatus] Event: websocket.connected. Setting state to true.');
            setIsConnected(true);
        };
        const handleDisconnected = () => {
            console.log('[ConnectionStatus] Event: websocket.disconnected. Setting state to false.');
            setIsConnected(false);
        };
        
        hookManager.addImplementation('websocket.connected', handleConnected);
        hookManager.addImplementation('websocket.disconnected', handleDisconnected);
        
        // 【关键】再次同步状态：防止在组件挂载和effect执行之间发生的事件丢失
        const currentState = remoteProxy.isConnected;
        console.log(`[ConnectionStatus] useEffect: Syncing state. Current proxy state: ${currentState}, component state: ${isConnected}`);
        if (currentState !== isConnected) {
            console.log('[ConnectionStatus] useEffect: State out of sync, forcing update.');
            setIsConnected(currentState);
        }
        
        return () => {
            console.log('[ConnectionStatus] useEffect cleanup.');
            hookManager.removeImplementation('websocket.connected', handleConnected);
            hookManager.removeImplementation('websocket.disconnected', handleDisconnected);
        };
        
    }, [hookManager, remoteProxy]); // 依赖项是正确的

    console.log(`[ConnectionStatus] FINAL RENDER with isConnected: ${isConnected}`);

  const style = {
    display: 'flex',
    alignItems: 'center',
    gap: '5px',
    fontSize: '0.9em',
  };

  return (
    <div style={style}>
      {isConnected ? (
        <>
          <span>🟢</span>
          <span>Connected</span>
        </>
      ) : (
        <>
          <span>🔴</span>
          <span>Disconnected</span>
        </>
      )}
    </div>
  );
}