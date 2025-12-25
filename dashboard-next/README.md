# CodeWeaver SRE Console - Next.js

Professional SRE monitoring dashboard built with Next.js 14, TypeScript, and modern React patterns.

## Features

- **Real-time Monitoring**: Auto-refreshing system health, metrics, and logs
- **Incident Management**: Visual incident response workflow with approve/reject actions
- **Dark Theme**: Professional Grafana-style UI
- **TypeScript**: Full type safety
- **Responsive**: Clean grid layout with sidebar and terminal view

## Getting Started

### Installation

```bash
cd dashboard-next
npm install
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### Production Build

```bash
npm run build
npm start
```

## Architecture

- **Next.js App Router**: Modern routing with React Server Components
- **API Proxy**: Automatic proxying to chaos-app (8000) and agent (8001)
- **Client-Side State**: Real-time data fetching with React hooks
- **CSS Modules**: Scoped styling without conflicts

## API Integration

The dashboard connects to:
- **Chaos App**: `http://localhost:8000` (proxied via `/api/chaos/*`)
- **Agent API**: `http://localhost:8001` (proxied via `/api/agent/*`)

## File Structure

```
dashboard-next/
├── app/
│   ├── layout.tsx      # Root layout
│   ├── page.tsx        # Main SRE Console component
│   ├── page.css        # Component styling
│   └── globals.css     # Global styles
├── package.json
├── tsconfig.json
└── next.config.js
```

## Deployment

Can be deployed to:
- Vercel (recommended)
- Docker container
- Any Node.js hosting

For Docker deployment, see the included Dockerfile example.
