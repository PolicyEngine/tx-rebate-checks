import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import PolicyOverview from '../components/PolicyOverview';

describe('PolicyOverview', () => {
  it('renders the proposal heading', () => {
    render(<PolicyOverview />);
    expect(
      screen.getByText('The proposed Texas $1,500 rebate checks'),
    ).toBeInTheDocument();
  });

  it('focuses the overview on the proposal itself', () => {
    render(<PolicyOverview />);
    expect(screen.getByText('The proposal')).toBeInTheDocument();
    // Cost context lives on the Statewide impact tab, not the overview.
    expect(screen.queryByText('Cost')).not.toBeInTheDocument();
  });

  it('states the eligibility terms', () => {
    render(<PolicyOverview />);
    expect(
      screen.getByText(/one check per household with no income limit/),
    ).toBeInTheDocument();
  });

  it('shows sources links', () => {
    render(<PolicyOverview />);
    expect(
      screen.getByRole('link', {
        name: /Texas Comptroller — Economic Stabilization Fund/,
      }),
    ).toBeInTheDocument();
  });
});
