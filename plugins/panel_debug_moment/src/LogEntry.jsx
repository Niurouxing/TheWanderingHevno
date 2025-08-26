// plugins/panel_debug_moment/src/LogEntry.jsx
import React from 'react';
import { Accordion, AccordionSummary, AccordionDetails, Typography, Box, Chip, Tooltip } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CodeIcon from '@mui/icons-material/Code';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import WarningAmberOutlinedIcon from '@mui/icons-material/WarningAmberOutlined';
import ErrorOutlineOutlinedIcon from '@mui/icons-material/ErrorOutlineOutlined';
import BugReportOutlinedIcon from '@mui/icons-material/BugReportOutlined';

// --- [新增] 智能JSON渲染器组件 ---

const jsonSyntaxHighlight = {
    key: '#8be9fd',      // 青色
    string: '#f1fa8c',   // 黄色
    number: '#bd93f9',   // 紫色
    boolean: '#ffb86c',  // 橙色
    null: '#ff79c6',      // 粉色
};

/**
 * 递归渲染JSON值，根据不同类型应用不同样式
 */
function JsonValue({ value }) {
    if (value === null) {
        return <span style={{ color: jsonSyntaxHighlight.null }}>null</span>;
    }
    const type = typeof value;
    switch (type) {
        case 'string':
            return <span style={{ color: jsonSyntaxHighlight.string, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>"{value}"</span>;
        case 'number':
            return <span style={{ color: jsonSyntaxHighlight.number }}>{value}</span>;
        case 'boolean':
            return <span style={{ color: jsonSyntaxHighlight.boolean }}>{value.toString()}</span>;
        case 'object':
            if (Array.isArray(value)) {
                return <JsonArray data={value} />;
            }
            return <JsonObject data={value} />;
        default:
            return <span>{String(value)}</span>;
    }
}

/**
 * 渲染可折叠的JSON对象
 */
function JsonObject({ data }) {
    const entries = Object.entries(data);
    if (entries.length === 0) return <span>{"{}"}</span>;
    
    // 生成预览文字，如 { "key1", "key2", ... }
    const preview = `{ ${entries.slice(0, 3).map(([key]) => `"${key}"`).join(', ')}${entries.length > 3 ? ', ...' : ''} }`;

    return (
        <details style={{ marginLeft: '1em' }}>
            <summary style={{ cursor: 'pointer', userSelect: 'none', listStyle: 'revert' }}>
                <span style={{ color: 'text.secondary' }}>{preview}</span>
            </summary>
            <Box sx={{ pl: 2, borderLeft: '1px solid rgba(255,255,255,0.2)' }}>
                {entries.map(([key, value], index) => (
                    <div key={index}>
                        <span style={{ color: jsonSyntaxHighlight.key }}>"{key}"</span>: <JsonValue value={value} />
                    </div>
                ))}
            </Box>
        </details>
    );
}

/**
 * 渲染可折叠的JSON数组
 */
function JsonArray({ data }) {
    if (data.length === 0) return <span>[]</span>;
    const preview = `[ ${data.length} item${data.length !== 1 ? 's' : ''} ]`;

    return (
        <details style={{ marginLeft: '1em' }}>
            <summary style={{ cursor: 'pointer', userSelect: 'none', listStyle: 'revert' }}>
                <span style={{ color: 'text.secondary' }}>{preview}</span>
            </summary>
            <Box sx={{ pl: 2, borderLeft: '1px solid rgba(255,255,255,0.2)' }}>
                {data.map((value, index) => (
                    <div key={index}>
                        <span>{index}:</span> <JsonValue value={value} />
                    </div>
                ))}
            </Box>
        </details>
    );
}

/**
 * 智能JSON查看器入口组件
 */
const SmartJsonViewer = ({ data, title }) => (
    <Box sx={{ fontFamily: 'monospace', fontSize: '13px', p: 1.5, borderRadius: '8px', bgcolor: 'rgba(0,0,0,0.25)' }}>
        {title && <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>{title}</Typography>}
        <JsonValue value={data} />
    </Box>
);

// --- [优化] LLM调用和系统日志的详情组件 ---

/**
 * 优化后的LLM调用详情组件
 * 提取关键信息置顶显示，原始数据可折叠查看
 */
const EnhancedLLMCallDetails = ({ data }) => {
    if (!data) return <Typography>No data.</Typography>;
    const { request, response } = data;

    const modelName = request?.model_name || 'N/A';
    const finishReason = response?.choices?.[0]?.finish_reason;
    const usage = response?.usage;

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {/* 关键信息摘要 */}
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '8px 16px' }}>
                <Box>
                    <Typography variant="caption" color="text.secondary">Model</Typography>
                    <Typography variant="body2" sx={{ wordBreak: 'break-all' }}>{modelName}</Typography>
                </Box>
                {finishReason && (
                    <Box>
                        <Typography variant="caption" color="text.secondary">Finish Reason</Typography>
                        <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>{finishReason.replace(/_/g, ' ')}</Typography>
                    </Box>
                )}
                 {usage && (
                    <Box>
                        <Typography variant="caption" color="text.secondary">Token Usage</Typography>
                        <Tooltip title={`Prompt: ${usage.prompt_tokens}, Completion: ${usage.completion_tokens}`}>
                           <Typography variant="body2">{usage.total_tokens}</Typography>
                        </Tooltip>
                    </Box>
                )}
            </Box>

            {/* 可折叠的原始数据 */}
            {request && <SmartJsonViewer data={request} title="Request Payload" />}
            {response && <SmartJsonViewer data={response} title="Response Payload" />}
        </Box>
    );
};

