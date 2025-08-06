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
    // 状态保持不变，但其内容结构会改变
    const [sandboxes, setSandboxes] = useState([]);
    const [selectedSandbox, setSelectedSandbox] = useState(null);
    const [activeView, setActiveView] = useState('Home');
    const [loading, setLoading] = useState(false);

    // 2. 实现与新 API 端点交互的函数

    /**
     * 从后端获取所有沙盒列表。
     * 现在获取的是 SandboxListItem 格式。
     */
    const fetchSandboxes = useCallback(async () => {
        setLoading(true);
        console.log('[SandboxContext] Fetching sandboxes list...');
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

    /**
     * 导入一个沙盒 (通过上传一个 .png 文件)。
     * @param {File} file - 用户选择的 PNG 文件。
     * @returns {object} 创建成功后的沙盒对象。
     */
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
            const importedSandbox = await response.json();
            console.log('[SandboxContext] Sandbox imported:', importedSandbox);
            await fetchSandboxes(); // 刷新列表
            return importedSandbox;
        } catch (error) {
            console.error(error);
            throw error;
        } finally {
            setLoading(false);
        }
    }, [fetchSandboxes]);

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
            // 注意：此处假设后端API端点为 PUT /api/sandboxes/{sandboxId}
            // 如果后端实现不同，需要修改此处的 fetch URL 和 body。
            const response = await fetch(`/api/sandboxes/${sandboxId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: newName }),
            });
             if (!response.ok) {
                const errorData = await response.json();
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


    // 选择沙盒的逻辑保持不变
    const selectSandbox = useCallback((sandbox) => {
        // 注意：传入的 sandbox 对象现在是 SandboxListItem 格式
        setSelectedSandbox(sandbox);
        if (sandbox) {
            setActiveView('Home');
            console.log(`[SandboxContext] Sandbox selected: ${sandbox.name} (${sandbox.id})`);
        } else {
             console.log(`[SandboxContext] Sandbox deselected.`);
        }
    }, []);

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