import React, { useState, useEffect } from 'react';
import './DailyNewspaperView.css';

const DailyNewspaperView = ({ selectedDate, onBackToCalendar }) => {
    const [dailySummary, setDailySummary] = useState('');
    const [limitlessData, setLimitlessData] = useState(null);
    const [beeData, setBeeData] = useState(null);
    const [moodData, setMoodData] = useState(null);
    const [weatherData, setWeatherData] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!selectedDate) return;

        const dateStr = selectedDate.toISOString().split('T')[0];
        setIsLoading(true);
        setError(null);
        setDailySummary('');
        setLimitlessData(null);
        setBeeData(null);
        setMoodData(null);
        setWeatherData(null);

        // TODO: Replace with actual API call to n8n workflow (query_daily_view.json)
        // This workflow should return all data for the day, including the AI summary.
        // For now, using placeholder data and timeout to simulate loading.
        console.log(`Fetching data for ${dateStr}... (placeholder)`);

        // Placeholder for fetching AI Daily Summary
        // fetch(`/api/lifeboard/daily-summary?date=${dateStr}`)
        // .then(res => res.json())
        // .then(data => setDailySummary(data.summary))
        // .catch(err => console.error("Failed to fetch daily summary", err));

        // Actual call to the new n8n workflow for daily summary
        const n8nBaseUrl = process.env.REACT_APP_N8N_BASE_URL || ''; // Fallback to relative if not set
        fetch(`${n8nBaseUrl}/webhook-daily-summary`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date: dateStr, userId: "lifeboard_user" })
        })
        .then(res => {
            if (!res.ok) {
                throw new Error(`HTTP error! status: ${res.status}`);
            }
            return res.json();
        })
        .then(data => {
            if (data.status === "success" && data.summary) {
                setDailySummary(data.summary);
            } else {
                setDailySummary("Could not generate a summary for this day.");
                console.error("Failed to get summary from workflow:", data.message || "Unknown error");
            }
        })
        .catch(err => {
            console.error("Failed to fetch daily summary:", err);
            setDailySummary("Error fetching summary. Please try again later.");
            setError(err.message);
        })
        .finally(() => {
            // Placeholder data for other modules (would ideally come from a single daily data endpoint)
            setLimitlessData({ title: "Limitless Log", content: `Data for Limitless from ${dateStr}. (Placeholder)` });
            setBeeData({ title: "Bee.computer Log", content: `Bee.computer activities for ${dateStr}. (Placeholder)` });
            setMoodData({ title: "Mood", content: "Placeholder Mood Data" });
            setWeatherData({ title: "Weather", content: "Placeholder Weather Data" });
            setIsLoading(false);
        });

    }, [selectedDate]);

    if (!selectedDate) {
        return <div className="daily-newspaper-view-empty">Select a day from the calendar to see details.</div>;
    }

    if (isLoading) {
        return <div className="daily-newspaper-view-loading">Loading data for {selectedDate.toLocaleDateString()}...</div>;
    }

    if (error) {
        return <div className="daily-newspaper-view-error">Error loading data: {error}</div>;
    }

    return (
        <div className="daily-newspaper-view">
            <button onClick={onBackToCalendar} className="back-button">&lt; Back to Calendar</button>
            <h2 className="view-title">Your Day: {selectedDate.toLocaleDateString()}</h2>

            {dailySummary && (
                <div className="module daily-summary-module">
                    <h3>Daily Summary</h3>
                    <p>{dailySummary}</p>
                </div>
            )}

            <div className="modules-grid">
                {limitlessData && (
                    <div className="module limitless-module">
                        <h3>{limitlessData.title}</h3>
                        <p>{limitlessData.content}</p>
                    </div>
                )}
                {beeData && (
                    <div className="module bee-module">
                        <h3>{beeData.title}</h3>
                        <p>{beeData.content}</p>
                    </div>
                )}
                {moodData && (
                    <div className="module mood-module">
                        <h3>{moodData.title}</h3>
                        <p>{moodData.content}</p>
                    </div>
                )}
                 {weatherData && (
                    <div className="module weather-module">
                        <h3>{weatherData.title}</h3>
                        <p>{weatherData.content}</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default DailyNewspaperView;
