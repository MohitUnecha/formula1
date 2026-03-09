'use client';

import { useRef, useEffect, useState, useCallback } from 'react';
import { Play, Pause, SkipForward, SkipBack, Settings } from 'lucide-react';

interface DriverPosition {
  code: string;
  position: number;
  x: number;
  y: number;
  speed: number;
  tyre: string;
  tyreAge: number;
  gapToLeader: number;
  teamColor: string;
}

interface ReplayFrame {
  lap: number;
  timeElapsed: number;
  drivers: DriverPosition[];
  trackStatus: string;
}

const normalizeTrackLayout = (raw: any): TrackLayout | null => {
  if (!raw || typeof raw !== 'object') return null;
  const corners = Array.isArray(raw.corners) ? raw.corners : [];
  return {
    circuitKey: raw.circuitKey ?? raw.circuit_key ?? 'default',
    corners,
    width: raw.width ?? 1600,
    height: raw.height ?? 1100,
  };
};

const normalizeFrames = (rawFrames: any[]): ReplayFrame[] => {
  if (!Array.isArray(rawFrames)) return [];
  return rawFrames.map((frame) => ({
    lap: frame.lap,
    timeElapsed: frame.timeElapsed ?? frame.time_elapsed ?? 0,
    trackStatus: frame.trackStatus ?? frame.track_status ?? 'Green',
    drivers: Array.isArray(frame.drivers)
      ? frame.drivers.map((driver: any) => ({
          code: driver.code,
          position: driver.position,
          x: driver.x,
          y: driver.y,
          speed: driver.speed,
          tyre: driver.tyre,
          tyreAge: driver.tyreAge ?? driver.tyre_age ?? 0,
          gapToLeader: driver.gapToLeader ?? driver.gap_to_leader ?? 0,
          teamColor: driver.teamColor ?? driver.team_color ?? '#888888',
        }))
      : [],
  }));
};

interface TrackLayout {
  circuitKey: string;
  corners: Array<{ x: number; y: number }>;
  width: number;
  height: number;
}

