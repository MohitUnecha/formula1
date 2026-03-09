'use client';

import { useEffect, useState, useRef, useCallback } from 'react';

interface F1CarAnimationProps {
  pageName?: string;
  onComplete?: () => void;
  durationMs?: number;
}

export function F1CarAnimation({ onComplete, durationMs = 5200 }: F1CarAnimationProps) {
  const [phase, setPhase] = useState<'lights' | 'car' | 'reveal' | 'fade-out' | 'done'>('lights');
  const [litLights, setLitLights] = useState(0);
  const [audioUnlocked, setAudioUnlocked] = useState(false);
  const stableOnComplete = useRef(onComplete);
  stableOnComplete.current = onComplete;
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Attempt to play audio — works if user has interacted or autoplay is allowed
  const tryPlayAudio = useCallback(() => {
    if (!audioRef.current) {
      const audio = new Audio('/lights-out.mp4');
      audio.volume = 0.5;
      audioRef.current = audio;
    }
    const audio = audioRef.current;
    audio.currentTime = 0;
    audio.muted = false;
    audio.play()
      .then(() => setAudioUnlocked(true))
      .catch(() => {
        // If unmuted play fails, try the muted→unmute trick
        audio.muted = true;
        audio.play()
          .then(() => { audio.muted = false; setAudioUnlocked(true); })
          .catch(() => {});
      });
  }, []);

  // On any tap/click/key, unlock audio if it hasn't played yet
  useEffect(() => {
    if (audioUnlocked) return;
    const unlock = () => {
      tryPlayAudio();
    };
    window.addEventListener('click', unlock, { once: true });
    window.addEventListener('touchstart', unlock, { once: true });
    window.addEventListener('keydown', unlock, { once: true });
    return () => {
      window.removeEventListener('click', unlock);
      window.removeEventListener('touchstart', unlock);
      window.removeEventListener('keydown', unlock);
    };
  }, [audioUnlocked, tryPlayAudio]);

  useEffect(() => {
    // Attempt autoplay immediately (works if browser allows it)
    tryPlayAudio();

    const timers: NodeJS.Timeout[] = [];
    for (let i = 1; i <= 5; i++) {
      timers.push(setTimeout(() => setLitLights(i), i * 380));
    }
    timers.push(setTimeout(() => { setLitLights(0); setPhase('car'); }, 2400));
    timers.push(setTimeout(() => setPhase('reveal'), 3900));
    timers.push(setTimeout(() => setPhase('fade-out'), durationMs));
    timers.push(setTimeout(() => {
      setPhase('done');
      stableOnComplete.current?.();
      if (audioRef.current) audioRef.current.pause();
    }, durationMs + 700));

    return () => {
      timers.forEach(clearTimeout);
      if (audioRef.current) audioRef.current.pause();
    };
  }, [durationMs, tryPlayAudio]);

  if (phase === 'done') return null;

  return (
    <div
      className={`fixed inset-0 z-[120] flex items-center justify-center overflow-hidden transition-opacity duration-700 ${
        phase === 'fade-out' ? 'opacity-0' : 'opacity-100'
      }`}
      style={{ background: '#050709' }}
    >
      {/* Ambient glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[80vw] h-[80vh] bg-red-900/8 rounded-full blur-[200px]" />
      </div>

      {/* Subtle pulsing grid lines */}
      <div className="absolute inset-0 pointer-events-none">
        {Array.from({ length: 10 }).map((_, i) => (
          <div
            key={i}
            className="absolute h-[1px] bg-gradient-to-r from-transparent via-red-500/10 to-transparent"
            style={{
              top: `${10 + i * 8}%`, left: 0, right: 0,
              animation: 'bgPulse 3s ease-in-out infinite',
              animationDelay: `${i * 120}ms`,
            }}
          />
        ))}
      </div>

      {/* ── LIGHTS PHASE ── */}
      {phase === 'lights' && (
        <div className="flex flex-col items-center gap-10" style={{ animation: 'fadeInUp 0.4s ease-out forwards' }}>
          <div className="relative flex flex-col items-center gap-2">
            <div className="w-1 h-8 bg-gray-700 rounded-full" />
            <div className="flex gap-3 md:gap-5">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex flex-col items-center gap-1">
                  <div className="w-0.5 h-4 bg-gray-700 rounded-full" />
                  <div
                    className="relative w-10 h-10 md:w-14 md:h-14 rounded-full border-2 flex items-center justify-center"
                    style={{
                      backgroundColor: i < litLights ? '#cc0000' : '#111118',
                      boxShadow: i < litLights
                        ? '0 0 35px rgba(204,0,0,0.9), 0 0 70px rgba(204,0,0,0.5), inset 0 0 20px rgba(255,80,80,0.4)'
                        : 'inset 0 0 10px rgba(0,0,0,0.8)',
                      borderColor: i < litLights ? '#ff2020' : '#2a2a3a',
                      transition: 'all 0.12s ease-out',
                    }}
                  >
                    {i < litLights && (
                      <div className="absolute inset-0 rounded-full animate-ping opacity-20"
                        style={{ background: '#ef4444', animationDuration: '0.8s' }} />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <p className="text-gray-600 text-[10px] tracking-[0.5em] uppercase font-black">
            {litLights === 0 ? 'GET READY' : litLights < 5 ? `LIGHT ${litLights}` : 'LIGHTS OUT'}
          </p>

          {/* Tap-to-audio hint — only when audio hasn't unlocked yet */}
          {!audioUnlocked && (
            <div
              style={{
                animation: 'revealFade 0.6s ease-out 0.8s forwards',
                opacity: 0,
                willChange: 'opacity, transform',
              }}
            >
              <p className="flex items-center gap-2 text-gray-600 text-[9px] md:text-[10px] tracking-[0.4em] uppercase font-medium">
                <span style={{ fontSize: '1.1em' }}>♪</span>
                TAP ANYWHERE TO HEAR AUDIO
              </p>
            </div>
          )}
        </div>
      )}

      {/* ── CAR PHASE ── */}
      {phase === 'car' && (
        <>
          {/* Speed lines */}
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            {Array.from({ length: 28 }).map((_, i) => (
              <div
                key={i}
                className="absolute h-[1px] bg-gradient-to-r from-white/50 via-white/20 to-transparent"
                style={{
                  top: `${5 + i * 3.3}%`,
                  animation: 'speedLine 0.7s linear forwards',
                  animationDelay: `${i * 30}ms`,
                }}
              />
            ))}
          </div>

          {/* Car */}
          <div className="absolute top-1/2 -translate-y-1/2" style={{ animation: 'carFlyBy 1.5s cubic-bezier(0.12,0.85,0.18,1) forwards' }}>
            <svg viewBox="0 0 600 160" className="w-[280px] md:w-[560px] h-auto" fill="none">
              <ellipse cx="18" cy="106" rx="45" ry="13" fill="url(#exGlow)" opacity="0.7" />
              <path d="M18 98 L62 80 L138 74 L193 54 L258 54 L280 70 L422 70 L480 82 L527 91 L550 99 L550 113 L18 113 Z" fill="url(#body)" />
              <path d="M193 54 L236 26 L282 26 L298 54 Z" fill="url(#cockpit)" />
              <rect x="0" y="60" width="30" height="10" rx="2" fill="#c0c4ca" />
              <rect x="2" y="49" width="18" height="10" rx="2" fill="#d0d4d9" />
              <path d="M545 94 L578 88 L578 101 L545 106 Z" fill="#d0d4d9" />
              <rect x="556" y="74" width="32" height="5" rx="1.5" fill="#b8bcc2" />
              <circle cx="120" cy="113" r="29" fill="#0a0a0c" />
              <circle cx="456" cy="113" r="29" fill="#0a0a0c" />
              <circle cx="120" cy="113" r="12" fill="#222232" stroke="#3a3a4a" strokeWidth="1.5" />
              <circle cx="456" cy="113" r="12" fill="#222232" stroke="#3a3a4a" strokeWidth="1.5" />
              {[0,60,120,180,240,300].map(a => (
                <line key={`fw${a}`}
                  x1={120+12*Math.cos(a*Math.PI/180)} y1={113+12*Math.sin(a*Math.PI/180)}
                  x2={120+24*Math.cos(a*Math.PI/180)} y2={113+24*Math.sin(a*Math.PI/180)}
                  stroke="#2a2a3a" strokeWidth="2.5" />
              ))}
              {[0,60,120,180,240,300].map(a => (
                <line key={`rw${a}`}
                  x1={456+12*Math.cos(a*Math.PI/180)} y1={113+12*Math.sin(a*Math.PI/180)}
                  x2={456+24*Math.cos(a*Math.PI/180)} y2={113+24*Math.sin(a*Math.PI/180)}
                  stroke="#2a2a3a" strokeWidth="2.5" />
              ))}
              <rect x="165" y="78" width="225" height="4" rx="2" fill="#e10600" />
              <path d="M266 54 L284 30 L296 30 L280 54 Z" fill="#e10600" />
              <path d="M222 54 Q244 36 266 54" fill="none" stroke="#888" strokeWidth="4" />
              <defs>
                <linearGradient id="body" x1="0" y1="0" x2="600" y2="0">
                  <stop offset="0%" stopColor="#b8bcc4" />
                  <stop offset="45%" stopColor="#e8eaed" />
                  <stop offset="100%" stopColor="#d0d3d8" />
                </linearGradient>
                <linearGradient id="cockpit" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#9098a0" />
                  <stop offset="100%" stopColor="#c8d0d8" />
                </linearGradient>
                <radialGradient id="exGlow" cx="0.5" cy="0.5" r="0.5">
                  <stop offset="0%" stopColor="#e10600" stopOpacity="0.9" />
                  <stop offset="60%" stopColor="#ff6600" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="#e10600" stopOpacity="0" />
                </radialGradient>
              </defs>
            </svg>
            {/* Exhaust fire particles */}
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="absolute rounded-full"
                style={{
                  width: `${6+i*2}px`, height: `${6+i*2}px`,
                  background: i % 2 === 0 ? '#e10600' : '#ff6600',
                  left: '-10px',
                  top: `calc(50% + ${-6 + i * 4}px)`,
                  animation: `exParticle 0.35s ease-out ${i * 70}ms infinite`,
                }} />
            ))}
          </div>
        </>
      )}

      {/* ── REVEAL PHASE — no smoke, no letter-by-letter, just a clean impactful slam ── */}
      {(phase === 'reveal' || phase === 'fade-out') && (
        <div className="relative flex flex-col items-center justify-center text-center px-6">
          {/* Glow behind text */}
          <div className="absolute w-[120vw] h-[60vh] bg-red-700/12 blur-[120px] rounded-full pointer-events-none" />

          {/* EVERY LAP. — slams in */}
          <div style={{ animation: 'revealSlam 0.35s cubic-bezier(0.16,1,0.3,1) forwards', opacity: 0, willChange: 'opacity, transform, filter', transform: 'translateZ(0)' }}>
            <div
              className="text-[13vw] md:text-[11vw] lg:text-[9vw] font-black text-white leading-none tracking-tighter"
              style={{ textShadow: '0 0 80px rgba(225,6,0,0.3)', transform: 'translateZ(0)' }}
            >
              EVERY LAP.
            </div>
          </div>

          {/* Red racing line */}
          <div
            className="h-[3px] bg-gradient-to-r from-transparent via-red-600 to-transparent mt-2 mb-3"
            style={{ width: 0, animation: 'lineExpand 0.5s ease-out 0.25s forwards', willChange: 'width, opacity' }}
          />

          {/* ANALYZED. — fades up */}
          <div style={{ animation: 'revealFade 0.5s ease-out 0.2s forwards', opacity: 0, willChange: 'opacity, transform', transform: 'translateZ(0)' }}>
            <div
              className="text-[5vw] md:text-[4vw] lg:text-[2.8vw] font-black tracking-[0.15em] uppercase"
              style={{ color: '#e10600', letterSpacing: '0.2em', transform: 'translateZ(0)' }}
            >
              ANALYZED.
            </div>
          </div>

          {/* Tagline */}
          <div style={{ animation: 'revealFade 0.5s ease-out 0.45s forwards', opacity: 0, willChange: 'opacity, transform', transform: 'translateZ(0)' }}>
            <p className="mt-4 text-gray-500 text-[2.8vw] md:text-[1.4vw] lg:text-xs tracking-[0.35em] uppercase font-semibold"
               style={{ transform: 'translateZ(0)' }}>
              25 seasons · Machine Learning · Real Telemetry
            </p>
          </div>
        </div>
      )}

      <style jsx>{`
        @keyframes bgPulse {
          0%, 100% { opacity: 0.06; }
          50% { opacity: 0.28; }
        }
        @keyframes fadeInUp {
          0%   { opacity: 0; transform: translateY(20px); }
          100% { opacity: 1; transform: translateY(0); }
        }
        @keyframes carFlyBy {
          0%   { left: -750px; filter: drop-shadow(0 0 0 rgba(225,6,0,0)); }
          25%  { filter: drop-shadow(0 0 30px rgba(225,6,0,0.7)); }
          100% { left: calc(100% + 750px); filter: drop-shadow(0 0 0 rgba(225,6,0,0)); }
        }
        @keyframes speedLine {
          0%   { left: -300px; width: 80px;  opacity: 0; }
          10%  { opacity: 0.6; }
          100% { left: calc(100% + 200px); width: 320px; opacity: 0; }
        }
        @keyframes exParticle {
          0%   { transform: translateX(0)     scale(1);    opacity: 0.9; }
          100% { transform: translateX(-55px) scale(0.15); opacity: 0; }
        }
        @keyframes revealSlam {
          0%   { opacity: 0; transform: scale(1.18) translateY(12px); filter: blur(6px); }
          60%  { opacity: 1; transform: scale(0.97) translateY(-2px); filter: blur(0); }
          100% { opacity: 1; transform: scale(1)    translateY(0);    filter: blur(0); }
        }
        @keyframes revealFade {
          0%   { opacity: 0; transform: translateY(14px); }
          100% { opacity: 1; transform: translateY(0); }
        }
        @keyframes lineExpand {
          0%   { width: 0;    opacity: 0; }
          30%  { opacity: 1; }
          100% { width: 65%; opacity: 1; }
        }
      `}</style>
    </div>
  );
}
