import React, { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, Clock, DollarSign, Zap } from 'lucide-react';
import apiClient, { Metrics as MetricsData } from '../services/api';
import { LoadingSpinner, ErrorMessage } from '../components/common/Feedback';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

interface Analysis {
  company_id: number;
  company_name: string;
  top_match_score: number;
  pain_points_count: number;
  matches_count: number;
  completed_at: string;
}

const COLORS = ['#667eea', '#764ba2', '#f093fb', '#4facfe'];

// Full implementation mirroring Streamlit's metrics_dashboard.py
const Metrics: React.FC = () => {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [manualTime, setManualTime] = useState(2.0);
  const [hourlyRate, setHourlyRate] = useState(75);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError('');
      const [metricsData, analysesData] = await Promise.all([
        apiClient.getMetrics(),
        apiClient.getAllAnalyses(500, 0),
      ]);
      setMetrics(metricsData);
      setAnalyses(analysesData.analyses);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatDuration = (seconds: number): string => {
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  const formatNumber = (num: number): string => {
    return num.toLocaleString();
  };

  // ROI Calculations
  const companiesAnalyzed = metrics?.total_companies_analyzed || 0;
  const autoTime = (metrics?.avg_time_per_analysis || 0) / 3600; // Convert to hours
  const manualCost = companiesAnalyzed * manualTime * hourlyRate;
  const autoCost = companiesAnalyzed * autoTime * hourlyRate;
  const savings = manualCost - autoCost;
  const roi = autoCost > 0 ? (savings / autoCost) * 100 : 0;

  // Prepare chart data
  const prepareTimeSeriesData = () => {
    const dailyCount: { [key: string]: number } = {};
    analyses.forEach(a => {
      const date = new Date(a.completed_at).toLocaleDateString();
      dailyCount[date] = (dailyCount[date] || 0) + 1;
    });

    const sortedDates = Object.keys(dailyCount).sort((a, b) => new Date(a).getTime() - new Date(b).getTime());
    let cumulative = 0;
    
    return sortedDates.map(date => {
      cumulative += dailyCount[date];
      return {
        date,
        count: dailyCount[date],
        cumulative,
      };
    });
  };

  const prepareScoreDistribution = () => {
    const bins = [0, 20, 40, 50, 60, 70, 80, 90, 100];
    const distribution = bins.slice(0, -1).map((min, i) => ({
      range: `${min}-${bins[i + 1]}`,
      count: analyses.filter(a => a.top_match_score >= min && a.top_match_score < bins[i + 1]).length,
    }));
    return distribution;
  };

  const prepareScoreCategories = () => {
    const categories = [
      { name: 'Excellent (80-100)', min: 80, max: 100 },
      { name: 'Good (65-79)', min: 65, max: 79 },
      { name: 'Fair (50-64)', min: 50, max: 64 },
      { name: 'Poor (<50)', min: 0, max: 49 },
    ];

    return categories.map(cat => ({
      name: cat.name,
      value: analyses.filter(a => a.top_match_score >= cat.min && a.top_match_score <= cat.max).length,
    })).filter(c => c.value > 0);
  };

  const getTopCompanies = () => {
    return [...analyses]
      .sort((a, b) => b.top_match_score - a.top_match_score)
      .slice(0, 10)
      .map(a => ({
        name: a.company_name.substring(0, 20),
        score: a.top_match_score,
      }));
  };

  const preparePainVsMatches = () => {
    return analyses.map(a => ({
      name: a.company_name.substring(0, 15),
      painPoints: a.pain_points_count,
      matches: a.matches_count,
      score: a.top_match_score,
    }));
  };

  const timeSeriesData = prepareTimeSeriesData();
  const scoreDistribution = prepareScoreDistribution();
  const scoreCategories = prepareScoreCategories();
  const topCompanies = getTopCompanies();
  const painVsMatches = preparePainVsMatches();

  if (loading) {
    return <LoadingSpinner text="Loading metrics..." />;
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={fetchData} />;
  }

  if (!metrics) {
    return <ErrorMessage message="Failed to load metrics. Please ensure the API is running." onRetry={fetchData} />;
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-primary-500 flex items-center gap-3">
        <BarChart3 size={32} />
        Performance Analytics
      </h1>
      <p className="text-gray-600 mt-2">Track system performance, usage, and ROI</p>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mt-6">
        <div className="bg-gradient-to-br from-purple-500 to-purple-600 text-white rounded-lg p-6 shadow-lg">
          <div className="text-4xl mb-2">🏢</div>
          <div className="text-3xl font-bold">{formatNumber(metrics.total_companies_analyzed)}</div>
          <div className="text-purple-100 text-sm mt-1">Companies Analyzed</div>
        </div>

        <div className="bg-gradient-to-br from-indigo-500 to-indigo-600 text-white rounded-lg p-6 shadow-lg">
          <div className="text-4xl mb-2">📊</div>
          <div className="text-3xl font-bold">{formatNumber(metrics.total_analyses_run)}</div>
          <div className="text-indigo-100 text-sm mt-1">Total Analyses</div>
        </div>

        <div className="bg-gradient-to-br from-pink-400 to-pink-500 text-white rounded-lg p-6 shadow-lg">
          <div className="text-4xl mb-2">🔍</div>
          <div className="text-3xl font-bold">{formatNumber(metrics.total_pain_points_found)}</div>
          <div className="text-pink-100 text-sm mt-1">Pain Points Found</div>
        </div>

        <div className="bg-gradient-to-br from-blue-400 to-blue-500 text-white rounded-lg p-6 shadow-lg">
          <div className="text-4xl mb-2">💼</div>
          <div className="text-3xl font-bold">{formatNumber(metrics.total_pitches_generated)}</div>
          <div className="text-blue-100 text-sm mt-1">Pitches Generated</div>
        </div>
      </div>

      {/* Performance Metrics */}
      <div className="card mt-6">
        <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2 mb-4">
          <Zap size={24} className="text-yellow-500" />
          Performance & Efficiency
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <Clock size={32} className="mx-auto text-gray-600 mb-2" />
            <p className="text-sm text-gray-600">Total Processing Time</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              {formatDuration(metrics.total_processing_time_seconds)}
            </p>
          </div>

          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <TrendingUp size={32} className="mx-auto text-gray-600 mb-2" />
            <p className="text-sm text-gray-600">Avg Time Per Analysis</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              {formatDuration(metrics.avg_time_per_analysis)}
            </p>
          </div>

          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <Clock size={32} className="mx-auto text-success-600 mb-2" />
            <p className="text-sm text-gray-600">Time Saved (vs Manual)</p>
            <p className="text-2xl font-bold text-success-600 mt-1">
              {metrics.estimated_time_saved_hours.toFixed(0)} hrs
            </p>
            <p className="text-xs text-gray-500 mt-1">
              ≈ {(metrics.estimated_time_saved_hours / 8).toFixed(0)} work days
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-600">Total Tokens Used</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              {formatNumber(metrics.total_tokens_used)}
            </p>
          </div>

          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-600">Total Cost</p>
            <p className="text-2xl font-bold text-success-600 mt-1">$0.00</p>
            <p className="text-xs text-success-600 mt-1">100% Free Tier</p>
          </div>

          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-600">Avg Tokens/Company</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              {formatNumber(Math.round(metrics.total_tokens_used / Math.max(companiesAnalyzed, 1)))}
            </p>
          </div>
        </div>
      </div>

      {/* Charts */}
      {analyses.length > 0 && (
        <div className="space-y-6 mt-6">
          {/* Trends Tab */}
          <div className="card">
            <h2 className="text-xl font-bold text-gray-900 mb-4">📈 Analysis Trends</h2>
            
            <div className="space-y-8">
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">Analyses Completed Over Time</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={timeSeriesData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="count" stroke="#667eea" strokeWidth={3} name="Daily Count" />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div>
                <h3 className="font-semibold text-gray-700 mb-3">Cumulative Analyses</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={timeSeriesData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Area type="monotone" dataKey="cumulative" stroke="#667eea" fill="rgba(102, 126, 234, 0.3)" name="Total Analyses" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Scoring Tab */}
          <div className="card">
            <h2 className="text-xl font-bold text-gray-900 mb-4">🎯 Score Analysis</h2>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div>
                <h3 className="font-semibold text-gray-700 mb-3">Score Distribution</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={scoreDistribution}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="range" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="count" fill="#764ba2" name="Companies" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div>
                <h3 className="font-semibold text-gray-700 mb-3">Match Quality Breakdown</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={scoreCategories}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={(entry) => `${entry.name}: ${entry.value}`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {scoreCategories.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Industry/Company Analysis */}
          <div className="card">
            <h2 className="text-xl font-bold text-gray-900 mb-4">🏭 Company Analysis</h2>
            
            <div>
              <h3 className="font-semibold text-gray-700 mb-3">Top 10 Companies by Match Score</h3>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={topCompanies} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" domain={[0, 100]} />
                  <YAxis type="category" dataKey="name" width={150} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="score" fill="#667eea" name="Score" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* ROI Calculator */}
      <div className="card mt-6">
        <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2 mb-4">
          <DollarSign size={24} className="text-success-600" />
          ROI Calculator
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <h3 className="font-semibold text-gray-700 mb-4">Manual Research Assumptions</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Hours per company (manual): {manualTime}
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="10"
                  step="0.5"
                  value={manualTime}
                  onChange={(e) => setManualTime(Number(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-500"
                />
                <p className="text-xs text-gray-500 mt-1">How long would it take to manually research one company?</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Hourly rate: ${hourlyRate}/hr
                </label>
                <input
                  type="number"
                  min="20"
                  max="500"
                  step="5"
                  value={hourlyRate}
                  onChange={(e) => setHourlyRate(Number(e.target.value))}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
                <p className="text-xs text-gray-500 mt-1">Average hourly cost of sales rep/analyst</p>
              </div>
            </div>
          </div>

          <div>
            <h3 className="font-semibold text-gray-700 mb-4">Automated Analysis</h3>
            <div className="space-y-4">
              <div className="p-4 bg-red-50 rounded-lg border-l-4 border-red-500">
                <p className="text-sm text-gray-600">Manual Research Cost</p>
                <p className="text-3xl font-bold text-red-600">${manualCost.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</p>
              </div>

              <div className="p-4 bg-blue-50 rounded-lg border-l-4 border-blue-500">
                <p className="text-sm text-gray-600">Automated Cost</p>
                <p className="text-3xl font-bold text-blue-600">${autoCost.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</p>
              </div>

              <div className="p-4 bg-success-50 rounded-lg border-l-4 border-success-500">
                <p className="text-sm text-gray-600">💰 Total Savings</p>
                <p className="text-3xl font-bold text-success-600">${savings.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</p>
                <p className="text-lg font-semibold text-success-600 mt-1">{roi.toFixed(0)}% ROI</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Metrics;

