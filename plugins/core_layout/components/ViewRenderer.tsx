/** @jsxImportSource @emotion/react */
import React from 'react';
import { useService } from '@hevno/frontend-sdk';
import { PluginService } from '@hevno/frontend-sdk/types';

interface ViewRendererProps {
  contributionPoint: string;
  className?: string; // Emotion 会通过这个 prop 注入样式
  children?: React.ReactNode;
}

const ViewRenderer: React.FC<ViewRendererProps> = ({ contributionPoint, className, children }) => {
  const pluginService = useService<PluginService>('plugins');
  const contributions = React.useMemo(() => 
    pluginService.getAllViewContributions()[contributionPoint] || [],
    [pluginService, contributionPoint]
  );
  
  if (contributions.length === 0) {
    // 如果没有贡献，渲染默认子节点，并应用 className
    return <div className={className}>{children}</div>;
  }
  
  return (
    // 将 className 应用到包裹元素上
    <div className={className}>
      {contributions.map(contrib => {
        const Component = pluginService.getComponent(contrib.pluginId, contrib.component);
        if (!Component) {
          console.warn(`[core_layout] Component "${contrib.component}" from plugin "${contrib.pluginId}" not found for contribution point "${contributionPoint}".`);
          return null;
        }
        return <Component key={contrib.id} />;
      })}
    </div>
  );
};

export default ViewRenderer;