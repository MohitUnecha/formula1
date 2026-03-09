'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { Menu, X } from 'lucide-react';

const NAV_LINKS = [
  { href: '/', label: 'Home' },
  { href: '/races', label: 'Races' },
  { href: '/drivers', label: 'Drivers' },
  { href: '/constructors', label: 'Constructors' },
  { href: '/analytics', label: 'Analytics' },
  { href: '/compare', label: 'Compare' },
  { href: '/predictions', label: 'Predictions' },
  { href: '/live', label: 'Live Data' },
  { href: '/replay', label: 'Replay' },
  { href: '/about', label: 'About' },
];

export function NavBar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/';
    return pathname.startsWith(href);
  };

  return (
    <nav className="relative sticky top-0 z-50 border-b border-white/[0.05] bg-[#070910]/90 backdrop-blur-2xl">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-red-500/70 to-transparent" />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-14 items-center">
          <div className="flex items-center gap-6">
            <Link href="/" className="flex items-center gap-2 group shrink-0" onClick={() => setMobileOpen(false)}>
              <div className="relative w-10 h-10 flex items-center justify-center">
                <svg viewBox="0 0 40 40" className="w-10 h-10 drop-shadow-[0_0_8px_rgba(225,6,0,0.35)]">
                  <circle cx="20" cy="20" r="18" fill="none" stroke="#E10600" strokeWidth="3" />
                  <path d="M12,14 L28,14 L28,18 L18,18 L18,22 L26,22 L26,26 L12,26 Z" fill="#E10600" />
                  <path d="M29,16 L32,16 L32,30 L29,30 Z M30,14 L31.5,14 L31.5,16 L30,16 Z" fill="white" />
                </svg>
                <div className="absolute inset-0 bg-red-500/20 rounded-full blur-md opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <div>
                <div className="text-[9px] text-gray-500 font-mono tracking-widest uppercase">Every Lap.</div>
              </div>
            </Link>
            {/* Desktop nav */}
            <div className="hidden lg:flex items-center gap-0">
              {NAV_LINKS.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`px-2 py-1.5 rounded-lg text-[11px] font-semibold transition-all relative tracking-wide ${
                    isActive(link.href)
                      ? 'text-white bg-white/12 shadow-[0_0_0_1px_rgba(255,255,255,0.1)]'
                      : 'text-gray-400 hover:text-white hover:bg-white/6'
                  }`}
                >
                  {link.label}
                  {isActive(link.href) && (
                    <span className="absolute -bottom-[9px] left-1/2 -translate-x-1/2 w-6 h-0.5 bg-red-500 rounded-full" />
                  )}
                </Link>
              ))}
            </div>
          </div>

          {/* Mobile hamburger */}
          <button
            className="lg:hidden p-2 rounded-lg hover:bg-white/10 transition-colors"
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            {mobileOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="lg:hidden border-t border-white/5 bg-gray-900/95 backdrop-blur-xl">
          <div className="px-4 py-3 space-y-1">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                className={`block px-4 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                  isActive(link.href)
                    ? 'bg-red-500/10 text-red-400 border-l-2 border-red-500'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>
      )}
    </nav>
  );
}
