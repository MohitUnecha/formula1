import type { Metadata } from 'next';
import { Rajdhani, Space_Grotesk } from 'next/font/google';
import Link from 'next/link';
import './globals.css';
import { Providers } from './providers';
import { NavBar } from './NavBar';
import { ChatbotPanel } from '@/components/ChatbotPanel';

const headingFont = Rajdhani({ subsets: ['latin'], weight: ['500', '600', '700'] });
const bodyFont = Space_Grotesk({ subsets: ['latin'], weight: ['400', '500', '600', '700'] });

export const metadata: Metadata = {
  title: 'F1 Analytics - Race Predictions & Replay',
  description: 'Advanced Formula 1 race prediction and replay platform powered by machine learning',
  keywords: 'F1, Formula 1, race predictions, analytics, machine learning, replay',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${bodyFont.className} ${headingFont.className}`}>
        <Providers>
          <div className="min-h-screen bg-[#080a0f] text-white">
            {/* Subtle noise-like texture */}
            <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,rgba(15,20,40,1),rgba(8,10,15,1))] pointer-events-none" />
            <div className="relative z-10">
              <NavBar />
              
              <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-8 overflow-x-hidden">
                {children}
              </main>
              
              <footer className="border-t border-white/[0.04] mt-20 py-10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
                  <div className="text-[10px] font-black tracking-[0.3em] text-gray-600 uppercase">
                    &copy; 2026 F1 Analytics Platform &middot; Machine Learning Powered
                  </div>
                </div>
              </footer>

              {/* Crofty AI Chatbot — global floating panel */}
              <ChatbotPanel />
            </div>
          </div>
        </Providers>
      </body>
    </html>
  );
}
