// plugins/core_goliath/src/context/SandboxContext.jsx 

import React, { createContext, useState, useContext, useCallback } from 'react';

// 1. 更新 Context 的默认值以反映新的 API 和方法
const SandboxContext = createContext({
    sandboxes: [], // 将存储 SandboxListItem 对象
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

    // ✨ 关键修复：把 selectSandbox 的定义移到前面
    const selectSandbox = useCallback((sandbox) => {
        setSelectedSandbox(sandbox);
        if (sandbox) {
            setActiveView('Home');
            console.log(`[SandboxContext] Sandbox selected: ${sandbox.name} (${sandbox.id})`);
        } else {
            console.log(`[SandboxContext] Sandbox deselected.`);
        }
    }, []); // setActiveView 通常不需要作为依赖，因为它是 setState 函数

    const importSandbox = useCallback(async (file) => {
        setLoading(true);
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/sandboxes/import', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to import sandbox');
            }
            const importedSandboxStub = await response.json();
            
            // 刷新列表
            await fetchSandboxes();
            
            // 使用函数式更新来安全地从最新的 state 中查找并选择
            setSandboxes(currentSandboxes => {
                const newSandboxInList = currentSandboxes.find(s => s.id === importedSandboxStub.id);
                if (newSandboxInList) {
                    selectSandbox(newSandboxInList);
                } else {
                    // 如果在列表中找不到（不太可能发生，但作为防御性编程），取消选择以避免不一致的状态
                    selectSandbox(null);
                }
                return currentSandboxes; // 返回未修改的列表
            });

        } catch (error) {
            console.error(error);
            throw error;
        } finally {
            setLoading(false);
        }
    }, [fetchSandboxes, selectSandbox]);// 添加 selectSandbox 到依赖数组


    /**
     * 更新指定沙盒的图标。
     * @param {string} sandboxId - 沙盒的 ID。
     * @param {File} file - 用户选择的新 PNG 文件。
     */
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
                 const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to update icon');
            }
            console.log(`[SandboxContext] Icon for sandbox ${sandboxId} updated.`);
            // 关键：必须重新获取列表以获得新的带版本号的 icon_url
            await fetchSandboxes();
        } catch (error) {
            console.error(error);
            throw error;
        } finally {
            setLoading(false);
        }
    }, [fetchSandboxes]);
    
    /**
     * 更新沙盒名称。
     * (假设后端有 PUT /api/sandboxes/{id} 端点)
     * @param {string} sandboxId 
     * @param {string} newName 
     */
    const updateSandboxName = useCallback(async (sandboxId, newName) => {
        setLoading(true);
        try {
            // 关键修正：使用 PATCH 方法，并确保 URL 是正确的根相对路径
            const response = await fetch(`/api/sandboxes/${sandboxId}`, {
                method: 'PATCH', // 使用 PATCH 更符合语义
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: newName }),
            });
             if (!response.ok) {
                // 后端可能会返回更详细的错误信息
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(errorData.detail || 'Failed to update name');
            }
            console.log(`[SandboxContext] Name for sandbox ${sandboxId} updated.`);
            // 乐观更新：在前端直接修改状态，避免重新请求列表
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



    /**
     * 删除一个沙盒。
     * (假设后端有 DELETE /api/sandboxes/{id} 端点)
     * @param {string} sandboxId 
     */
    const deleteSandbox = useCallback(async (sandboxId) => {
        setLoading(true);
        try {
            const response = await fetch(`/api/sandboxes/${sandboxId}`, {
                method: 'DELETE',
            });
             if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to delete sandbox');
            }
            console.log(`[SandboxContext] Sandbox ${sandboxId} deleted.`);
            // 如果删除的是当前选中的沙盒，则取消选择
            if (selectedSandbox?.id === sandboxId) {
                setSelectedSandbox(null);
            }
            await fetchSandboxes(); // 重新获取列表
        } catch (error) {
            console.error(error);
            throw error;
        } finally {
            setLoading(false);
        }
    }, [selectedSandbox, fetchSandboxes]);


    // 3. 将所有新的和更新后的方法打包到 value 对象中
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

// 自定义 Hook 保持不变
export const useSandbox = () => {
    const context = useContext(SandboxContext);
    if (context === undefined) {
        throw new Error('useSandbox must be used within a SandboxProvider');
    }
    return context;
};