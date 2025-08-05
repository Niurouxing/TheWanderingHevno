import React, { useState, useEffect } from 'react';

export function SandboxIndicator() {
    const [activeSandbox, setActiveSandbox] = useState(null);
    const hookManager = window.Hevno.services.get('hookManager');

    useEffect(() => {
        if (!hookManager) return;
        
        // 假设未来会有一个 'sandbox.selected' 或 'sandbox.created' 钩子
        const handleSandboxChange = (sandbox) => {
            setActiveSandbox(sandbox);
        };
        
        hookManager.addImplementation('sandbox.selected', handleSandboxChange);

        return () => {
            hookManager.removeImplementation('sandbox.selected', handleSandboxChange);
        };
    }, [hookManager]);

    const style = {
        display: 'flex',
        alignItems: 'center',
        gap: '5px',
        fontSize: '0.9em',
        cursor: 'default'
    };
    
    return (
        <div style={style} title="Active Sandbox">
            <span>📦</span>
            <span>{activeSandbox ? activeSandbox.name : 'No Sandbox'}</span>
        </div>
    );
}