// plugins/core_layout/src/components/PageContainer.jsx
import React, { useMemo } from 'react';
import { useLayout } from '../context/LayoutContext';
import { Box, Typography, CircularProgress } from '@mui/material';

// getLazyComponent 函数保持不变
const componentCache = new Map();
function getLazyComponent(pageInfo) {
  const { id, manifest, componentExportName } = pageInfo;
  if (componentCache.has(id)) {
    return componentCache.get(id);
  }
  const LazyComponent = React.lazy(async () => {
    const modulePath = `/plugins/${manifest.id}/${manifest.frontend.srcEntryPoint || manifest.frontend.entryPoint}`;
    try {
      const module = await import(/* @vite-ignore */ modulePath);
      if (module[componentExportName]) {
        return { default: module[componentExportName] };
      } else {
        if (module.default) {
           return { default: module.default }
        }
        throw new Error(`Component export '${componentExportName}' not found in plugin '${manifest.id}'.`);
      }
    } catch (error) {
      console.error(`Failed to load component for plugin '${manifest.id}':`, error);
      const ErrorComponent = () => (
        <Box sx={{ p: 2, color: 'error.main' }}>
          <Typography>Error loading page: {manifest.id}</Typography>
          <Typography variant="body2">{error.message}</Typography>
        </Box>
      );
      return { default: ErrorComponent };
    }
  });
  componentCache.set(id, LazyComponent);
  return LazyComponent;
}


export function PageContainer() {
  const { pages, activePageId, services } = useLayout();
  
  const ActiveLazyComponent = useMemo(() => {
    if (!activePageId) return null;
    const pageInfo = pages.find(p => p.id === activePageId);
    return pageInfo ? getLazyComponent(pageInfo) : null;
  }, [activePageId, pages]);

  if (!ActiveLazyComponent) {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h5">Hevno</Typography>
        <Typography color="text.secondary">戳一下那个按钮试试</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%', height: '100%', position: 'relative' }}>
        <React.Suspense fallback={<Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>}>
            <ActiveLazyComponent services={services} />
        </React.Suspense>
    </Box>
  );
}