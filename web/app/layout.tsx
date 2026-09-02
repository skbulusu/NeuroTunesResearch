import type { Metadata } from 'next'
import { GeistSans } from 'geist/font/sans'
import { GeistMono } from 'geist/font/mono'
import './globals.css'
import { ThemeProvider } from '@/components/theme-provider'

export const metadata: Metadata = {
  metadataBase: new URL('https://netr.ai'),
  title: {
    default: 'NeuroTunes — The open platform for AI music therapy research',
    template: '%s · NeuroTunes by Netr.ai',
  },
  description:
    'NeuroTunes is an open, patent-pending research platform for AI-personalized therapeutic music. Generate, study, and improve therapeutic music with a programmatic API, open code, and a transparent roadmap — for clinicians, researchers, and users.',
  keywords: [
    'music therapy', 'AI music', 'therapeutic music', 'binaural beats', 'RLHF',
    'neurological rehabilitation', 'open research platform', 'NeuroTunes', 'Netr.ai',
  ],
  authors: [{ name: 'Netr.ai' }],
  generator: 'Next.js',
  openGraph: {
    type: 'website',
    url: 'https://netr.ai',
    siteName: 'NeuroTunes by Netr.ai',
    title: 'NeuroTunes — The open platform for AI music therapy research',
    description:
      'Open, patent-pending platform for AI-personalized therapeutic music. Programmatic API, open code, transparent roadmap. For clinicians, researchers, and users.',
    images: [{ url: '/logo.png', width: 1200, height: 630, alt: 'NeuroTunes by Netr.ai' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'NeuroTunes — The open platform for AI music therapy research',
    description:
      'Open, patent-pending platform for AI-personalized therapeutic music. For clinicians, researchers, and users.',
    images: ['/logo.png'],
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <style>{`
html {
  font-family: ${GeistSans.style.fontFamily};
  --font-sans: ${GeistSans.variable};
  --font-mono: ${GeistMono.variable};
}
        `}</style>
      </head>
      <body className="dark">
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem={false}
          disableTransitionOnChange
        >
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}