// plugins/core_runner_ui/src/context/SandboxStateContext.jsx
import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
// 导入所有需要的 API 函数
import { query, step, revert, getHistory, getSandboxDetails, deleteSnapshot } from '../api';

export const SandboxStateContext = createContext(null);

export function SandboxStateProvider({ sandboxId, services, children }) {
    // 将所有相关状态合并到一个 state 对象中
    const [sandboxState, setSandboxState] = useState({ 
        moment: null, 
        lore: null, 
        definition: null,
        history: [],
        headSnapshotId: null
    });
    const [isLoading, setIsLoading] = useState(true);
    const [isStepping, setIsStepping] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        if (services && !services.has('sandboxStateContext')) {
            console.log('[core_runner_ui] Registering SandboxStateContext service.');
            services.register('sandboxStateContext', SandboxStateContext, 'core_runner_ui');
        }
    }, [services]);

    // 重构 refreshState 来获取所有数据
    const refreshState = useCallback(async (showLoadingSpinner = true) => {
        if (!sandboxId) return;
        if (showLoadingSpinner) setIsLoading(true);
        setError('');
        try {
            // 使用 Promise.all 并行获取所有数据
            const [details, history, queryResults] = await Promise.all([
                getSandboxDetails(sandboxId),
                getHistory(sandboxId),
                query(sandboxId, ['moment', 'lore', 'definition'])
            ]);
            
            setSandboxState({
                ...queryResults,
                history,
                headSnapshotId: details.head_snapshot_id
            });
        } catch (e) {
            setError(`Failed to load sandbox state: ${e.message}`);
            // 如果出错，清空状态以避免显示脏数据
            setSandboxState({ moment: null, lore: null, definition: null, history: [], headSnapshotId: null });
        } finally {
            if (showLoadingSpinner) setIsLoading(false);
        }
    }, [sandboxId]);

    useEffect(() => {
        refreshState();
    }, [refreshState]);

    const performStep = useCallback(async (inputPayload) => {
        if (!sandboxId) return;
        setIsStepping(true);
        setError('');
        try {
            const stepResponse = await step(sandboxId, inputPayload);
            if (stepResponse.status === 'ERROR') throw new Error(stepResponse.error_message);
            // 成功后刷新整个状态
            await refreshState(false);
        } catch (e) {
            setError(e.message);
            // 出错时也刷新一下，以同步到失败前的最后一个状态
            await refreshState(false);
        } finally {
            setIsStepping(false);
        }
    }, [sandboxId, refreshState]);

    // [新增] 封装 revert 操作
    const revertSnapshot = useCallback(async (snapshotId) => {
        if (!sandboxId) return;
        setIsLoading(true);
        setError('');
        try {
            await revert(sandboxId, snapshotId);
            await refreshState(false); // revert 成功后，刷新所有状态
        } catch (e) {
            setError(`Revert failed: ${e.message}`);
            await refreshState(false); // 即使失败也刷新，以防万一
        } finally {
            setIsLoading(false);
        }
    }, [sandboxId, refreshState]);

    // [新增] 封装 delete 操作
    const deleteSnapshotFromHistory = useCallback(async (snapshotId) => {
        if (!sandboxId) return;
        setIsLoading(true);
        setError('');
        try {
            await deleteSnapshot(sandboxId, snapshotId);
            await refreshState(false); // delete 成功后，刷新所有状态
        } catch (e) {
            setError(`Delete failed: ${e.message}`);
        } finally {
            setIsLoading(false);
        }
    }, [sandboxId, refreshState]);


    const value = {
        sandboxId,
        ...sandboxState, // 将 moment, lore, definition, history, headSnapshotId 全部展开
        isLoading,
        isStepping,
        error,
        refreshState,
        performStep,
        revertSnapshot, // 暴露新的方法
        deleteSnapshotFromHistory, // 暴露新的方法
    };

    return (
        <SandboxStateContext.Provider value={value}>
            {children}
        </SandboxStateContext.Provider>
    );
}

export const useSandboxState = () => {
    const context = useContext(SandboxStateContext);
    if (!context) {
        throw new Error('useSandboxState must be used within a SandboxStateProvider');
    }
    return context;
};