import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import DailyNewspaperView from './DailyNewspaperView';

// Mock timers for useEffect with setTimeout
jest.useFakeTimers();

describe('DailyNewspaperView', () => {
  const mockDate = new Date(2023, 9, 26); // October 26, 2023
  const mockOnBackToCalendar = jest.fn();
  let originalFetch;

  beforeEach(() => {
    originalFetch = global.fetch;
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ status: "success", summary: "Mocked AI Summary for the day." }),
      })
    );
  });

  afterEach(() => {
    global.fetch = originalFetch; // Restore original fetch
    jest.clearAllMocks(); // Clear all mocks including jest.fn() for fetch
  });


  test('renders loading state initially', () => {
    render(<DailyNewspaperView selectedDate={mockDate} onBackToCalendar={mockOnBackToCalendar} />);
    expect(screen.getByText(`Loading data for ${mockDate.toLocaleDateString()}...`)).toBeInTheDocument();
  });

  test('renders data after loading (simulated)', async () => {
    render(<DailyNewspaperView selectedDate={mockDate} onBackToCalendar={mockOnBackToCalendar} />);

    // Wait for the fetch to complete and component to update
    expect(await screen.findByText("Mocked AI Summary for the day.")).toBeInTheDocument();

    expect(screen.getByText(`Your Day: ${mockDate.toLocaleDateString()}`)).toBeInTheDocument();
    expect(screen.getByText('Limitless Log')).toBeInTheDocument();
    expect(screen.getByText('Bee.computer Log')).toBeInTheDocument();
    expect(screen.getByText('Mood')).toBeInTheDocument();
    expect(screen.getByText('Weather')).toBeInTheDocument();
  });

  test('calls onBackToCalendar when back button is clicked', async () => {
    render(<DailyNewspaperView selectedDate={mockDate} onBackToCalendar={mockOnBackToCalendar} />);

    // Wait for loading to complete (summary text appears)
    expect(await screen.findByText("Mocked AI Summary for the day.")).toBeInTheDocument();

    fireEvent.click(screen.getByText('< Back to Calendar'));
    expect(mockOnBackToCalendar).toHaveBeenCalledTimes(1);
  });

  test('renders empty state if no date is selected', () => {
    render(<DailyNewspaperView selectedDate={null} onBackToCalendar={mockOnBackToCalendar} />);
    expect(screen.getByText('Select a day from the calendar to see details.')).toBeInTheDocument();
  });

  // To test error state, you would need to mock the fetch to throw an error
  // For example:
  // test('renders error state if data fetching fails', async () => {
  //   jest.spyOn(global, 'fetch').mockImplementationOnce(() => Promise.reject('API error'));
  //   render(<DailyNewspaperView selectedDate={mockDate} onBackToCalendar={mockOnBackToCalendar} />);
  //   await act(async () => {
  //       jest.runAllTimers(); // For the initial data load attempt
  //   });
  //   // This requires the component to actually set an error message based on a catch block
  //   // The current placeholder doesn't have explicit error state propagation to UI for fetch errors.
  //   // expect(screen.getByText(/Error loading data/)).toBeInTheDocument();
  //   global.fetch.mockRestore();
  // });

});

// Clean up timers and mocks
// afterEach is already defined for clearing mocks.
afterAll(() => {
  jest.useRealTimers();
  // global.fetch is restored in afterEach, so no need to delete here if originalFetch pattern is used.
});
