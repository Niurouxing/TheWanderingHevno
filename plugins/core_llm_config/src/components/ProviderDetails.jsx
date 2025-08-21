// plugins/core_llm_config/src/components/ProviderDetails.jsx

import React from 'react';
import { Box, Typography, Chip } from '@mui/material';

export function ProviderDetails({ provider }) {
    if (!provider) return null;

    return (
        <Box>
            <Typography variant="h6" gutterBottom>
                提供商详情: {provider.id}
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="body2" color="text.secondary">类型:</Typography>
                    <Chip size="small" label={provider.type} />
                </Box>
                {provider.model_mapping && Object.keys(provider.model_mapping).length > 0 && (
                    <Box>
                        <Typography variant="body2" color="text.secondary" gutterBottom>模型映射:</Typography>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                            {Object.entries(provider.model_mapping).map(([alias, canonical]) => (
                                <Chip 
                                    key={alias} 
                                    size="small" 
                                    variant="outlined" 
                                    label={`${alias} → ${canonical}`} 
                                />
                            ))}
                        </Box>
                    </Box>
                )}
            </Box>
        </Box>
    );
}
