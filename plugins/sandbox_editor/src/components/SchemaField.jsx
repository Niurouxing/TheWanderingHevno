// plugins/sandbox_editor/src/components/SchemaField.jsx
import React from 'react';
import { TextField, Select, MenuItem, FormControl, InputLabel, FormControlLabel, Switch } from '@mui/material';

export function SchemaField({ fieldKey, schema, value, onChange }) {
  const label = schema.title || fieldKey;
  const description = schema.description || null;
  const defaultValue = schema.default;

  // --- [核心修复 3/3] ---
  // 判断一个字段是否为布尔类型的最终逻辑
  const isBooleanField = 
      schema.type === 'boolean' || 
      (Array.isArray(schema.anyOf) && schema.anyOf.some(item => item.type === 'boolean'));

  const currentValue = value ?? defaultValue ?? (isBooleanField ? false : '');

  const handleChange = (event) => {
    const { type, checked, value } = event.target;
    const finalValue = type === 'checkbox' ? checked : value;
    onChange(fieldKey, finalValue);
  };

  if (schema.enum) {
    return (
      <FormControl fullWidth size="small" variant="outlined">
        <InputLabel>{label}</InputLabel>
        <Select
          label={label}
          value={currentValue || ''}
          onChange={handleChange}
        >
          {schema.enum.map((option) => (
            <MenuItem key={option} value={option}>
              {option}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    );
  }
  
  // 使用我们上面定义的 isBooleanField 变量
  if (isBooleanField) {
    return (
      <FormControlLabel
        control={
          <Switch
            checked={!!currentValue}
            onChange={handleChange}
          />
        }
        label={label}
        title={description || ''}
      />
    );
  }

  if (schema.type === 'number' || schema.type === 'integer') {
    return (
        <TextField
            label={label}
            type="number"
            value={currentValue || ''}
            onChange={handleChange}
            helperText={description}
            fullWidth
            size="small"
            variant="outlined"
        />
    );
  }
  
  // 默认渲染文本框 (for strings)
  const isMultiline = schema.description?.toLowerCase().includes('json') || 
                      schema.description?.toLowerCase().includes('宏') ||
                      fieldKey.toLowerCase().includes('code') || 
                      fieldKey.toLowerCase().includes('content') ||
                      fieldKey.toLowerCase().includes('template');
                      
  return (
    <TextField
      label={label}
      value={currentValue || ''}
      onChange={handleChange}
      helperText={description}
      fullWidth
      multiline={isMultiline}
      minRows={isMultiline ? 3 : 1}
      size="small"
      variant="outlined"
    />
  );
}