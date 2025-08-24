// plugins/sandbox_editor/src/components/SchemaField.jsx
import React from 'react';
import { TextField, Select, MenuItem, FormControl, InputLabel, FormControlLabel, Switch, Chip, Box } from '@mui/material';

// [修改] 将辅助函数导出，以便父组件可以使用它
export const isStringArrayField = (schema) => {
  if (!schema) return false;
  if (schema.type === 'array' && schema.items?.type === 'string') return true;
  if (Array.isArray(schema.anyOf)) {
    return schema.anyOf.some(item => item.type === 'array' && item.items?.type === 'string');
  }
  return false;
};

export function SchemaField({ fieldKey, schema, value, onChange }) {
  const label = schema.title || fieldKey;
  const description = schema.description || null;
  const defaultValue = schema.default;

  const isBooleanField = schema.type === 'boolean' || (Array.isArray(schema.anyOf) && schema.anyOf.some(item => item.type === 'boolean'));
  const isStringArray = isStringArrayField(schema);

  const currentValue = value ?? defaultValue ?? (isBooleanField ? false : (isStringArray ? [] : ''));

  // [核心修改] 这里的 handleChange 现在是通用的，它只负责传递来自UI组件的原始值
  const handleChange = (event) => {
    const { type, checked, value } = event.target;
    const finalValue = type === 'checkbox' ? checked : value;
    onChange(fieldKey, finalValue); // 将原始值 (可能是字符串) 传递给父组件
  };
  
  if (isStringArray) {
    // 确保我们在这里总是处理一个数组，以安全地渲染 chips
    const chipArray = Array.isArray(currentValue) ? currentValue : [];

    // 将数组转换为字符串以在 TextField 中显示
    const displayString = chipArray.join(', ');

    return (
      <TextField
        label={label}
        value={displayString}
        onChange={handleChange} // 当用户输入时，调用通用handleChange，它会传递TextField的完整字符串
        helperText={description || "输入值并用逗号分隔"}
        fullWidth
        size="small"
        variant="outlined"
        InputProps={{
          startAdornment: (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mr: 1, p: '2px 0' }}>
              {chipArray.map((item, index) => (
                <Chip
                  key={`${item}-${index}`}
                  label={item}
                  size="small"
                  // 注意：这里不再需要 onDelete，因为所有编辑都在文本框中完成
                />
              ))}
            </Box>
          ),
        }}
      />
    );
  }

  // --- 其他字段类型的渲染保持不变 ---

  if (schema.enum) {
    return (
      <FormControl fullWidth size="small" variant="outlined">
        <InputLabel>{label}</InputLabel>
        <Select label={label} value={currentValue || ''} onChange={handleChange}>
          {schema.enum.map((option) => (<MenuItem key={option} value={option}>{option}</MenuItem>))}
        </Select>
      </FormControl>
    );
  }
  
  if (isBooleanField) {
    return (
      <FormControlLabel
        control={<Switch checked={!!currentValue} onChange={handleChange} />}
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