// plugins/sandbox_editor/src/SandboxEditorPage.jsx
import React from 'react';
import { Box, Typography } from '@mui/material';
import { useLayout } from '../../core_layout/src/context/LayoutContext'; // 注意: 路径基于 monorepo 假设调整，或使用相对路径

export function SandboxEditorPage({ services }) {
  const { currentSandboxId } = useLayout();

  if (!currentSandboxId) {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h6" color="error">No sandbox selected for editing.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, height: '100%', overflowY: 'auto' }}>
      <Typography variant="h4" gutterBottom>Editing Sandbox: {currentSandboxId}</Typography>
      {/* 这里是编辑器页面的最小实现，实际内容留空。未来可以添加图编辑器、作用域管理等组件 */}
      <Typography color="text.secondary">Editor UI placeholder. Implement graph/scope editing here.</Typography>
    </Box>
  );
}

export default SandboxEditorPage;