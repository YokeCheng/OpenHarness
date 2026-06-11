# OpenHarness Web Interface

A web frontend for the OpenHarness CLI project, designed for demonstration purposes.

## Features

- **Financial Hotspot Pipeline**: Generate professional financial analysis articles and infographics
- **Generic Skill Execution**: Execute any OpenHarness skill through a web interface
- **Real-time Progress Updates**: SSE streaming for live execution status
- **Result Download**: Download generated articles and images

## Prerequisites

- Node.js 16+
- npm or yarn
- OpenHarness backend running on http://localhost:8000

## Installation

1. Clone the repository
2. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
3. Install dependencies:
   ```bash
   npm install
   ```

## Development

Start the development server:
```bash
npm run dev
```

The frontend will be available at http://localhost:3000 and will proxy API requests to http://localhost:8000.

## Building for Production

Build the static files:
```bash
npm run build
```

The built files will be in the `dist/` directory and can be served by any static file server.

## Deployment

### Vercel
1. Push to GitHub
2. Import the project in Vercel
3. Deploy!

### Netlify
1. Push to GitHub
2. Create a new site in Netlify
3. Select the repository and deploy!

### GitHub Pages
1. Build the project: `npm run build`
2. Push the `dist/` folder to your GitHub Pages branch

## API Integration

The frontend integrates with the following OpenHarness API endpoints:

- `POST /api/v1/financial-hotspot-pipeline` - Dedicated financial pipeline endpoint
- `POST /api/v1/execute` - Generic skill execution endpoint  
- `POST /api/v1/execute/stream` - SSE streaming endpoint
- `GET /api/v1/health` - Health check endpoint

## Environment Configuration

The frontend uses the following environment variables:

- `VITE_API_BASE_URL` - Base URL for API calls (defaults to `/api` in development, can be set for production)

## Troubleshooting

### CORS Issues
Ensure the OpenHarness backend has CORS enabled for your frontend origin.

### SSE Connection Failures
Verify that the backend supports SSE streaming and that the network connection is stable.

### Missing Results
Check that the backend is properly configured with the necessary API keys for LLM and image generation services.