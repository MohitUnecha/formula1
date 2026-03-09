#!/bin/bash

echo "🏎️  Setting up F1 Analytics Frontend..."

# Check Node.js version
NODE_VERSION=$(node -v | cut -d 'v' -f 2 | cut -d '.' -f 1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Error: Node.js 18+ is required. Current version: $(node -v)"
    exit 1
fi

echo "✅ Node.js version OK: $(node -v)"

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Setup environment
if [ ! -f .env.local ]; then
    echo "📝 Creating .env.local from .env.example..."
    cp .env.example .env.local
    echo "⚠️  Please edit .env.local with your backend API URL"
else
    echo "✅ .env.local already exists"
fi

# Type check
echo "🔍 Running TypeScript type check..."
npm run type-check

if [ $? -eq 0 ]; then
    echo "✅ Type check passed"
else
    echo "⚠️  Type check failed - please review errors"
fi

echo ""
echo "🎉 Frontend setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env.local with your backend API URL"
echo "  2. Start development server: npm run dev"
echo "  3. Open http://localhost:3000"
echo ""
