// plugins/core_goliath/src/context/SandboxContext.jsx

import React, { createContext, useState, useContext, useCallback } from 'react';

// 1. 创建 Context 对象
// 我们提供一个默认值，以便在没有Provider的情况下进行测试或获得更好的自动完成。
const SandboxContext = createContext({
    sandboxes: [],
    selectedSandbox: null,
    activeView: 'Home',
    loading: false,
    fetchSandboxes: async () => {},
    selectSandbox: () => {},
    createSandbox: async () => {},
    setActiveView: () => {},
});

/**
 * 这是我们的 Provider 组件。它将包含所有的状态和逻辑，
 * 并通过 Context 将它们提供给所有子组件。
 */
export const SandboxProvider = ({ children }) => {
    // 2. 定义所有需要全局管理的状态
    const [sandboxes, setSandboxes] = useState([]);
    const [selectedSandbox, setSelectedSandbox] = useState(null);
    const [activeView, setActiveView] = useState('Home');
    const [loading, setLoading] = useState(false);

    // 3. 定义与后端交互的函数
    // 使用 useCallback 来优化性能，防止函数在每次渲染时都重新创建。

    /**
     * 从后端获取所有沙盒列表。
     */
    const fetchSandboxes = useCallback(async () => {
        setLoading(true);
        console.log('[SandboxContext] Fetching sandboxes...');
        try {
            const response = await fetch('/api/sandboxes');
            if (!response.ok) {
                throw new Error(`Failed to fetch sandboxes: ${response.statusText}`);
            }
            const data = await response.json();
            setSandboxes(data);
            console.log('[SandboxContext] Sandboxes loaded:', data);
        } catch (error) {
            console.error(error);
            setSandboxes([]); // 出错时清空
        } finally {
            setLoading(false);
        }
    }, []);

    /**
     * 创建一个新的沙盒。
     * @param {object} newSandboxData - 符合后端API要求的沙盒数据。
     * @returns {object} 创建成功后的沙盒对象。
     */
    const createSandbox = useCallback(async (newSandboxData) => {
        setLoading(true);
        try {
            const response = await fetch('/api/sandboxes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newSandboxData),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to create sandbox');
            }
            
            const createdSandbox = await response.json();
            console.log('[SandboxContext] Sandbox created:', createdSandbox);

            // --- 关键修改 ---
            // 创建成功后，立即刷新整个列表
            await fetchSandboxes();
            // --- 结束修改 ---

            return createdSandbox; // 仍然返回新创建的沙盒，以便调用方可以立即选中它

        } catch (error) {
            console.error(error);
            throw error;
        } finally {
            setLoading(false);
        }
    }, [fetchSandboxes]);

    /**
     * 设置当前选中的沙盒，并重置视图到 'Home'。
     * @param {object | null} sandbox - 要选择的沙盒对象，或 null 来取消选择。
     */
    const selectSandbox = useCallback((sandbox) => {
        setSelectedSandbox(sandbox);
        if (sandbox) {
            setActiveView('Home'); // 每次选择新沙盒时，默认显示 Home 视图
            console.log(`[SandboxContext] Sandbox selected: ${sandbox.name} (${sandbox.id})`);
        } else {
             console.log(`[SandboxContext] Sandbox deselected.`);
        }
    }, []);


    // 4. 将所有状态和函数打包成一个 value 对象
    const value = {
        sandboxes,
        selectedSandbox,
        activeView,
        loading,
        fetchSandboxes,
        selectSandbox,
        createSandbox,
        setActiveView,
    };

    // 5. 返回 Provider，并将 value 传递下去
    return (
        <SandboxContext.Provider value={value}>
            {children}
        </SandboxContext.Provider>
    );
};

/**
 * 创建一个自定义 Hook，以简化在其他组件中对 Context 的使用。
 * 这是推荐的最佳实践。
 */
export const useSandbox = () => {
    const context = useContext(SandboxContext);
    if (context === undefined) {
        throw new Error('useSandbox must be used within a SandboxProvider');
    }
    return context;
};