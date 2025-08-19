// plugins/core_runner_ui/src/components/DynamicComponentLoader.jsx
import React from 'react';
import { CircularProgress, Box } from '@mui/material';

// 将懒加载逻辑封装成一个可复用的组件
const componentCache = new Map();

function getLazyComponent(contribution) {
    const cacheKey = `${contribution.pluginId}-${contribution.componentExportName}`;
    if (componentCache.has(cacheKey)) {
        return componentCache.get(cacheKey);
    }

    const LazyComponent = React.lazy(async () => {
        const modulePath = `/plugins/${contribution.pluginId}/${contribution.manifest.frontend.srcEntryPoint}`;
        try {
            const module = await import(/* @vite-ignore */ modulePath);
            if (module[contribution.componentExportName]) {
                return { default: module[contribution.componentExportName] };
            }
            throw new Error(`Component export '${contribution.componentExportName}' not found in plugin '${contribution.pluginId}'.`);
        } catch (error) {
            console.error(error);
            const ErrorComponent = () => <Box sx={{ p: 1, color: 'error.main' }}>Error loading component: {contribution.id}</Box>;
            return { default: ErrorComponent };
        }
    });

    componentCache.set(cacheKey, LazyComponent);
    return LazyComponent;
}


export function DynamicComponentLoader({ contribution, services, props = {} }) {
    if (!contribution) return null;

    const Component = getLazyComponent(contribution);

    return (
        <React.Suspense fallback={<CircularProgress size={24} />}>
            <Component {...props} services={services} />
        </React.Suspense>
    );
}