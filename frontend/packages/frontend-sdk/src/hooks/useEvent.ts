// frontend/packages/frontend-sdk/src/hooks/useEvent.ts
import { useEffect } from 'react';
import { useService } from './useService';
import { ServiceBus } from '../../../kernel/src/ServiceBus'; // 引用类型

export function useEvent(eventName: string, handler: (payload?: any) => void) {
  const bus = useService<ServiceBus>('bus');
  
  useEffect(() => {
    const unsubscribe = bus.on(eventName, handler);
    return () => unsubscribe(); // 组件卸载时自动清理
  }, [bus, eventName, handler]);
}