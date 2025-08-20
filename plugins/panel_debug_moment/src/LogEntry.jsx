// plugins/panel_debug_moment/src/LogEntry.jsx
import React from 'react';
import { Accordion, AccordionSummary, AccordionDetails, Typography, Box, Chip, Tooltip } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CodeIcon from '@mui/icons-material/Code';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import WarningAmberOutlinedIcon from '@mui/icons-material/WarningAmberOutlined';
import ErrorOutlineOutlinedIcon from '@mui/icons-material/ErrorOutlineOutlined';
import BugReportOutlinedIcon from '@mui/icons-material/BugReportOutlined';

const LogLogLevels = {
    info: { icon: <InfoOutlinedIcon fontSize="small" />, color: 'info', title: '信息' },
    debug: { icon: <BugReportOutlinedIcon fontSize="small" />, color: 'default', title: '调试' },
    warning: { icon: <WarningAmberOutlinedIcon fontSize="small" />, color: 'warning', title: '警告' },
    error: { icon: <ErrorOutlineOutlinedIcon fontSize="small" />, color: 'error', title: '错误' },
    critical: { icon: <ErrorOutlineOutlinedIcon fontSize="small" />, color: 'error', title: '严重' },
};

const JsonViewer = ({ data, title }) => (
    <Box>
        <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5 }}>{title}</Typography>
        <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontSize: '12px', background: 'rgba(0,0,0,0.2)', padding: '8px', borderRadius: '4px' }}>
            {JSON.stringify(data, null, 2)}
        </pre>
    </Box>
);

const LLMCallDetails = ({ data }) => {
    if (!data) return <Typography>No data.</Typography>;
    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {data.request && <JsonViewer data={data.request} title="Request Payload" />}
            {data.response && <JsonViewer data={data.response} title="Response Payload" />}
        </Box>
    );
};

const SystemLogDetails = ({ data }) => {
     if (!data) return <Typography>No data.</Typography>;
     return <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '12px' }}>{data.message}</Typography>;
};


export function LogEntry({ item }) {
    let icon, title, summary, DetailsComponent;

    switch (item.type) {
        case 'llm_call':
            icon = <CodeIcon fontSize="small" />;
            title = 'LLM 调用';
            summary = item.data?.request?.model_name || '未知模型';
            DetailsComponent = <LLMCallDetails data={item.data} />;
            break;
        case 'system_log':
            const levelInfo = LogLogLevels[item.data?.level] || LogLogLevels.info;
            icon = levelInfo.icon;
            title = levelInfo.title;
            summary = item.data?.message;
            DetailsComponent = <SystemLogDetails data={item.data} />;
            break;
        default:
            icon = <InfoOutlinedIcon fontSize="small" />;
            title = '未知日志';
            summary = JSON.stringify(item.data);
            DetailsComponent = <JsonViewer data={item} title="Raw Data" />;
    }

    const timestamp = new Date(item.timestamp).toLocaleTimeString();

    return (
        <Accordion
            disableGutters
            elevation={0}
            sx={{
                bgcolor: 'transparent',
                backgroundImage: 'none',
                borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                '&:before': { display: 'none' },
                '&:last-of-type': { borderBottom: 'none' },
            }}
        >
            <AccordionSummary 
                expandIcon={<ExpandMoreIcon />} 
                sx={{ 
                    '& .MuiAccordionSummary-content': { overflow: 'hidden', my: 1 },
                    // 减弱 hover 效果
                    '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.04)' }
                }}
            >
                <Box sx={{ display: 'flex', flexDirection: 'column', width: '100%', overflow: 'hidden' }}>
                    {/* 第一行: 图标, 标题, 节点ID, 和时间戳 */}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, width: '100%' }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexShrink: 0 }}>
                            {icon}
                            <Typography variant="body2" sx={{ fontWeight: 'bold' }}>{title}</Typography>
                        </Box>
                        <Tooltip title="来源节点">
                            <Chip
                                label={item.node_id}
                                size="small"
                                variant="outlined"
                                sx={{
                                    height: '20px', fontSize: '0.7rem', color: 'text.secondary',
                                    borderColor: 'rgba(255, 255, 255, 0.23)',
                                    fontFamily: 'monospace',
                                }}
                            />
                        </Tooltip>
                        <Typography variant="caption" sx={{ ml: 'auto', flexShrink: 0, color: 'text.secondary' }}>
                            {timestamp}
                        </Typography>
                    </Box>
                    {/* 第二行: 日志摘要 */}
                    <Typography variant="body2" noWrap sx={{ color: 'text.secondary', mt: 0.5, fontSize: '0.8rem', pl: '28px' }}>
                        {summary}
                    </Typography>
                </Box>
            </AccordionSummary>
            <AccordionDetails sx={{ bgcolor: 'rgba(0,0,0,0.2)', p: 2, borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                {DetailsComponent}
            </AccordionDetails>
        </Accordion>
    );
}