export default function TrackCanvas({ sessionId }: { sessionId: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [frames, setFrames] = useState<ReplayFrame[]>([]);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1.0);
  const [trackLayout, setTrackLayout] = useState<TrackLayout | null>(null);
  const animationRef = useRef<number>();

  // Load track layout and frames
  useEffect(() => {
    const loadData = async () => {
      try {
        // Load track metadata
        const metaResponse = await fetch(`/api/replay/${sessionId}/metadata`);
        const metaData = await metaResponse.json();
        setTrackLayout(normalizeTrackLayout(metaData.track_layout ?? metaData.trackLayout));

        // Load replay frames
        const framesResponse = await fetch(`/api/replay/${sessionId}/frames?start_lap=1&end_lap=60&fps=5`);
        const framesData = await framesResponse.json();
        setFrames(normalizeFrames(framesData.frames));
      } catch (error) {
        console.error('Error loading replay data:', error);
      }
    };

    loadData();
  }, [sessionId]);

  // Render current frame
  useEffect(() => {
    if (!canvasRef.current || !trackLayout || frames.length === 0) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw track
    drawTrack(ctx, trackLayout);

    // Draw current frame
    if (frames[currentFrame]) {
      drawFrame(ctx, frames[currentFrame], canvas.width, canvas.height);
    }
  }, [currentFrame, frames, trackLayout]);

  // Animation loop
  useEffect(() => {
    if (!isPlaying) {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      return;
    }

    let lastTime = performance.now();
    const fps = 5 * speed; // Base 5 FPS, scaled by speed
    const frameInterval = 1000 / fps;

    const animate = (currentTime: number) => {
      const deltaTime = currentTime - lastTime;

      if (deltaTime >= frameInterval) {
        lastTime = currentTime - (deltaTime % frameInterval);
        
        setCurrentFrame(prev => {
          if (prev >= frames.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }

      animationRef.current = requestAnimationFrame(animate);
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isPlaying, speed, frames.length]);

  const drawTrack = (ctx: CanvasRenderingContext2D, layout: TrackLayout) => {
    ctx.strokeStyle = '#4B5563';
    ctx.lineWidth = 40;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    // Draw track outline
    ctx.beginPath();
    if (layout.corners.length > 0) {
      ctx.moveTo(layout.corners[0].x, layout.corners[0].y);
      for (let i = 1; i < layout.corners.length; i++) {
        ctx.lineTo(layout.corners[i].x, layout.corners[i].y);
      }
      ctx.closePath();
    }
    ctx.stroke();

    // Draw track center line
    ctx.strokeStyle = '#6B7280';
    ctx.lineWidth = 2;
    ctx.setLineDash([10, 10]);
    ctx.stroke();
    ctx.setLineDash([]);
  };

  const drawFrame = (ctx: CanvasRenderingContext2D, frame: ReplayFrame, width: number, height: number) => {
    // Draw each driver
    frame.drivers.forEach(driver => {
      // Scale coordinates to canvas
      const x = driver.x;
      const y = driver.y;

      // Draw car (circle)
      ctx.fillStyle = driver.teamColor || '#888888';
      ctx.beginPath();
      ctx.arc(x, y, 12, 0, 2 * Math.PI);
      ctx.fill();

      // Draw outline
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Draw position number
      ctx.fillStyle = '#FFFFFF';
      ctx.font = 'bold 10px monospace';
      ctx.textAlign = 'center';
      ctx.fillText(driver.position.toString(), x, y + 4);

      // Draw driver code
      ctx.fillStyle = '#FFFFFF';
      ctx.font = '12px monospace';
      ctx.fillText(driver.code, x + 20, y + 4);

      // Draw gap to leader
      if (driver.gapToLeader > 0) {
        ctx.fillStyle = '#9CA3AF';
        ctx.font = '10px monospace';
        ctx.fillText(`+${driver.gapToLeader.toFixed(1)}s`, x + 20, y + 16);
      }
    });

    // Draw lap counter
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    ctx.fillRect(10, 10, 150, 60);
    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 20px sans-serif';
    ctx.fillText(`Lap ${frame.lap}`, 20, 35);
    ctx.font = '14px sans-serif';
    ctx.fillText(`Time: ${Math.floor(frame.timeElapsed / 60)}:${(frame.timeElapsed % 60).toFixed(0).padStart(2, '0')}`, 20, 55);
  };

  const handlePlayPause = () => {
    setIsPlaying(!isPlaying);
  };

  const handleSkipForward = () => {
    setCurrentFrame(prev => Math.min(prev + 50, frames.length - 1));
  };

  const handleSkipBack = () => {
    setCurrentFrame(prev => Math.max(prev - 50, 0));
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newFrame = parseInt(e.target.value);
    setCurrentFrame(newFrame);
  };

  return (
    <div className="space-y-4">
      {/* Canvas */}
      <div className="relative">
        <canvas
          ref={canvasRef}
          width={1600}
          height={900}
          className="track-canvas w-full"
        />
        
        {/* Loading overlay */}
        {frames.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900/50 rounded-lg">
            <div className="text-center">
              <div className="animate-pulse text-xl">Loading replay data...</div>
            </div>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
        {/* Timeline */}
        <div className="mb-4">
          <input
            type="range"
            min={0}
            max={frames.length - 1}
            value={currentFrame}
            onChange={handleSeek}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
            style={{
              background: `linear-gradient(to right, #EF4444 0%, #EF4444 ${(currentFrame / (frames.length - 1)) * 100}%, #374151 ${(currentFrame / (frames.length - 1)) * 100}%, #374151 100%)`
            }}
          />
          <div className="flex justify-between text-sm text-gray-400 mt-1">
            <span>Frame {currentFrame + 1} / {frames.length}</span>
            <span>
              {frames[currentFrame] ? `Lap ${frames[currentFrame].lap}` : 'Lap 0'}
            </span>
          </div>
        </div>

        {/* Playback controls */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <button
              onClick={handleSkipBack}
              className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition"
              title="Skip back"
            >
              <SkipBack size={20} />
            </button>
            
            <button
              onClick={handlePlayPause}
              className="p-3 bg-red-600 hover:bg-red-700 rounded-lg transition"
              title={isPlaying ? 'Pause' : 'Play'}
            >
              {isPlaying ? <Pause size={24} /> : <Play size={24} />}
            </button>
            
            <button
              onClick={handleSkipForward}
              className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition"
              title="Skip forward"
            >
              <SkipForward size={20} />
            </button>
          </div>

          {/* Speed control */}
          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-400">Speed:</label>
            <select
              value={speed}
              onChange={(e) => setSpeed(parseFloat(e.target.value))}
              className="bg-gray-700 border border-gray-600 rounded px-3 py-1 text-sm"
            >
              <option value={0.25}>0.25x</option>
              <option value={0.5}>0.5x</option>
              <option value={1}>1x</option>
              <option value={2}>2x</option>
              <option value={4}>4x</option>
            </select>
          </div>

          <button className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition">
            <Settings size={20} />
          </button>
        </div>
      </div>

      {/* Driver panel */}
      {frames[currentFrame] && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
          <h3 className="text-lg font-bold mb-3">Current Positions</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {frames[currentFrame].drivers
              .sort((a, b) => a.position - b.position)
              .slice(0, 10)
              .map(driver => (
                <div key={driver.code} className="flex items-center space-x-2 text-sm">
                  <div className="font-bold w-6">{driver.position}</div>
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: driver.teamColor }}
                  />
                  <div className="font-mono">{driver.code}</div>
                  {driver.gapToLeader > 0 && (
                    <div className="text-gray-400 text-xs">+{driver.gapToLeader.toFixed(1)}</div>
                  )}
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
