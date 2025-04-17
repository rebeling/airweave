# Airweave Frontend

## Overview

The Airweave frontend is a React/TypeScript application that provides the UI for the Airweave platform. Airweave is an open-source platform that makes any app searchable for your agent by syncing data from various sources into vector and graph databases with minimal configuration.

## Technology Stack

- **Framework**: React with TypeScript
- **UI Components**: ShadCN UI components with Radix UI
- **Styling**: Tailwind CSS
- **Icons**: Lucide Icons
- **Build Tool**: Vite
- **Package Manager**: npm/bun

## Getting Started

### Prerequisites

- Node.js (v18+)
- npm or bun

### Installation

```sh
# Clone the repository
git clone https://github.com/airweave-ai/airweave

# Navigate to the frontend directory
cd airweave/frontend

# Install dependencies
npm install
# or
bun install
```

### Development

```sh
# Start the development server
npm run dev
# or
bun run dev
```

This will start the development server at `http://localhost:5173` (or another port if 5173 is in use).

## Project Structure

```
frontend/
├── src/               # Source code
│   ├── components/    # React components
│   ├── config/        # Configuration
│   ├── hooks/         # React hooks
│   ├── lib/           # Utility libraries
│   ├── pages/         # Page components
│   ├── styles/        # CSS styles
│   └── types/         # TypeScript type definitions
├── public/            # Static assets
└── ...
```

## API Integration

The frontend communicates with the backend API using the `apiClient`. When making API calls, use relative paths without prefixing with `api/v1`. The API client will handle the correct URL construction.

```tsx
// Example API call
import { apiClient } from '@/lib/api';

// Correct
const response = await apiClient.get('/sources');

// Incorrect
const response = await apiClient.get('api/v1/sources');
```

## Building for Production

```sh
# Build the frontend
npm run build
# or
bun run build
```

The build artifacts will be stored in the `dist/` directory.

## Contributing

When contributing to the frontend:

1. Follow the established patterns in the codebase
2. Use existing components where possible
3. Follow the TypeScript typing conventions
4. Test your changes before submitting a PR

## Docker

A Dockerfile is included for containerizing the frontend. Build and run with:

```sh
docker build -t airweave-frontend .
docker run -p 8080:80 airweave-frontend
```
