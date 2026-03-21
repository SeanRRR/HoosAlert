import React from 'react';
import { render, screen } from '@testing-library/react';
import App from '../src/App';

test('renders hello message', () => {
  render(<App />);
  const heading = screen.getByText(/Hoos Alert Prototype/i);
  expect(heading).toBeInTheDocument();
});