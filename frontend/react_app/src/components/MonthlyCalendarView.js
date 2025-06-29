import React, { useState, useEffect } from 'react';
import './MonthlyCalendarView.css'; // We'll create this basic CSS file too

const MonthlyCalendarView = ({ onDayClick }) => {
    const [currentDate, setCurrentDate] = useState(new Date());
    const [daysWithData, setDaysWithData] = useState({}); // Example: { "2023-10-26": true }

    // TODO: Fetch daysWithData from backend based on current month/year
    useEffect(() => {
        // Placeholder: fetch data for the current month
        // const year = currentDate.getFullYear();
        // const month = currentDate.getMonth() + 1;
        // fetch(`/api/lifeboard/month-data?year=${year}&month=${month}`)
        //   .then(res => res.json())
        //   .then(data => setDaysWithData(data.daysWithData || {}))
        //   .catch(err => console.error("Failed to fetch month data:", err));
        console.log("MonthlyCalendarView: useEffect - fetch data for month (placeholder)");
        // Example static data
        setDaysWithData({
            [`${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, '0')}-10`]: true,
            [`${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, '0')}-15`]: true,
        });
    }, [currentDate]);

    const daysInMonth = (year, month) => {
        return new Date(year, month + 1, 0).getDate();
    };

    const getMonthName = (month) => {
        return new Date(currentDate.getFullYear(), month).toLocaleString('default', { month: 'long' });
    };

    const firstDayOfMonth = (year, month) => {
        return new Date(year, month, 1).getDay(); // 0 (Sun) - 6 (Sat)
    };

    const renderCalendarDays = () => {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        const numDays = daysInMonth(year, month);
        const firstDay = firstDayOfMonth(year, month);
        const days = [];

        // Add empty cells for days before the first day of the month
        for (let i = 0; i < firstDay; i++) {
            days.push(<div key={`empty-start-${i}`} className="calendar-day empty"></div>);
        }

        for (let day = 1; day <= numDays; day++) {
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const hasData = daysWithData[dateStr];
            days.push(
                <div
                    key={day}
                    className={`calendar-day ${hasData ? 'has-data' : ''} ${new Date().toDateString() === new Date(year, month, day).toDateString() ? 'today' : ''}`}
                    onClick={() => onDayClick(new Date(year, month, day))}
                >
                    {day}
                </div>
            );
        }
        return days;
    };

    const goToPreviousMonth = () => {
        setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
    };

    const goToNextMonth = () => {
        setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));
    };

    const goToCurrentMonth = () => {
        setCurrentDate(new Date());
    };

    return (
        <div className="monthly-calendar-view">
            <div className="calendar-header">
                <button onClick={goToPreviousMonth}>&lt;</button>
                <h2>{getMonthName(currentDate.getMonth())} {currentDate.getFullYear()}</h2>
                <button onClick={goToNextMonth}>&gt;</button>
            </div>
            <button onClick={goToCurrentMonth} className="current-month-button">Today</button>
            <div className="calendar-grid">
                <div className="calendar-day-label">Sun</div>
                <div className="calendar-day-label">Mon</div>
                <div className="calendar-day-label">Tue</div>
                <div className="calendar-day-label">Wed</div>
                <div className="calendar-day-label">Thu</div>
                <div className="calendar-day-label">Fri</div>
                <div className="calendar-day-label">Sat</div>
                {renderCalendarDays()}
            </div>
        </div>
    );
};

export default MonthlyCalendarView;
