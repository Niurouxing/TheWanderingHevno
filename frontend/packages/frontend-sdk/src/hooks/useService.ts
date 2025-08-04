// frontend/packages/frontend-sdk/src/hooks/useService.ts
import { useMemo } from 'react';
import { HevnoGlobal } from '../types';

export function useService<T>(name: string): T {
  return useMemo(() => {
    return (window as any).Hevno.services.registry.resolve<T>(name);
  }, [name]);
}