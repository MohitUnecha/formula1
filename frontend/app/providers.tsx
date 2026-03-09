'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import api from '@/lib/api';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 1 minute
        refetchOnWindowFocus: false,
      },
    },
  }));

  useEffect(() => {
    const enableClientTrigger = process.env.NEXT_PUBLIC_ENABLE_CLIENT_INGEST_TRIGGER === 'true';
    if (!enableClientTrigger) return;

    let cancelled = false;
    const inFlight = { current: false };

    const startLiveIngest = async () => {
      if (inFlight.current || cancelled) return;
      if (typeof document !== 'undefined' && document.visibilityState !== 'visible') return;

      inFlight.current = true;
      try {
        let season = new Date().getFullYear();
        try {
          const seasons = await api.getSeasons();
          if (Array.isArray(seasons) && seasons.length > 0) {
            season = Math.max(...seasons);
          }
        } catch {
          // Fallback to current year if seasons endpoint is unavailable.
        }

        await api.startLiveIngest(season, 120);
      } catch {
        // Keep this silent for users; page should continue even if backend is unavailable.
      } finally {
        inFlight.current = false;
      }
    };

    startLiveIngest();

    const timer = setInterval(() => {
      if (!cancelled) {
        startLiveIngest();
      }
    }, 120_000);

    const onVisible = () => {
      if (!cancelled) {
        startLiveIngest();
      }
    };

    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', onVisible);
    }

    return () => {
      cancelled = true;
      clearInterval(timer);
      if (typeof document !== 'undefined') {
        document.removeEventListener('visibilitychange', onVisible);
      }
    };
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
