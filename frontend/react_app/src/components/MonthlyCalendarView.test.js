import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom'; // For extended matchers like .toBeInTheDocument()
import MonthlyCalendarView from './MonthlyCalendarView';

describe('MonthlyCalendarView', () => {
  test('renders the current month and year', () => {
    render(<MonthlyCalendarView onDayClick={() => {}} />);
    const currentMonth = new Date().toLocaleString('default', { month: 'long' });
    const currentYear = new Date().getFullYear();
    expect(screen.getByText(`${currentMonth} ${currentYear}`)).toBeInTheDocument();
  });

  test('renders day labels', () => {
    render(<MonthlyCalendarView onDayClick={() => {}} />);
    expect(screen.getByText('Sun')).toBeInTheDocument();
    expect(screen.getByText('Mon')).toBeInTheDocument();
    // ... and so on for all days
    expect(screen.getByText('Sat')).toBeInTheDocument();
  });

  test('calls onDayClick when a day is clicked', () => {
    const mockOnDayClick = jest.fn();
    render(<MonthlyCalendarView onDayClick={mockOnDayClick} />);
    // Click on the 10th day of the month (assuming it's rendered)
    // This is a bit brittle as it depends on the day rendering.
    // A better way might be to find a day with specific text if possible or add test-ids.
    const dayElement = screen.getByText('10'); // Assumes day 10 is visible
    fireEvent.click(dayElement);
    expect(mockOnDayClick).toHaveBeenCalled();
    // We can also check the date argument if needed, but it requires more setup
    // to know exactly which date '10' corresponds to without complex date mocking.
  });

  test('navigates to the previous month', () => {
    render(<MonthlyCalendarView onDayClick={() => {}} />);
    const currentMonth = new Date();
    const prevMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1);
    const prevMonthName = prevMonth.toLocaleString('default', { month: 'long' });
    const prevMonthYear = prevMonth.getFullYear();

    fireEvent.click(screen.getByText('<'));
    expect(screen.getByText(`${prevMonthName} ${prevMonthYear}`)).toBeInTheDocument();
  });

  test('navigates to the next month', () => {
    render(<MonthlyCalendarView onDayClick={() => {}} />);
    const currentMonth = new Date();
    const nextMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1);
    const nextMonthName = nextMonth.toLocaleString('default', { month: 'long' });
    const nextMonthYear = nextMonth.getFullYear();

    fireEvent.click(screen.getByText('>'));
    expect(screen.getByText(`${nextMonthName} ${nextMonthYear}`)).toBeInTheDocument();
  });

  test('navigates to the current month when "Today" is clicked', () => {
    // First, navigate away from the current month
    render(<MonthlyCalendarView onDayClick={() => {}} />);
    fireEvent.click(screen.getByText('>')); // Go to next month

    // Now click "Today"
    fireEvent.click(screen.getByText('Today'));

    const currentMonth = new Date().toLocaleString('default', { month: 'long' });
    const currentYear = new Date().getFullYear();
    expect(screen.getByText(`${currentMonth} ${currentYear}`)).toBeInTheDocument();
  });

  // Placeholder for testing daysWithData - requires more setup or context mocking for API calls
  test('highlights days with data (placeholder test)', () => {
    // This test would ideally mock the useEffect fetch and provide daysWithData
    // then check for the 'has-data' class on specific days.
    // For now, just checking if it renders.
    render(<MonthlyCalendarView onDayClick={() => {}} />);
    // Example: if day 10 has data from the static example in useEffect
    const day10 = screen.getByText('10');
    expect(day10).toHaveClass('has-data'); // This relies on the static example in useEffect
  });
});
