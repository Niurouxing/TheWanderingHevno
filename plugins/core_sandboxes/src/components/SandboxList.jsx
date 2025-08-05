import React, { useState, useEffect, useCallback } from 'react';
import './SandboxList.css';

export function SandboxList() {
    const hookManager = window.Hevno.services.get('hookManager');
    // ++ 获取命令服务
    const commandService = window.Hevno.services.get('commandService');

    const [sandboxes, setSandboxes] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedSandboxId, setSelectedSandboxId] = useState(null);

    // ++ 将 fetch 逻辑提取到一个可复用的函数中
    const fetchSandboxes = useCallback(async () => {
        setIsLoading(true);
        try {
            const response = await fetch('/api/sandboxes');
            if (!response.ok) {
                throw new Error(`Failed to fetch sandboxes: ${response.statusText}`);
            }
            const data = await response.json();
            setSandboxes(data);
            setError(null);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    }, []);

    // 初始加载
    useEffect(() => {
        fetchSandboxes();
    }, [fetchSandboxes]);

    // ++ 添加钩子监听器以在创建新沙盒后刷新列表
    useEffect(() => {
        if (!hookManager) return;

        const handleSandboxCreated = () => {
            console.log('[SandboxList] "sandbox.created" hook received. Refreshing list...');
            fetchSandboxes();
        };

        hookManager.addImplementation('sandbox.created', handleSandboxCreated);

        return () => {
            hookManager.removeImplementation('sandbox.created', handleSandboxCreated);
        };
    }, [hookManager, fetchSandboxes]);

    const handleSelectSandbox = (sandbox) => {
        if (!hookManager) {
            console.error("[SandboxList] HookManager not available to trigger 'sandbox.selected'");
            return;
        }
        console.log(`[SandboxList] Selecting sandbox: ${sandbox.name} (${sandbox.id})`);
        setSelectedSandboxId(sandbox.id);
        hookManager.trigger('sandbox.selected', sandbox);
    };

    // ++ 新增：处理创建按钮点击事件
    const handleCreateClick = () => {
        if (commandService) {
            commandService.execute('sandboxes.create');
        } else {
            console.error('[SandboxList] CommandService not available.');
        }
    };

    if (isLoading) {
        return <div className="sandbox-list-feedback">Loading sandboxes...</div>;
    }

    if (error) {
        return <div className="sandbox-list-feedback error">Error: {error}</div>;
    }

    return (
        <div className="sandbox-list-container">
            <ul className="sandbox-list">
                {sandboxes.length === 0 ? (
                    <li className="sandbox-item empty">No sandboxes found.</li>
                ) : (
                    sandboxes.map(sandbox => (
                        <li 
                            key={sandbox.id} 
                            className={`sandbox-item ${selectedSandboxId === sandbox.id ? 'selected' : ''}`}
                            onClick={() => handleSelectSandbox(sandbox)}
                        >
                            <span className="sandbox-name">{sandbox.name}</span>
                        </li>
                    ))
                )}
            </ul>
            <div className="sandbox-actions">
                {/* ++ 连接到命令 */}
                <button className="action-button" title="Create New Sandbox" onClick={handleCreateClick}>+</button>
                <button className="action-button" title="Import Sandbox (Not Implemented)">↑</button>
            </div>
        </div>
    );
}