// plugins/core_runner_ui/src/context/SandboxStateContext.jsx
import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { query, step, revert } from '../api'; // 引入核心API

const SandboxStateContext = createContext(null);

export function SandboxStateProvider({ sandboxId, children }) {
    const [sandboxState, setSandboxState] = useState({ moment: null, lore: null, definition: null });
    const [isLoading, setIsLoading] = useState(true);
    const [isStepping, setIsStepping] = useState(false); // 用于区分初次加载和step执行
    const [error, setError] = useState('');

    const refreshState = useCallback(async (showLoadingSpinner = true) => {
        if (!sandboxId) return;
        if (showLoadingSpinner) setIsLoading(true);
        setError('');
        try {
            const results = await query(sandboxId, ['moment', 'lore', 'definition']);
            setSandboxState(results);
        } catch (e) {
            setError(`Failed to load sandbox state: ${e.message}`);
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
        } finally {
            setIsStepping(false);
        }
    }, [sandboxId, refreshState]);

    const value = {
        sandboxId,
        ...sandboxState,
        isLoading,
        isStepping,
        error,
        refreshState,
        performStep,
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