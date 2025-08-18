// plugins/sandbox_editor/src/components/SchemaField.jsx
import React from 'react';
import { TextField, Select, MenuItem, FormControl, InputLabel, FormControlLabel, Switch } from '@mui/material';

export function SchemaField({ fieldKey, schema, value, onChange }) {
  const label = schema.title || fieldKey;
  const description = schema.description || null;
  const defaultValue = schema.default;
  const currentValue = value ?? defaultValue;

  const handleChange = (event) => {
    const { type, checked, value } = event.target;
    const finalValue = type === 'checkbox' ? checked : value;
    onChange(fieldKey, finalValue);
  };
  
  // 渲染下拉选择框 (for enums)
  if (schema.enum) {
    return (
      <FormControl fullWidth size="small" variant="outlined">
        <InputLabel>{label}</InputLabel>
        <Select
          label={label}
          value={currentValue || ''}
          onChange={handleChange}
          // helperText is not a prop for Select, description should be handled outside if needed
        >
          {schema.enum.map((option) => (
            <MenuItem key={option} value={option}>
              {option}
            </MenuItem>
          ))}
        </Select>
        {/* We can add a FormHelperText component for description if needed */}
      </FormControl>
    );
  }

  // 渲染开关 (for booleans)
  if (schema.type === 'boolean') {
    return (
      <FormControlLabel
        control={
          <Switch
            checked={!!currentValue}
            onChange={handleChange}
          />
        }
        label={label}
      />
    );
  }
  
  // 渲染数字输入框
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
  // 简单的启发式方法来决定是否使用多行文本框
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
