/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  output: 'standalone',
  
  // API proxy configuration
  async rewrites() {
    const apiBase = process.env.NEXT_PUBLIC_API_URL;
    if (!apiBase || !/^https?:\/\//.test(apiBase)) {
      return [];
    }

    return [
      {
        source: '/api/:path*',
        destination: `${apiBase}/api/:path*`,
      },
    ];
  },
  
  // Image optimization
  images: {
    domains: ['localhost', 'media.formula1.com', 'ui-avatars.com', 'upload.wikimedia.org'],
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'media.formula1.com',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'ui-avatars.com',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'upload.wikimedia.org',
        pathname: '/**',
      },
    ],
  },
  
  // Performance optimizations
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
  },
  
  // Webpack configuration
  webpack: (config) => {
    config.module.rules.push({
      test: /\.node$/,
      use: 'node-loader',
    });
    return config;
  },
};

module.exports = nextConfig;
