import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Sidebar } from './components/layout/Sidebar';
import Dashboard from './pages/Dashboard';
import AnalysisQueue from './pages/AnalysisQueue';
import CompanyInsights from './pages/CompanyInsights';
import TopPitches from './pages/TopPitches';
import Metrics from './pages/Metrics';
import CatalogManager from './pages/CatalogManager';

const App: React.FC = () => {
  return (
    <Router>
      <div className="flex h-screen overflow-hidden bg-gray-50">
        {/* Sidebar */}
        <Sidebar />
        
        {/* Main Content */}
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/analysis-queue" element={<AnalysisQueue />} />
            <Route path="/company-insights" element={<CompanyInsights />} />
            <Route path="/top-pitches" element={<TopPitches />} />
            <Route path="/metrics" element={<Metrics />} />
            <Route path="/catalog-manager" element={<CatalogManager />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
};

export default App;
