import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Attribution MVP - Multi-Segment Partner Attribution Platform',
  description: 'Automatically track partner contributions, calculate revenue splits, and manage attribution with confidence. Built for B2B teams managing complex partner ecosystems.',
  keywords: 'partner attribution, revenue attribution, B2B attribution, partner management, revenue splits',
  openGraph: {
    title: 'Attribution MVP - Multi-Segment Partner Attribution Platform',
    description: 'Automatically track partner contributions, calculate revenue splits, and manage attribution with confidence.',
    type: 'website',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  )
}
