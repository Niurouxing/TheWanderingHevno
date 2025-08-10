// plugins/sandbox_editor/src/editors/RuntimeConfigForm.jsx
import React from 'react';
import { Box, TextField, Select, MenuItem, FormControlLabel, Switch, Typography, FormControl, InputLabel } from '@mui/material';

// --- [MODIFIED] Added specs for all new runtimes from the docs ---
const RUNTIME_CONFIG_SPECS = {
  // LLM
  'llm.default': [
    { key: 'model', type: 'text', label: 'Model (e.g., provider/model_id)', required: true },
    { key: 'prompt', type: 'text', label: 'Prompt', multiline: true, required: true },
    { key: 'temperature', type: 'text', label: 'Temperature (Optional)', multiline: false },
    // Other specific params can be added as needed, or handled via a generic "extra_params" JSON field.
  ],
  // Memoria
  'memoria.add': [
    { key: 'stream', type: 'text', label: 'Stream Name', required: true },
    { key: 'content', type: 'text', label: 'Content (supports macros)', multiline: true, required: true },
    { key: 'level', type: 'text', label: 'Level (e.g., event)', default: 'event' },
    { key: 'tags', type: 'text', label: 'Tags (comma-separated)', },
  ],
  'memoria.query': [
    { key: 'stream', type: 'text', label: 'Stream Name', required: true },
    { key: 'latest', type: 'text', label: 'Latest N Entries (number)' },
    { key: 'levels', type: 'text', label: 'Levels (comma-separated)' },
    { key: 'tags', type: 'text', label: 'Tags (comma-separated)' },
    { key: 'order', type: 'select', label: 'Order', options: ['ascending', 'descending'], default: 'ascending' },
  ],
  'memoria.aggregate': [
    { key: 'entries', type: 'text', label: 'Entries (macro, e.g., from pipe.output)', required: true, multiline: true },
    { key: 'template', type: 'text', label: 'Template', default: '{content}' },
    { key: 'joiner', type: 'text', label: 'Joiner', default: '\\n\\n' },
  ],
  // Codex
  'codex.invoke': [
      { key: 'from', type: 'text', label: 'From (JSON list of {"codex": "...", "source": "..."})', required: true, multiline: true },
      { key: 'recursion_enabled', type: 'switch', label: 'Enable Recursion', default: false },
      { key: 'debug', type: 'switch', label: 'Enable Debug Output', default: false },
  ],
  // System IO
  'system.io.input': [
    { key: 'value', type: 'text', label: 'Value (any JSON-compatible)', multiline: true, required: true },
  ],
  'system.io.log': [
    { key: 'message', type: 'text', label: 'Message', multiline: true, required: true },
    { key: 'level', type: 'select', label: 'Level', options: ['debug', 'info', 'warning', 'error', 'critical'], default: 'info' },
  ],
  // System Data
  'system.data.format': [
    { key: 'items', type: 'text', label: 'Items (macro for list/dict)', multiline: true, required: true },
    { key: 'template', type: 'text', label: 'Template (e.g., {item.name})', multiline: false, required: true },
    { key: 'joiner', type: 'text', label: 'Joiner', multiline: false, default: '\\n' },
  ],
  'system.data.parse': [
    { key: 'text', type: 'text', label: 'Text (macro)', multiline: true, required: true },
    { key: 'format', type: 'select', label: 'Format', options: ['json', 'xml'], default: 'json', required: true },
    { key: 'strict', type: 'switch', label: 'Strict Mode', default: false },
    { key: 'selector', type: 'text', label: 'Selector (for XML)' },
  ],
  'system.data.regex': [
    { key: 'text', type: 'text', label: 'Text (macro)', multiline: true, required: true },
    { key: 'pattern', type: 'text', label: 'Pattern (e.g., (?P<name>...))', multiline: false, required: true },
    { key: 'mode', type: 'select', label: 'Mode', options: ['search', 'find_all'], default: 'search' },
  ],
  // System Flow
  'system.flow.call': [
    { key: 'graph', type: 'text', label: 'Graph Name (ID)', multiline: false, required: true },
    { key: 'using', type: 'text', label: 'Using (macro for dict)', multiline: true },
  ],
  'system.flow.map': [
    { key: 'list', type: 'text', label: 'List (macro)', multiline: true, required: true },
    { key: 'graph', type: 'text', label: 'Graph Name (ID)', multiline: false, required: true },
    { key: 'using', type: 'text', label: 'Using (macro for dict, can use source.item)', multiline: true },
    { key: 'collect', type: 'text', label: 'Collect (macro, from sub-graph nodes)', multiline: true },
  ],
  // System Advanced
  'system.execute': [
    { key: 'code', type: 'text', label: 'Code (macro)', multiline: true, required: true },
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

  if (spec.length === 0) {
    return <Typography color="text.secondary" sx={{mt:2}}>No configuration needed for this runtime.</Typography>
  }

  return (
    <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Typography variant="subtitle2">Configuration</Typography>
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
                rows={field.multiline ? 3 : 1}
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
                    {field.options.map(opt => <MenuItem key={opt} value={opt}>{opt}</MenuItem>)}
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