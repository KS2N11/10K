import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Rocket, Building2, Target, TrendingUp } from 'lucide-react';
import apiClient from '../services/api';
import { LoadingSpinner, ErrorMessage } from '../components/common/Feedback';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const data = await apiClient.getMetrics();
        setMetrics(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, []);

  if (loading) return <div className="p-8"><LoadingSpinner text="Loading dashboard..." /></div>;
  if (error) return <div className="p-8"><ErrorMessage message={error} /></div>;

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800">Welcome to 10K Insight Agent</h1>
        <p className="text-gray-600 mt-2">AI-powered analysis of SEC 10-K filings to discover sales opportunities</p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Companies Analyzed</p>
              <p className="text-3xl font-bold text-gray-800 mt-1">
                {metrics?.total_companies_analyzed || 0}
              </p>
            </div>
            <Building2 className="text-primary-500" size={40} />
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Pain Points Found</p>
              <p className="text-3xl font-bold text-gray-800 mt-1">
                {metrics?.total_pain_points_found || 0}
              </p>
            </div>
            <TrendingUp className="text-pain-500" size={40} />
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Pitches Generated</p>
              <p className="text-3xl font-bold text-gray-800 mt-1">
                {metrics?.total_pitches_generated || 0}
              </p>
            </div>
            <Target className="text-success-400" size={40} />
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Success Rate</p>
              <p className="text-3xl font-bold text-gray-800 mt-1">
                {metrics?.success_rate?.toFixed(0) || 0}%
              </p>
            </div>
            <Rocket className="text-primary-500" size={40} />
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <button
          onClick={() => navigate('/analysis-queue')}
          className="card hover:shadow-lg transition-shadow text-left p-8"
        >
          <Rocket className="text-primary-500 mb-4" size={48} />
          <h3 className="text-xl font-semibold mb-2">Start New Analysis</h3>
          <p className="text-gray-600">Launch a batch analysis job for multiple companies</p>
        </button>

        <button
          onClick={() => navigate('/company-insights')}
          className="card hover:shadow-lg transition-shadow text-left p-8"
        >
          <Building2 className="text-primary-500 mb-4" size={48} />
          <h3 className="text-xl font-semibold mb-2">Browse Companies</h3>
          <p className="text-gray-600">Explore analyzed companies and their insights</p>
        </button>

        <button
          onClick={() => navigate('/top-pitches')}
          className="card hover:shadow-lg transition-shadow text-left p-8"
        >
          <Target className="text-primary-500 mb-4" size={48} />
          <h3 className="text-xl font-semibold mb-2">View Top Pitches</h3>
          <p className="text-gray-600">Discover the highest-scoring sales opportunities</p>
        </button>

        <button
          onClick={() => navigate('/metrics')}
          className="card hover:shadow-lg transition-shadow text-left p-8"
        >
          <TrendingUp className="text-primary-500 mb-4" size={48} />
          <h3 className="text-xl font-semibold mb-2">Performance Metrics</h3>
          <p className="text-gray-600">Track system performance and analytics</p>
        </button>
      </div>
    </div>
  );
};

export default Dashboard;
