# React Frontend Migration - 10K Insight Agent

## Overview

The frontend has been migrated from **Streamlit** to **React** with **TypeScript** for a more modern, performant, and customizable user experience.

## Technology Stack

- **React 18.3** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool (fast development)
- **React Router 6** - Client-side routing
- **Tailwind CSS** - Utility-first styling
- **Axios** - HTTP client
- **Lucide React** - Icon library
- **Recharts** - Data visualization (replacing Plotly)

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── common/          # Reusable components
│   │   │   └── Feedback.tsx # Loading, Error, Success messages
│   │   └── layout/
│   │       └── Sidebar.tsx  # Navigation sidebar
│   ├── pages/               # Route components
│   │   ├── Dashboard.tsx
│   │   ├── AnalysisQueue.tsx
│   │   ├── CompanyInsights.tsx
│   │   ├── TopPitches.tsx
│   │   └── Metrics.tsx
│   ├── services/
│   │   └── api.ts           # API client with TypeScript interfaces
│   ├── App.tsx              # Main app with routing
│   ├── main.tsx             # Entry point
│   ├── index.css            # Global styles + Tailwind
│   └── vite-env.d.ts        # TypeScript environment types
├── public/                  # Static assets
├── index.html              # HTML template
├── package.json            # Dependencies
├── vite.config.ts          # Vite configuration
├── tailwind.config.js      # Tailwind CSS configuration
├── tsconfig.json           # TypeScript configuration
└── setup_frontend.bat      # Setup script (Windows)
```

## Setup Instructions

### Prerequisites

- **Node.js 18+** and **npm** installed
- Docker Desktop running (for PostgreSQL)
- Python environment configured (for API)

### Installation

1. **Install Frontend Dependencies**:
   ```cmd
   cd frontend
   npm install
   ```

   Or use the setup script:
   ```cmd
   frontend\setup_frontend.bat
   ```

2. **Verify Installation**:
   ```cmd
   npm list --depth=0
   ```

## Development

### Start Development Server

**Option 1: Individual Services**

```cmd
# Terminal 1: PostgreSQL
docker-compose up -d

# Terminal 2: API Server
.venv\Scripts\python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 3: React Frontend
cd frontend
npm run dev
```

**Option 2: All Services at Once**

```cmd
start_react.bat
```

### Access the Application

- **React UI**: http://localhost:3000
- **API Server**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432

### Available npm Scripts

```json
{
  "dev": "vite",              // Start development server
  "build": "tsc && vite build", // Build for production
  "preview": "vite preview",   // Preview production build
  "lint": "eslint ."          // Run linter
}
```

## Key Features Implemented

### ✅ Completed

1. **Core Architecture**
   - React Router for navigation
   - TypeScript for type safety
   - Tailwind CSS for styling
   - Axios API client with interfaces

2. **Layout & Navigation**
   - Responsive sidebar with icons
   - Clean, modern design matching Streamlit aesthetic
   - Smooth transitions and hover effects

3. **Analysis Queue Page**
   - Company name input (multi-line)
   - Filter-based search (market cap, sector)
   - Active job monitoring
   - Real-time status updates (polling every 5 seconds)
   - Progress bars and stats

4. **Dashboard Page**
   - Quick metrics overview
   - Navigation cards
   - System statistics

5. **Common Components**
   - LoadingSpinner
   - ErrorMessage with retry
   - InfoMessage & SuccessMessage
   - Consistent styling

### 🚧 In Progress

6. **Company Insights Page** (placeholder created)
   - Company search and filtering
   - Analysis details display
   - Pain points cards
   - Product matches with scores
   - Expandable detail views

7. **Top Pitches Page** (placeholder created)
   - Pitch filtering by score
   - Persona filtering
   - Pitch cards with company info
   - Expandable pitch body

8. **Metrics Dashboard** (placeholder created)
   - System metrics charts
   - Performance analytics
   - Success rate tracking
   - Industry/sector breakdowns

## Styling Guide

The React version maintains Streamlit's clean, professional look:

### Color Palette

```css
--primary: #1f77b4    /* Blue - primary actions */
--pain: #ff6b35       /* Orange - pain points */
--success: #28a745    /* Green - success/matches */
--warning: #ffc107    /* Yellow - warnings */
--error: #dc3545      /* Red - errors */
```

### Component Classes

```tsx
<div className="card">               // Standard card
<div className="pain-card">          // Pain point card
<div className="match-card">         // Product match card
<div className="pitch-card">         // Pitch card
<button className="btn-primary">     // Primary button
<input className="input-field">      // Input field
<select className="select-field">    // Select dropdown
```

## API Integration

The `src/services/api.ts` file provides a typed API client:

```typescript
import apiClient from '@/services/api';

// Start batch analysis
const response = await apiClient.startBatchAnalysis({
  company_names: ["Microsoft", "Apple"],
  limit: 10
});

// Get job status
const status = await apiClient.getJobStatus(jobId);

// Search companies
const { companies, count } = await apiClient.searchCompanies({
  market_cap: ["mega"],
  sector: ["Technology"],
  limit: 50
});
```

All API responses are typed with TypeScript interfaces.

## Migration from Streamlit

### Key Differences

| Feature | Streamlit | React |
|---------|-----------|-------|
| **Routing** | `st.sidebar` + manual | React Router |
| **State** | Session state | React hooks (useState, useEffect) |
| **Styling** | Custom CSS in markdown | Tailwind CSS classes |
| **Auto-refresh** | Built-in (problematic) | Manual control with polling |
| **Components** | Functions | React components |
| **Port** | 8501 | 3000 |

### Advantages of React Version

✅ **Better Performance** - No full-page reloads  
✅ **Type Safety** - TypeScript catches errors at compile time  
✅ **Modern UX** - Smooth transitions, better responsiveness  
✅ **Customizable** - Full control over UI/UX  
✅ **Scalable** - Easier to maintain and extend  
✅ **Standard Stack** - Widely used tech stack  

## Building for Production

```cmd
cd frontend
npm run build
```

This creates an optimized build in `frontend/dist/`.

### Serve Production Build

```cmd
npm run preview
```

Or use a static server:

```cmd
npx serve -s dist -l 3000
```

## Troubleshooting

### Port Already in Use

If port 3000 is taken:

```cmd
# Edit vite.config.ts and change port
server: {
  port: 3001  // Or any available port
}
```

### API Connection Issues

Ensure:
1. API server is running on port 8000
2. CORS is configured in FastAPI
3. Check browser console for errors

### Styling Issues

If Tailwind classes don't work:

```cmd
# Rebuild with Tailwind
npm run build
```

## Next Steps

1. **Complete remaining pages**:
   - Finish CompanyInsights.tsx
   - Finish TopPitches.tsx
   - Finish Metrics.tsx with Recharts

2. **Add features**:
   - Company detail modal
   - Pitch export functionality
   - Advanced filtering

3. **Optimize**:
   - Code splitting
   - Lazy loading
   - Service worker (PWA)

4. **Testing**:
   - Unit tests (Jest + React Testing Library)
   - E2E tests (Playwright/Cypress)

## Contributing

When adding new features:

1. Use TypeScript for type safety
2. Follow Tailwind CSS utility classes
3. Keep components small and reusable
4. Add proper error handling
5. Update this README

## Support

For issues or questions:
- Check API server logs (Terminal 2)
- Check browser console (F12)
- Review network tab for API calls
- Check `frontend/vite.config.ts` for configuration

---

**Note**: The Streamlit version is still available in the `pages/` directory and can be run with `run_streamlit.bat` if needed.
