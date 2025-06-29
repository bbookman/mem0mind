import React, { useState } from 'react';
import './App.css';
import MonthlyCalendarView from './components/MonthlyCalendarView';
import DailyNewspaperView from './components/DailyNewspaperView';
import ChatWidget from './components/ChatWidget';

function App() {
  const [currentView, setCurrentView] = useState('calendar'); // 'calendar' or 'daily'
  const [selectedDate, setSelectedDate] = useState(null);

  const handleDayClick = (date) => {
    setSelectedDate(date);
    setCurrentView('daily');
  };

  const handleBackToCalendar = () => {
    setCurrentView('calendar');
    setSelectedDate(null);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Lifeboard MVP</h1>
      </header>
      <main className="App-main">
        {currentView === 'calendar' && (
          <MonthlyCalendarView onDayClick={handleDayClick} />
        )}
        {currentView === 'daily' && selectedDate && (
          <DailyNewspaperView
            selectedDate={selectedDate}
            onBackToCalendar={handleBackToCalendar}
          />
        )}
      </main>
      <ChatWidget />
      <footer className="App-footer">
        <p>&copy; {new Date().getFullYear()} Lifeboard Project</p>
      </footer>
    </div>
  );
}

export default App;
