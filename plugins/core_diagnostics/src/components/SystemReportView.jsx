import React, { useState, useEffect } from 'react';

export function SystemReportView() {
    const [report, setReport] = useState(null);
    const [error, setError] = useState(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        async function fetchReport() {
            try {
                const response = await fetch('/api/system/report');
                if (!response.ok) {
                    throw new Error(`Failed to fetch system report: ${response.statusText}`);
                }
                const data = await response.json();
                setReport(data);
            } catch (err) {
                setError(err.message);
            } finally {
                setIsLoading(false);
            }
        }
        fetchReport();
    }, []);
    
    const preStyle = {
        backgroundColor: '#1a1a1a',
        border: '1px solid #333',
        padding: '1rem',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-all',
        height: 'calc(100% - 2rem)',
        overflowY: 'auto',
        margin: 0,
    };

    if (isLoading) return <div style={{padding: '1rem'}}>Loading system report...</div>;
    if (error) return <div style={{padding: '1rem', color: 'red'}}>Error: {error}</div>;

    return (
        <pre style={preStyle}>
            {JSON.stringify(report, null, 2)}
        </pre>
    );
}