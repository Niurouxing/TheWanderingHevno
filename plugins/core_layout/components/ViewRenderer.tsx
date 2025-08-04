import React from 'react';
import { useService } from '@hevno/frontend-sdk';
import { PluginService } from '@hevno/frontend-sdk/types'; // 引用类型

interface ViewRendererProps {
  contributionPoint: string;
  className?: string;
  children?: React.ReactNode; // 允许传递默认内容
}

const ViewRenderer: React.FC<ViewRendererProps> = ({ contributionPoint, className, children }) => {
  const pluginService = useService<PluginService>('plugins');
  // 使用 useMemo 防止不必要的重计算
  const contributions = React.useMemo(() => 
    pluginService.getAllViewContributions()[contributionPoint] || [],
    [pluginService, contributionPoint]
  );
  
  if (contributions.length === 0) {
    return <>{children}</>; // 如果没有贡献，渲染默认子节点
  }
  
  return (
    <div className={className}>
      {contributions.map(contrib => {
        const Component = pluginService.getComponent(contrib.pluginId, contrib.component);
        if (!Component) {
          console.warn(`[core-layout] Component "${contrib.component}" from plugin "${contrib.pluginId}" not found for contribution point "${contributionPoint}".`);
          return null;
        }
        return <Component key={contrib.id} />;
      })}
    </div>
  );
};

export default ViewRenderer;