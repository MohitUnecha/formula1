'use client';

import { useEffect, useState } from 'react';

export default function DebugPage() {
  const [output, setOutput] = useState<string[]>([]);

  useEffect(() => {
    const test = async () => {
      const logs: string[] = [];

      try {
        // Test 1: Health check
        logs.push('🔍 Test 1: Backend Health Check');
        const healthRes = await fetch('http://localhost:8000/health');
        const healthData = await healthRes.json();
        logs.push(`Status: ${healthRes.status}`, `Data: ${JSON.stringify(healthData)}`);

        // Test 2: Get seasons
        logs.push('\n🔍 Test 2: Get Seasons');
        const seasonsRes = await fetch('http://localhost:8000/api/seasons');
        const seasonsData = await seasonsRes.json();
        logs.push(`Status: ${seasonsRes.status}`, `Count: ${seasonsData.length}`, `Data: ${JSON.stringify(seasonsData)}`);

        // Test 3: Get 2025 events
        logs.push('\n🔍 Test 3: Get 2025 Events');
        const eventsRes = await fetch('http://localhost:8000/api/seasons/2025/events');
        const eventsData = await eventsRes.json();
        logs.push(`Status: ${eventsRes.status}`, `Count: ${eventsData.length}`, `First: ${eventsData[0]?.event_name}`);

        // Test 4: Get drivers
        logs.push('\n🔍 Test 4: Get Drivers');
        const driversRes = await fetch('http://localhost:8000/api/drivers');
        const driversData = await driversRes.json();
        logs.push(`Status: ${driversRes.status}`, `Count: ${driversData.length}`, `First: ${driversData[0]?.first_name} ${driversData[0]?.last_name}`);

        logs.push('\n✅ All API tests passed!');
      } catch (error) {
        logs.push(`\n❌ Error: ${error}`);
      }

      setOutput(logs);
    };

    test();
  }, []);

  return (
    <div className="space-y-6 p-8">
      <div>
        <h1 className="text-3xl font-bold mb-4">🔧 API Debug Page</h1>
        <p className="text-gray-400 mb-6">Testing API connectivity from frontend</p>
      </div>

      <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 font-mono text-sm">
        {output.length === 0 ? (
          <p className="text-gray-400">Loading tests...</p>
        ) : (
          output.map((line, i) => (
            <div key={i} className={line.includes('✅') ? 'text-green-400' : line.includes('❌') ? 'text-red-400' : line.includes('🔍') ? 'text-blue-400' : ''}>
              {line}
            </div>
          ))
        )}
      </div>

      <div className="bg-blue-900/30 border border-blue-700/50 rounded-lg p-6">
        <h3 className="font-bold mb-2">API Base URL:</h3>
        <p className="text-gray-300">{process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}</p>
      </div>
    </div>
  );
}
