// plugins/core_goliath/src/context/SandboxContext.jsx 

import React, { createContext, useState, useContext, useCallback } from 'react';

const SandboxContext = createContext({
    sandboxes: [],
    selectedSandbox: null,
    activeView: 'Home',
    loading: false,
    fetchSandboxes: async () => {},
    selectSandbox: () => {},
    importSandbox: async (file) => {},
    updateSandboxIcon: async (sandboxId, file) => {},
    updateSandboxName: async (sandboxId, newName) => {},
    deleteSandbox: async (sandboxId) => {},
    setActiveView: () => {},
});

export const SandboxProvider = ({ children }) => {
    const [sandboxes, setSandboxes] = useState([]);
    const [selectedSandbox, setSelectedSandbox] = useState(null);
    const [activeView, setActiveView] = useState('Home');
    const [loading, setLoading] = useState(false);

    const fetchSandboxes = useCallback(async () => {
        setLoading(true);
        try {
            const response = await fetch('/api/sandboxes');
            if (!response.ok) {
                throw new Error(`Failed to fetch sandboxes: ${response.statusText}`);
            }
            const data = await response.json();
            setSandboxes(data);
            console.log('[SandboxContext] Sandboxes list loaded:', data);
        } catch (error) {
            console.error(error);
            setSandboxes([]);
        } finally {
            setLoading(false);
        }
    }, []);
    
    const selectSandbox = useCallback((sandbox) => {
        setSelectedSandbox(sandbox);
        if (sandbox) {
            setActiveView('Home');
            console.log(`[SandboxContext] Sandbox selected: ${sandbox.name} (${sandbox.id})`);
        } else {
             // 当没有沙盒被选择时，回到欢迎界面
            setActiveView('Welcome');
            console.log(`[SandboxContext] Sandbox deselected.`);
        }
    }, []);

    const importSandbox = useCallback(async (file) => {
        setLoading(true);
        const formData = new FormData();
        formData.append('file', file);

        try {
            // ==========================================================
            // 关键修复 #1: API端点应为 /api/sandboxes:import，使用冒号
            // ==========================================================
            const response = await fetch('/api/sandboxes:import', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Failed to import sandbox' }));
                throw new Error(errorData.detail || `Server responded with ${response.status}`);
            }
            
            const importedSandbox = await response.json();
            
            // ====================================================================
            // 关键修复 #2: 优化选择逻辑，直接在此处获取新列表以避免竞态条件
            // ====================================================================
            // 重新获取完整的沙盒列表
            const listResponse = await fetch('/api/sandboxes');
            const newSandboxesList = await listResponse.json();
            setSandboxes(newSandboxesList); // 更新全局状态

            // 从刚刚获取的新列表中找到我们导入的那个
            const newSandboxInList = newSandboxesList.find(s => s.id === importedSandbox.id);
            if (newSandboxInList) {
                selectSandbox(newSandboxInList); // 设为当前选中项
            } else {
                // 如果找不到（理论上不应该发生），则刷新列表并取消选择
                selectSandbox(null);
            }

        } catch (error) {
            console.error(error);
            throw error; // 抛出错误，让UI组件可以捕获并显示
        } finally {
            setLoading(false);
        }
    }, [selectSandbox]); // 依赖 selectSandbox，因为我们在函数内部调用了它


    const updateSandboxIcon = useCallback(async (sandboxId, file) => {
        setLoading(true);
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch(`/api/sandboxes/${sandboxId}/icon`, {
                method: 'POST',
                body: formData,
            });
            if (!response.ok) {
                 const errorData = await response.json().catch(() => ({ detail: 'Failed to update icon' }));
                throw new Error(errorData.detail);
            }
            console.log(`[SandboxContext] Icon for sandbox ${sandboxId} updated.`);
            await fetchSandboxes();
        } catch (error) {
            console.error(error);
            throw error;
        } finally {
            setLoading(false);
        }
    }, [fetchSandboxes]);
    
    const updateSandboxName = useCallback(async (sandboxId, newName) => {
        setLoading(true);
        try {
            const response = await fetch(`/api/sandboxes/${sandboxId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: newName }),
            });
             if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(errorData.detail || 'Failed to update name');
            }
            console.log(`[SandboxContext] Name for sandbox ${sandboxId} updated.`);
            setSandboxes(prev => 
                prev.map(s => s.id === sandboxId ? { ...s, name: newName } : s)
            );
            if (selectedSandbox?.id === sandboxId) {
                setSelectedSandbox(prev => prev ? { ...prev, name: newName } : null);
            }
        } catch (error) {
            console.error(error);
            throw error;
        } finally {
            setLoading(false);
        }
    }, [selectedSandbox]);



    const deleteSandbox = useCallback(async (sandboxId) => {
        setLoading(true);
        try {
            const response = await fetch(`/api/sandboxes/${sandboxId}`, {
                method: 'DELETE',
            });
             if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Failed to delete sandbox' }));
                throw new Error(errorData.detail);
            }
            console.log(`[SandboxContext] Sandbox ${sandboxId} deleted.`);
            if (selectedSandbox?.id === sandboxId) {
                selectSandbox(null);
            }
            await fetchSandboxes();
        } catch (error) {
            console.error(error);
            throw error;
        } finally {
            setLoading(false);
        }
    }, [selectedSandbox, fetchSandboxes, selectSandbox]);


    const value = {
        sandboxes,
        selectedSandbox,
        activeView,
        loading,
        fetchSandboxes,
        selectSandbox,
        importSandbox,
        updateSandboxIcon,
        updateSandboxName,
        deleteSandbox,
        setActiveView,
    };

    return (
        <SandboxContext.Provider value={value}>
            {children}
        </SandboxContext.Provider>
    );
};

export const useSandbox = () => {
    const context = useContext(SandboxContext);
    if (context === undefined) {
        throw new Error('useSandbox must be used within a SandboxProvider');
    }
    return context;
};