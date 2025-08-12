// plugins/core_llm_config/src/components/Countdown.jsx
import React, { useState, useEffect } from 'react';

export function Countdown({ until }) {
    const [timeLeft, setTimeLeft] = useState(Math.round(until - Date.now() / 1000));

    useEffect(() => {
        if (timeLeft <= 0) return;
        const timer = setInterval(() => {
            const newTimeLeft = Math.round(until - Date.now() / 1000);
            setTimeLeft(newTimeLeft > 0 ? newTimeLeft : 0);
        }, 1000);
        return () => clearInterval(timer);
    }, [timeLeft, until]);

    return timeLeft > 0 ? `~${timeLeft}s` : '可用';
}