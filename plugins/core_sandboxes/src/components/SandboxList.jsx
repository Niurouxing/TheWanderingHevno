import React, { useState, useEffect } from 'react';
import './SandboxList.css'; // 导入样式

export function SandboxList() {
    // 遵循黄金规则二：在 UI 组件中使用服务定位器
    const hookManager = window.Hevno.services.get('hookManager');

    // 组件状态
    const [sandboxes, setSandboxes] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedSandboxId, setSelectedSandboxId] = useState(null);

    // 获取沙盒列表的 effect
    useEffect(() => {
        async function fetchSandboxes() {
            try {
                const response = await fetch('/api/sandboxes');
                if (!response.ok) {
                    throw new Error(`Failed to fetch sandboxes: ${response.statusText}`);
                }
                const data = await response.json();
                setSandboxes(data);
            } catch (err) {
                setError(err.message);
            } finally {
                setIsLoading(false);
            }
        }
        fetchSandboxes();
    }, []);

    // 处理沙盒选择的函数
    const handleSelectSandbox = (sandbox) => {
        if (!hookManager) {
            console.error("[SandboxList] HookManager not available to trigger 'sandbox.selected'");
            return;
        }
        console.log(`[SandboxList] Selecting sandbox: ${sandbox.name} (${sandbox.id})`);
        setSelectedSandboxId(sandbox.id);
        // 触发全局钩子，通知其他插件（如 core_history, core_runner）
        hookManager.trigger('sandbox.selected', sandbox);
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
                <button className="action-button" title="Create New Sandbox">+</button>
                <button className="action-button" title="Import Sandbox">↑</button>
            </div>
        </div>
    );
}