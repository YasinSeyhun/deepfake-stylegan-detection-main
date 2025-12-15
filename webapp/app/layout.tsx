import './globals.css';
import { ReactNode } from 'react';

export const metadata = {
  title: 'Deepfake Detection',
  description: 'Modern landing page',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="tr">
      <body className="dark">
        {children}
      </body>
    </html>
  );
} 