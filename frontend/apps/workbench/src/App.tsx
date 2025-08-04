import React from 'react';
import { useService } from '@hevno/frontend-sdk';
import { PluginService } from '@hevno/frontend-sdk/types';

function App() {
  const pluginService = useService<PluginService>('plugins');
  
  // 按照约定，从 'core_layout' 插件获取 'WorkbenchRoot' 组件
  const WorkbenchRoot = React.useMemo(
    () => pluginService.getComponent('core_layout', 'WorkbenchRoot'),
    [pluginService]
  );

  if (!WorkbenchRoot) {
    return (
        <div style={{ /* ... */ }}>
            <h1>Loading Core Layout...</h1>
            <p>If this message persists, check the console for errors.</p>
        </div>
    );
  }
  
  return <WorkbenchRoot />;
}

export default App;