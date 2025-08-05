import React, { useState, useEffect, useRef, useCallback } from 'react';
import './RunnerView.css';

export function RunnerView({ sandbox }) {
    const hookManager = window.Hevno.services.get('hookManager');
    
    const [history, setHistory] = useState([]);
    const [userInput, setUserInput] = useState('');
    const [isStepping, setIsStepping] = useState(false);
    const [error, setError] = useState(null);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [history]);

    // ++ 将 fetch 逻辑提取到 useCallback 中
    const fetchHistory = useCallback(async () => {
        if (!sandbox?.id) return;
        setIsStepping(true); // 使用 isStepping 作为加载状态
        try {
            const response = await fetch(`/api/sandboxes/${sandbox.id}/history`);
            if (!response.ok) throw new Error("Failed to load history.");
            const data = await response.json();
            setHistory(data);
            setError(null);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsStepping(false);
        }
    }, [sandbox.id]);

    useEffect(() => {
        // 初始加载
        fetchHistory();

        const handleStateUpdated = (data) => {
            if (data.sandbox_id === sandbox.id) {
                console.log('[RunnerView] state.sandbox.updated hook received. Refetching history.');
                // ++ 修复：重新获取整个历史记录以确保同步
                fetchHistory();
            }
        };

        if (hookManager) {
            hookManager.addImplementation('state.sandbox.updated', handleStateUpdated);
        }

        return () => {
            if (hookManager) {
                hookManager.removeImplementation('state.sandbox.updated', handleStateUpdated);
            }
        };
    }, [sandbox.id, hookManager, fetchHistory]);

    const handleStep = async (e) => {
        e.preventDefault();
        if (!userInput.trim() || isStepping) return;

        setIsStepping(true);
        setError(null);
        const currentInput = userInput;
        setUserInput(''); // 立即清空输入框，提供更好的用户体验

        try {
            const response = await fetch(`/api/sandboxes/${sandbox.id}/step`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_message: currentInput }),
            });
            
            const responseData = await response.json();
            
            if (!response.ok) {
                throw new Error(responseData.detail || "Failed to execute step.");
            }
            
            // 成功后，我们不再做任何事，等待 state.sandbox.updated 钩子来更新UI
            // 这确保了UI状态总是由后端推送的“事实来源”驱动

        } catch (err) {
            setError(err.message);
            setUserInput(currentInput); // 如果失败，恢复用户的输入
        } finally {
            // isStepping 会在 fetchHistory 完成时设置为 false
        }
    };

    const renderOutput = (snapshot) => {
        if (!snapshot.run_output) return null;
        const text = snapshot.run_output.dialogue_node?.llm_output ||
                     snapshot.run_output.llm_output ||
                     JSON.stringify(snapshot.run_output);
        return <div className="message bot-message">{text}</div>;
    }
    
    const renderInput = (snapshot) => {
        if (!snapshot.triggering_input?.user_message) return null;
        return <div className="message user-message">{snapshot.triggering_input.user_message}</div>;
    }

    return (
        <div className="runner-view">
            <div className="runner-header">
                <h3>{sandbox.name}</h3>
            </div>
            <div className="runner-messages">
                {history.map(snapshot => (
                   <React.Fragment key={snapshot.id}>
                       {renderInput(snapshot)}
                       {renderOutput(snapshot)}
                   </React.Fragment>
                ))}
                <div ref={messagesEndRef} />
            </div>
            <div className="runner-input-area">
                <form onSubmit={handleStep}>
                    <input
                        type="text"
                        value={userInput}
                        onChange={(e) => setUserInput(e.target.value)}
                        placeholder="Type your message..."
                        disabled={isStepping}
                        autoFocus
                    />
                    <button type="submit" disabled={isStepping}>
                        {isStepping ? '...' : 'Send'}
                    </button>
                </form>
                {error && <div className="runner-error">{error}</div>}
            </div>
        </div>
    );
}