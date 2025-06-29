import { render, screen, fireEvent, act } from '@testing-library/react'; // Added act
import '@testing-library/jest-dom';
import App from './App';

// It's good practice to mock child components that are complex or make API calls,
// if you only want to test the App component's logic.
// However, for these integration-style tests of App, we'll let them render.
// jest.mock('./components/MonthlyCalendarView', () => () => <div data-testid="monthly-calendar-view">MonthlyCalendarView</div>);
// jest.mock('./components/DailyNewspaperView', () => ({selectedDate, onBackToCalendar}) => <div data-testid="daily-newspaper-view">DailyNewspaperView for {selectedDate.toISOString()} <button onClick={onBackToCalendar}>Back</button></div>);
// jest.mock('./components/ChatWidget', () => () => <div data-testid="chat-widget">ChatWidget</div>);


describe('App Component', () => {
  let originalFetch;

  beforeEach(() => {
    originalFetch = global.fetch;
    // Default mock for fetch, can be overridden in specific tests if needed
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ status: "success", summary: "Mocked Summary", reply: "Mocked Reply" }),
      })
    );
  });

  afterEach(() => {
    global.fetch = originalFetch;
    jest.clearAllMocks();
  });

  test('renders Lifeboard MVP header', () => {
    render(<App />);
    const headerElement = screen.getByText(/Lifeboard MVP/i);
    expect(headerElement).toBeInTheDocument();
  });

  test('renders MonthlyCalendarView by default', () => {
    render(<App />);
    const currentMonth = new Date().toLocaleString('default', { month: 'long' });
    const currentYear = new Date().getFullYear();
    // Check for an element unique to MonthlyCalendarView, like the month/year display
    // Combining them as they appear in an H2: "Month Year"
    expect(screen.getByText(`${currentMonth} ${currentYear}`)).toBeInTheDocument();
  });

  // No longer skipping, will attempt to make it pass with proper fetch mocking and act
  test('switches to DailyNewspaperView on day click and back to calendar', async () => {
    render(<App />);

    // Day 10 is used in MonthlyCalendarView's static data, ensure it's clickable
    const dayElement = screen.getByText((content, element) => {
        return element.tagName.toLowerCase() === 'div' &&
               element.classList.contains('calendar-day') &&
               content === '10';
    });
    expect(dayElement).toBeInTheDocument();

    jest.useFakeTimers(); // Use fake timers for operations involving timeouts

    fireEvent.click(dayElement); // This click causes DailyNewspaperView to mount and start its timer

    // Expect the loading state immediately after click
    expect(screen.getByText(/Loading data for/i)).toBeInTheDocument();

    await act(async () => {
      jest.advanceTimersByTime(1001);
      await Promise.resolve();
    });

    // Now the content should be there.
    expect(screen.getByText(/Your Day:/i)).toBeInTheDocument();

    // Click the back button
    fireEvent.click(screen.getByText('< Back to Calendar'));

    jest.useRealTimers(); // Clean up fake timers

    // Should be back to MonthlyCalendarView
    const currentMonth = new Date().toLocaleString('default', { month: 'long' });
    const currentYear = new Date().getFullYear();
    // The MonthlyCalendarView header displays "Month Year"
    expect(screen.getByText(`${currentMonth} ${currentYear}`)).toBeInTheDocument();
  });

  test('renders ChatWidget', () => {
    render(<App />);
    // Check for the initial button text of ChatWidget
    expect(screen.getByText(/Chat with Life AI/i)).toBeInTheDocument();
  });
});
