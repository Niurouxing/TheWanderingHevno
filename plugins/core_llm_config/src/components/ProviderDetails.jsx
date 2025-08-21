// plugins/core_llm_config/src/components/ProviderDetails.jsx

import React from 'react';
import { Box, Typography, Chip, IconButton, Tooltip } from '@mui/material';
// [新增] 导入编辑图标
import EditIcon from '@mui/icons-material/Edit';

// [修改] 添加 onEdit 回调函数
export function ProviderDetails({ provider, onEdit }) {
    if (!provider) return null;

    return (
        <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="h6" component="div">
                    提供商详情: {provider.id}
                </Typography>
                {/* [新增] 编辑按钮 */}
                {!['gemini', 'mock'].includes(provider.id) && (
                    <Tooltip title="编辑此提供商">
                        <IconButton onClick={onEdit} size="small">
                            <EditIcon fontSize="small" />
                        </IconButton>
                    </Tooltip>
                )}
            </Box>
            
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mt: 1 }}>
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
