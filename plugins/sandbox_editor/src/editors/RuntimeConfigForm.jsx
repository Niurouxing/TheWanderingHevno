// plugins/sandbox_editor/src/editors/RuntimeConfigForm.jsx
import React from 'react';
import { Box, Typography } from '@mui/material';
import { SchemaField } from '../components/SchemaField';
import { CodexInvokeEditor } from './CodexInvokeEditor.jsx';
import { LlmContentsEditor } from './LlmContentsEditor.jsx';
import { LlmModelEditor } from './LlmModelEditor.jsx';

// [新增] 导入 isStringArrayField 辅助函数，父组件需要用它来做判断
import { isStringArrayField } from '../components/SchemaField';

export function RuntimeConfigForm({ runtimeType, schema, config, onConfigChange }) {
  
  // --- [核心修改] 创建一个更智能的 handleChange，它知道如何处理来自 SchemaField 的原始值 ---
  const handleChange = (key, value) => {
    const fieldSchema = schema.properties[key];
    let finalValue = value;

    // 检查这个字段是否期望一个字符串数组
    if (fieldSchema && isStringArrayField(fieldSchema)) {
      // 如果是，并且收到的值是字符串，就将其转换为数组
      if (typeof value === 'string') {
        finalValue = value.split(',').map(item => item.trim()).filter(Boolean);
      } else if (!Array.isArray(value)) {
        // 提供一个回退，以防收到意外的类型
        finalValue = [];
      }
    }
    
    // 用格式正确的值更新 config 对象
    const newConfig = { ...config, [key]: finalValue };
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
      
      {Object.entries(schema.properties).map(([key, propSchema]) => {

        if (runtimeType === 'llm.default' && key === 'contents') {
          return (
            <LlmContentsEditor 
              key={key}
              contents={config.contents || []} 
              onContentsChange={(newContents) => handleChange('contents', newContents)}
            />
          );
        }

        if (runtimeType === 'llm.default' && key === 'model') {
            return (
                <LlmModelEditor
                    key={key}
                    value={config.model}
                    onChange={(newValue) => handleChange('model', newValue)}
                    schema={propSchema}
                />
            );
        }

        if (runtimeType === 'codex.invoke' && key === 'from') {
          return (
            <CodexInvokeEditor
              key={key}
              value={config.from || []}
              onChange={(newValue) => handleChange('from', newValue)}
            />
          );
        }
        
        // 将新的、更智能的 handleChange 传递给 SchemaField
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