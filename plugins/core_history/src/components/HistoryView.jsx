import React, { useState, useEffect, useCallback } from 'react';
import './HistoryView.css';

export function HistoryView() {
    const hookManager = window.Hevno.services.get('hookManager');
    const [activeSandbox, setActiveSandbox] = useState(null);
    const [history, setHistory] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchHistory = useCallback(async (sandboxId) => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await fetch(`/api/sandboxes/${sandboxId}/history`);
            if (!response.ok) {
                throw new Error(`Failed to fetch history: ${response.statusText}`);
            }
            const data = await response.json();
            setHistory(data.reverse()); // 显示最新的在顶部
        } catch (err) {
            setError(err.message);
            setHistory([]);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        if (!hookManager) return;

        const handleSandboxSelected = (sandbox) => {
            setActiveSandbox(sandbox);
            fetchHistory(sandbox.id);
        };
        
        // 监听后端推送的更新
        const handleStateUpdated = (data) => {
            // 仅当更新属于当前活动沙盒时才刷新
            if (activeSandbox && data.sandbox_id === activeSandbox.id) {
                fetchHistory(activeSandbox.id);
            }
        };

        hookManager.addImplementation('sandbox.selected', handleSandboxSelected);
        hookManager.addImplementation('state.sandbox.updated', handleStateUpdated);

        return () => {
            hookManager.removeImplementation('sandbox.selected', handleSandboxSelected);
            hookManager.removeImplementation('state.sandbox.updated', handleStateUpdated);
        };

    }, [hookManager, activeSandbox, fetchHistory]);
    
    const renderTrigger = (snapshot) => {
        // ++ 修复：增加对空对象的判断
        if (!snapshot.triggering_input || Object.keys(snapshot.triggering_input).length === 0) {
            return <span className="trigger-empty">Genesis</span>;
        }
        
        const message = snapshot.triggering_input.user_message || 
                        snapshot.triggering_input.user_choice ||
                        JSON.stringify(snapshot.triggering_input);
        
        return <span className="trigger-text">{message}</span>;
    }

    if (!activeSandbox) {
        return <div className="history-feedback">No sandbox selected.</div>;
    }

    if (isLoading) {
        return <div className="history-feedback">Loading history...</div>;
    }
    
    if (error) {
        return <div className="history-feedback error">Error: {error}</div>;
    }

    return (
        <ul className="history-list">
            {history.map((snapshot, index) => (
                <li key={snapshot.id} className="history-item">
                    <div className="history-item-header">
                       {renderTrigger(snapshot)}
                       <span className="history-item-head-tag">{index === 0 ? 'HEAD' : ''}</span>
                    </div>
                </li>
            ))}
        </ul>
    );
}