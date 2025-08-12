// plugins/sandbox_editor/src/editors/RuntimeConfigForm.jsx
import React from 'react';
import { Box, TextField, Select, MenuItem, FormControlLabel, Switch, Typography, FormControl, InputLabel } from '@mui/material';
import { CodexInvokeEditor } from './CodexInvokeEditor.jsx';
// [MODIFIED] Import the new editor for llm.default
import { LlmContentsEditor } from './LlmContentsEditor.jsx';

const RUNTIME_CONFIG_SPECS = {
    // LLM
    // llm.default is now handled by a custom component, so it is removed from here.
    // Memoria
    'memoria.add': [
        { key: 'stream', type: 'text', label: '流名称', required: true },
        { key: 'content', type: 'text', label: '内容 (支持宏)', multiline: true, required: true },
        // [MODIFIED] Updated label to guide user
        { key: 'level', type: 'text', label: '级别 (如 event, user, model)', default: 'event' },
        { key: 'tags', type: 'text', label: '标签 (逗号分隔)', },
    ],
    'memoria.query': [
        { key: 'stream', type: 'text', label: '流名称', required: true },
        { key: 'latest', type: 'text', label: '最新N条 (数字)' },
        { key: 'levels', type: 'text', label: '级别 (逗号分隔)' },
        { key: 'tags', type: 'text', label: '标签 (逗号分隔)' },
        { key: 'order', type: 'select', label: '排序', options: ['升序', '降序'], default: '升序' },
        // [NEW] Add the new format field with user-friendly labels
        { 
            key: 'format', 
            type: 'select', 
            label: '返回格式', 
            options: [
                { value: 'raw_entries', label: '原始条目 (raw_entries)' },
                { value: 'message_list', label: '消息列表 (message_list)' },
            ], 
            default: 'raw_entries' 
        },
    ],
    // Codex
    'codex.invoke': [
            { key: 'recursion_enabled', type: 'switch', label: '启用递归', default: false },
            { key: 'debug', type: 'switch', label: '启用调试输出', default: false },
    ],
    // System IO
    'system.io.input': [
        { key: 'value', type: 'text', label: '值 (任意 JSON 兼容)', multiline: true, required: true },
    ],
    'system.io.log': [
        { key: 'message', type: 'text', label: '消息', multiline: true, required: true },
        { key: 'level', type: 'select', label: '级别', options: ['调试', '信息', '警告', '错误', '严重'], default: '信息' },
    ],
    // System Data
    'system.data.format': [
        { key: 'items', type: 'text', label: '条目 (列表/字典宏)', multiline: true, required: true },
        { key: 'template', type: 'text', label: '模板 (如 {item.name})', multiline: false, required: true },
        { key: 'joiner', type: 'text', label: '连接符', multiline: false, default: '\\n' },
    ],
    'system.data.parse': [
        { key: 'text', type: 'text', label: '文本 (宏)', multiline: true, required: true },
        { key: 'format', type: 'select', label: '格式', options: ['json', 'xml'], default: 'json', required: true },
        { key: 'strict', type: 'switch', label: '严格模式', default: false },
        { key: 'selector', type: 'text', label: '选择器 (用于 XML)' },
    ],
    'system.data.regex': [
        { key: 'text', type: 'text', label: '文本 (宏)', multiline: true, required: true },
        { key: 'pattern', type: 'text', label: '正则表达式 (如 (?P<name>...))', multiline: false, required: true },
        { key: 'mode', type: 'select', label: '模式', options: ['查找', '全部查找'], default: '查找' },
    ],
    // System Flow
    'system.flow.call': [
        { key: 'graph', type: 'text', label: '图名称 (ID)', multiline: false, required: true },
        { key: 'using', type: 'text', label: '参数 (字典宏)', multiline: true },
    ],
    'system.flow.map': [
        { key: 'list', type: 'text', label: '列表 (宏)', multiline: true, required: true },
        { key: 'graph', type: 'text', label: '图名称 (ID)', multiline: false, required: true },
        { key: 'using', type: 'text', label: '参数 (字典宏，可用 source.item)', multiline: true },
        { key: 'collect', type: 'text', label: '收集 (子图节点宏)', multiline: true },
    ],
    // System Advanced
    'system.execute': [
        { key: 'code', type: 'text', label: '代码 (宏)', multiline: true, required: true },
    ],
};

export function RuntimeConfigForm({ runtimeType, config, onConfigChange }) {
  const spec = RUNTIME_CONFIG_SPECS[runtimeType] || [];

  const handleChange = (key, value) => {
    // For comma-separated text fields that should be arrays
    if (['tags', 'levels'].includes(key) && typeof value === 'string') {
        onConfigChange({ ...config, [key]: value.split(',').map(s => s.trim()).filter(Boolean) });
    } else {
        onConfigChange({ ...config, [key]: value });
    }
  };
  
  const hasGenericFields = spec.length > 0;
  const isCodexInvoke = runtimeType === 'codex.invoke';
  // [NEW] Add a check for the llm.default runtime
  const isLlmDefault = runtimeType === 'llm.default';

  // [MODIFIED] Adjust the condition to include the new custom editor
  if (!hasGenericFields && !isCodexInvoke && !isLlmDefault) {
    return <Typography color="text.secondary" sx={{mt:2}}>该指令不需要额外配置</Typography>
  }

  return (
    <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Typography variant="subtitle2">配置</Typography>
      
      {/* [NEW] Render the custom contents editor for 'llm.default' */}
      {isLlmDefault && (
        <LlmContentsEditor 
            contents={config.contents || []} 
            onContentsChange={(newContents) => handleChange('contents', newContents)}
        />
      )}
      
      {isCodexInvoke && (
        <CodexInvokeEditor
            value={config.from}
            onChange={(newValue) => handleChange('from', newValue)}
        />
      )}
      
      {spec.map(field => {
        let value = config[field.key];
        // Handle array-to-string conversion for text fields
        if (['tags', 'levels'].includes(field.key) && Array.isArray(value)) {
            value = value.join(', ');
        }
        // Set default value
        value = value ?? field.default ?? (field.type === 'switch' ? false : '');
        
        switch (field.type) {
          case 'text':
            return (
              <TextField
                key={field.key}
                label={field.label}
                required={field.required}
                value={value}
                onChange={(e) => handleChange(field.key, e.target.value)}
                fullWidth
                multiline={field.multiline}
                variant="outlined"
                size="small"
              />
            );
          case 'select':
            return (
             <FormControl fullWidth size="small" key={field.key}>
                <InputLabel>{field.label}</InputLabel>
                <Select
                    label={field.label}
                    required={field.required}
                    value={value}
                    onChange={(e) => handleChange(field.key, e.target.value)}
                >
                    {/* [MODIFIED] Handle both string arrays and object arrays for options */}
                    {field.options.map(opt => {
                      const optValue = typeof opt === 'object' ? opt.value : opt;
                      const optLabel = typeof opt === 'object' ? opt.label : opt;
                      return <MenuItem key={optValue} value={optValue}>{optLabel}</MenuItem>
                    })}
                </Select>
            </FormControl>
            );
          case 'switch':
            return (
              <FormControlLabel
                key={field.key}
                control={
                  <Switch
                    checked={!!value}
                    onChange={(e) => handleChange(field.key, e.target.checked)}
                  />
                }
                label={field.label}
              />
            );
          default:
            return null;
        }
      })}
    </Box>
  );
}