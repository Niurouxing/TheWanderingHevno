import React, { useState } from 'react';
import './CreateSandboxView.css';

const defaultGraph = {
  "main": {
    "nodes": [
      {
        "id": "start",
        "run": [
          {
            "runtime": "llm.default",
            "config": {
              "model": "gemini/gemini-1.5-flash",
              "prompt": "You are a helpful assistant. The user said: {{run.triggering_input.user_message}}"
            }
          }
        ]
      }
    ]
  }
};

const defaultState = {
  "player": {
    "name": "Alex",
    "inventory": []
  }
};

export function CreateSandboxView() {
    const hookManager = window.Hevno.services.get('hookManager');

    const [name, setName] = useState('');
    const [graph, setGraph] = useState(JSON.stringify(defaultGraph, null, 2));
    const [state, setState] = useState(JSON.stringify(defaultState, null, 2));
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsSubmitting(true);
        setError(null);

        let parsedGraph, parsedState;

        try {
            parsedGraph = JSON.parse(graph);
            parsedState = JSON.parse(state);
        } catch (jsonError) {
            setError(`Invalid JSON: ${jsonError.message}`);
            setIsSubmitting(false);
            return;
        }

        const payload = {
            name: name,
            graph_collection: parsedGraph,
            initial_state: parsedState,
        };

        try {
            const response = await fetch('/api/sandboxes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });

            const responseData = await response.json();

            if (!response.ok) {
                throw new Error(responseData.detail || `HTTP error! status: ${response.status}`);
            }

            console.log('Sandbox created successfully:', responseData);
            
            if (hookManager) {
                // 触发钩子通知其他部分
                hookManager.trigger('sandbox.created', responseData);
                hookManager.trigger('sandbox.selected', responseData);
            }

        } catch (err) {
            setError(err.message);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="create-sandbox-view">
            <h2>Create New Sandbox</h2>
            <form onSubmit={handleSubmit} className="create-sandbox-form">
                <div className="form-group">
                    <label htmlFor="sandbox-name">Sandbox Name</label>
                    <input
                        id="sandbox-name"
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        required
                        disabled={isSubmitting}
                    />
                </div>
                <div className="form-group">
                    <label htmlFor="sandbox-graph">Graph Collection (JSON)</label>
                    <textarea
                        id="sandbox-graph"
                        value={graph}
                        onChange={(e) => setGraph(e.target.value)}
                        required
                        rows="12"
                        disabled={isSubmitting}
                    />
                </div>
                <div className="form-group">
                    <label htmlFor="sandbox-state">Initial World State (JSON)</label>
                    <textarea
                        id="sandbox-state"
                        value={state}
                        onChange={(e) => setState(e.target.value)}
                        required
                        rows="8"
                        disabled={isSubmitting}
                    />
                </div>

                {error && <div className="form-error">{error}</div>}

                <button type="submit" disabled={isSubmitting}>
                    {isSubmitting ? 'Creating...' : 'Create Sandbox'}
                </button>
            </form>
        </div>
    );
}