/**
 * 优化后的系统日志详情组件
 * 如果日志消息是JSON字符串，则使用智能查看器渲染
 */
const SystemLogDetails = ({ data }) => {
     if (!data) return <Typography>No data.</Typography>;
     
     try {
        const parsedJson = JSON.parse(data.message);
        return <SmartJsonViewer data={parsedJson} />;
     } catch (e) {
        return <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontFamily: 'monospace', fontSize: '13px' }}>{data.message}</Typography>;
     }
};


const LogLogLevels = {
    info: { icon: <InfoOutlinedIcon fontSize="small" />, color: 'info', title: '信息' },
    debug: { icon: <BugReportOutlinedIcon fontSize="small" />, color: 'default', title: '调试' },
    warning: { icon: <WarningAmberOutlinedIcon fontSize="small" />, color: 'warning', title: '警告' },
    error: { icon: <ErrorOutlineOutlinedIcon fontSize="small" />, color: 'error', title: '错误' },
    critical: { icon: <ErrorOutlineOutlinedIcon fontSize="small" />, color: 'error', title: '严重' },
};


// --- [重构] 主日志条目组件 ---

export function LogEntry({ item }) {
    let icon, title, summary, DetailsComponent;

    switch (item.type) {
        case 'llm_call':
            icon = <CodeIcon fontSize="small" />;
            title = 'LLM 调用';
            // [优化] 摘要显示更有用的信息
            summary = `[${item.data?.request?.model_name || '...'}] finished with reason: ${item.data?.response?.choices?.[0]?.finish_reason || '...'}`;
            DetailsComponent = <EnhancedLLMCallDetails data={item.data} />;
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
            // [优化] 未知类型也使用新的查看器
            DetailsComponent = <SmartJsonViewer data={item} title="Raw Data" />;
    }

    const timestamp = new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });

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
            // [优化] 解决动画卡顿和性能问题
            // unmountOnExit: 关闭时从DOM中移除内容，提高长列表性能
            // timeout: 固定动画时间，避免因内容长度不同导致动画速度不一
            TransitionProps={{ unmountOnExit: true, timeout: 250 }}
        >
            <AccordionSummary 
                expandIcon={<ExpandMoreIcon />} 
                sx={{ 
                    '& .MuiAccordionSummary-content': { overflow: 'hidden', my: 1.5 },
                    // [优化] 减弱 hover 效果，使其不那么突兀
                    '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.05)' }
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