// frontend/packages/frontend-sdk/src/hooks/useEvent.ts
import { useEffect } from 'react';
import { useService } from './useService';
// [修正] 从 SDK 自己的类型文件中导入
import type { ServiceBus } from '../types';

export function useEvent(eventName: string, handler: (payload?: any) => void) {
  const bus = useService<ServiceBus>('bus');
  
  useEffect(() => {
    const unsubscribe = bus.on(eventName, handler);
    return () => unsubscribe(); // 组件卸载时自动清理
  }, [bus, eventName, handler]);
}