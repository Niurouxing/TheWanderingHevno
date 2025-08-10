// plugins/page_demo/src/DemoPage.jsx
import React from 'react';
// 插件可以假设 MUI 组件可用，因为宿主会提供
import { Typography, Card, CardContent, Button } from '@mui/material';

// 插件组件会接收到由宿主 `core_layout` 传入的 props
export function DemoPage({ services }) {
  
  const handleTriggerHook = () => {
    const hookManager = services.get('hookManager');
    // 插件可以通过宿主传入的服务与系统交互
    hookManager.trigger('demo.button.clicked', { from: 'page_demo' });
    alert('Hook "demo.button.clicked" triggered! Check the console.');
  };

  return (
    <Card sx={{ m: 2 }}>
      <CardContent>
        <Typography variant="h4" gutterBottom>
          这是一个演示页面
        </Typography>
        <Typography>
          这个组件是从 `page_demo` 插件动态加载的。
          如果你到达了这个页面，那说明Niurx忘记删了这个页面了
        </Typography>
        <Button 
          variant="contained" 
          sx={{ mt: 2 }} 
          onClick={handleTriggerHook}
        >
          触发一个 Hook
        </Button>
      </CardContent>
    </Card>
  );
}

// 默认导出组件，这是一种常见的模式
export default DemoPage;