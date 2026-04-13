import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import UploadDialog from './UploadDialog';

describe('UploadDialog', () => {
  it('shows file picker CTA and disabled submit without file', () => {
    render(<UploadDialog open onClose={() => {}} onUploaded={() => {}} />);

    expect(screen.getByText('Upload Document')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Upload' })).toBeDisabled();
  });
});
