// plugins/sandbox_editor/src/editors/RuntimeConfigForm.jsx
import React from 'react';
import { Box, Typography } from '@mui/material';
import { SchemaField } from '../components/SchemaField';
// [恢复] 重新导入我们现有的高级编辑器
import { CodexInvokeEditor } from './CodexInvokeEditor.jsx';
import { LlmContentsEditor } from './LlmContentsEditor.jsx';

//接收新的 runtimeType prop
export function RuntimeConfigForm({ runtimeType, schema, config, onConfigChange }) {
  
  const handleChange = (key, value) => {
    const newConfig = { ...config, [key]: value };
    onConfigChange(newConfig);
  };
  
  if (!schema) {
    return <Typography color="text.secondary" sx={{mt:2}}>该指令无需配置或Schema正在加载...</Typography>;
  }
  
  if (!schema.properties || Object.keys(schema.properties).length === 0) {
      return <Typography color="text.secondary" sx={{mt:2}}>该指令无需配置。</Typography>;
  }

  return (
    <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Typography variant="subtitle2">配置</Typography>
      
      {/* 
        [核心修改] 
        我们不再是简单地循环所有属性。
        而是循环所有属性，并对每个属性进行判断：
        - 如果是特殊情况，渲染自定义组件。
        - 否则，渲染通用的 SchemaField。
      */}
      {Object.entries(schema.properties).map(([key, propSchema]) => {

        // --- 特殊情况 1: llm.default 的 'contents' 字段 ---
        if (runtimeType === 'llm.default' && key === 'contents') {
          return (
            <LlmContentsEditor 
              key={key}
              contents={config.contents || []} 
              onContentsChange={(newContents) => handleChange('contents', newContents)}
            />
          );
        }

        // --- 特殊情况 2: codex.invoke 的 'from' 字段 ---
        if (runtimeType === 'codex.invoke' && key === 'from') {
          return (
            <CodexInvokeEditor
              key={key}
              value={config.from || []} // 确保传递一个数组
              onChange={(newValue) => handleChange('from', newValue)}
            />
          );
        }
        
        // --- 默认情况: 渲染通用的 SchemaField ---
        // 这将处理所有其他字段，例如 llm.default 的 'model' 和 'temperature'
        return (
          <SchemaField
            key={key}
            fieldKey={key}
            schema={propSchema}
            value={config[key]}
            onChange={handleChange}
          />
        );
      })}
    </Box>
  );
}