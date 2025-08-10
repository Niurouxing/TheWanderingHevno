// plugins/sandbox_editor/src/editors/RuntimeConfigForm.jsx
// 根据 runtime 类型渲染特定 config 表单的组件
import React from 'react';
import { Box, TextField, Select, MenuItem, FormControlLabel, Switch } from '@mui/material';

// 定义所有 runtime 的 config 字段及其类型
// type 可以是: 'text' (支持 multiline), 'select' (需提供 options), 'switch' (boolean)
const RUNTIME_CONFIG_SPECS = {
  'system.io.input': [
    { key: 'value', type: 'text', label: 'Value', multiline: true },
  ],
  'system.io.log': [
    { key: 'message', type: 'text', label: 'Message', multiline: true },
    { key: 'level', type: 'select', label: 'Level', options: ['debug', 'info', 'warning', 'error', 'critical'], default: 'info' },
  ],
  'system.data.format': [
    { key: 'items', type: 'text', label: 'Items (macro for list or dict)', multiline: true },
    { key: 'template', type: 'text', label: 'Template', multiline: false },
    { key: 'joiner', type: 'text', label: 'Joiner', multiline: false, default: '\\n' },
  ],
  'system.data.parse': [
    { key: 'text', type: 'text', label: 'Text (macro)', multiline: true },
    { key: 'format', type: 'select', label: 'Format', options: ['json'], default: 'json' }, // 未来可添加更多
    { key: 'strict', type: 'switch', label: 'Strict Mode', default: false },
  ],
  'system.data.regex': [
    { key: 'text', type: 'text', label: 'Text (macro)', multiline: true },
    { key: 'pattern', type: 'text', label: 'Pattern', multiline: false },
    { key: 'mode', type: 'select', label: 'Mode', options: ['search', 'find_all'], default: 'search' },
  ],
  'system.flow.call': [
    { key: 'graph', type: 'text', label: 'Graph (name)', multiline: false },
    { key: 'using', type: 'text', label: 'Using (macro for dict)', multiline: true },
  ],
  'system.flow.map': [
    { key: 'list', type: 'text', label: 'List (macro)', multiline: true },
    { key: 'graph', type: 'text', label: 'Graph (name)', multiline: false },
    { key: 'using', type: 'text', label: 'Using (macro for dict)', multiline: true },
    { key: 'collect', type: 'text', label: 'Collect (macro)', multiline: true },
  ],
  'system.execute': [
    { key: 'code', type: 'text', label: 'Code (macro)', multiline: true },
  ],
  // 如果有更多 runtime，可以在此添加
};

export function RuntimeConfigForm({ runtimeType, config, onConfigChange }) {
  const spec = RUNTIME_CONFIG_SPECS[runtimeType] || [];

  const handleChange = (key, value) => {
    onConfigChange({ ...config, [key]: value });
  };

  return (
    <Box sx={{ mt: 2 }}>
      {spec.map(field => {
        switch (field.type) {
          case 'text':
            return (
              <TextField
                key={field.key}
                label={field.label}
                value={config[field.key] || field.default || ''}
                onChange={(e) => handleChange(field.key, e.target.value)}
                fullWidth
                multiline={field.multiline}
                rows={field.multiline ? 3 : 1}
                sx={{ mb: 2 }}
              />
            );
          case 'select':
            return (
              <Select
                key={field.key}
                label={field.label}
                value={config[field.key] || field.default || ''}
                onChange={(e) => handleChange(field.key, e.target.value)}
                fullWidth
                sx={{ mb: 2 }}
              >
                {field.options.map(opt => <MenuItem key={opt} value={opt}>{opt}</MenuItem>)}
              </Select>
            );
          case 'switch':
            return (
              <FormControlLabel
                key={field.key}
                control={
                  <Switch
                    checked={config[field.key] ?? field.default ?? false}
                    onChange={(e) => handleChange(field.key, e.target.checked)}
                  />
                }
                label={field.label}
                sx={{ mb: 2 }}
              />
            );
          // 可以添加更多类型，如 'json' 用于复杂对象，使用 JSON.stringify/parse
          default:
            return null;
        }
      })}
    </Box>
  );
}