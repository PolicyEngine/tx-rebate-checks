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

  it('displays the two summary cards', () => {
    render(<PolicyOverview />);
    expect(screen.getByText('The proposal')).toBeInTheDocument();
    expect(screen.getByText('Cost')).toBeInTheDocument();
  });

  it('states the eligibility assumption', () => {
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
