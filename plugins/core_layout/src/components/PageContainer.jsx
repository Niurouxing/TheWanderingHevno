// plugins/core_layout/src/components/PageContainer.jsx
import React, { useState, useEffect, useMemo } from 'react';
import { useLayout } from '../context/LayoutContext';
import { Box, Typography, CircularProgress } from '@mui/material';

// 将组件的创建和缓存移到组件外部或使用 useMemo，以避免在每次渲染时重新创建 LazyComponent
const componentCache = new Map();

function getLazyComponent(pageInfo) {
  const { id, manifest, componentExportName } = pageInfo;

  if (componentCache.has(id)) {
    return componentCache.get(id);
  }

  const LazyComponent = React.lazy(async () => {
    // 动态 import 路径
    const modulePath = `/plugins/${manifest.id}/${manifest.frontend.srcEntryPoint || manifest.frontend.entryPoint}`;
    
    try {
      const module = await import(/* @vite-ignore */ modulePath);
      if (module[componentExportName]) {
        // React.lazy 期望一个包含 default 导出的模块
        return { default: module[componentExportName] };
      } else {
        // 如果找不到具名导出，尝试默认导出
        if (module.default) {
           return { default: module.default }
        }
        throw new Error(`Component export '${componentExportName}' not found in plugin '${manifest.id}'.`);
      }
    } catch (error) {
      console.error(`Failed to load component for plugin '${manifest.id}':`, error);
      // 返回一个显示错误的组件
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
  
  // 使用 useMemo 来根据 activePageId 查找页面信息并获取懒加载组件
  // 只有当 activePageId 变化时，才会重新计算
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
    // Suspense 包裹懒加载组件，提供 fallback UI
    <React.Suspense fallback={<Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>}>
      {/* 在这里将 props 传递给将要被渲染的组件 */}
      <ActiveLazyComponent services={services} />
    </React.Suspense>
  );
}