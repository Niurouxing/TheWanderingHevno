// plugins/sandbox_editor/src/editors/LlmModelEditor.jsx
import React, { useState, useEffect } from 'react';
import { Box, Typography, TextField, Chip, Paper } from '@mui/material';
import { getLlmProviders } from '../utils/schemaManager';

export function LlmModelEditor({ value, onChange, schema }) {
    const [providers, setProviders] = useState([]);

    useEffect(() => {
        const providerData = getLlmProviders();
        if (providerData) {
            setProviders(providerData);
        }
    }, []);

    const label = schema.title || '模型';
    const description = schema.description || "格式: 'provider_id/model_name'";

    return (
        <Box>
            <TextField
                label={label}
                value={value || ''}
                onChange={(e) => onChange(e.target.value)}
                helperText={description}
                fullWidth
                size="small"
                variant="outlined"
            />
            {providers.length > 0 && (
                <Paper variant="outlined" sx={{ p: 1.5, mt: 1, fontSize: '0.8rem', backgroundColor: 'rgba(0,0,0,0.2)' }}>
                    <Typography variant="caption" display="block" color="text.secondary" sx={{ mb: 1 }}>
                        <b>可用提供商和别名:</b>
                    </Typography>
                    {providers.map(p => (
                        <Box key={p.id} sx={{ mb: 1 }}>
                            <Chip label={p.id} size="small" variant="filled" color="primary" />
                            {Object.entries(p.model_mapping).length > 0 && (
                                <Box component="span" sx={{ ml: 1, color: 'text.secondary' }}>
                                    (别名: {Object.entries(p.model_mapping).map(([alias, real]) => `${alias} -> ${real}`).join(', ')})
                                </Box>
                            )}
                        </Box>
                    ))}
                </Paper>
            )}
        </Box>
    );
}
