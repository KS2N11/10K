import React, { useState, useEffect } from 'react';
import { Search, Building2, Clock, ChevronDown, ChevronUp, FileText, CheckCircle, AlertCircle, ExternalLink, Quote } from 'lucide-react';
import apiClient, { CompanyDetails } from '../services/api';
import { LoadingSpinner, ErrorMessage } from '../components/common/Feedback';

type SortOption = 'Recent' | 'Company Name' | 'Score (High-Low)';

interface Analysis {
  company_id: number;
  company_name: string;
  company_ticker: string;
  company_cik: string;
  pain_points_count: number;
  matches_count: number;
  top_match_score: number;
  completed_at: string | null;
}

// Full implementation mirroring Streamlit's company_insights.py
const CompanyInsights: React.FC = () => {
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [filteredAnalyses, setFilteredAnalyses] = useState<Analysis[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<SortOption>('Recent');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedCompanyId, setExpandedCompanyId] = useState<number | null>(null);
  const [companyDetails, setCompanyDetails] = useState<CompanyDetails | null>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  useEffect(() => {
    fetchAnalyses();
  }, []);

  useEffect(() => {
    filterAndSortAnalyses();
  }, [searchQuery, sortBy, analyses]);

  const fetchAnalyses = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await apiClient.getAllAnalyses(100, 0);
      setAnalyses(data.analyses);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const filterAndSortAnalyses = () => {
    let filtered = [...analyses];

    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (a) =>
          a.company_name.toLowerCase().includes(query) ||
          a.company_ticker.toLowerCase().includes(query) ||
          a.company_cik.toLowerCase().includes(query)
      );
    }

    // Sort
    if (sortBy === 'Recent') {
      filtered.sort((a, b) => {
        const dateA = a.completed_at ? new Date(a.completed_at).getTime() : 0;
        const dateB = b.completed_at ? new Date(b.completed_at).getTime() : 0;
        return dateB - dateA;
      });
    } else if (sortBy === 'Company Name') {
      filtered.sort((a, b) => a.company_name.localeCompare(b.company_name));
    } else if (sortBy === 'Score (High-Low)') {
      filtered.sort((a, b) => b.top_match_score - a.top_match_score);
    }

    setFilteredAnalyses(filtered);
  };

  const loadCompanyDetails = async (companyId: number) => {
    if (expandedCompanyId === companyId) {
      setExpandedCompanyId(null);
      setCompanyDetails(null);
      return;
    }

    try {
      setLoadingDetails(true);
      setExpandedCompanyId(companyId);
      const data = await apiClient.getCompanyAnalysis(companyId);
      setCompanyDetails(data);
    } catch (err: any) {
      setError(`Failed to load details: ${err.message}`);
      setExpandedCompanyId(null);
    } finally {
      setLoadingDetails(false);
    }
  };

  const openFilingDocument = (companyId: number) => {
    const url = apiClient.getFilingDocumentUrl(companyId);
    window.open(url, '_blank');
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'bg-success-500';
    if (score >= 65) return 'bg-yellow-500';
    return 'bg-red-500';
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

  if (loading) {
    return <LoadingSpinner text="Loading companies..." />;
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-primary-500 flex items-center gap-3">
        <Building2 size={32} />
        Company Insights
      </h1>
      <p className="text-gray-600 mt-2">Browse and explore all analyzed companies</p>

      {/* Search and filters */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">
        <div className="md:col-span-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by name, ticker, or CIK..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
        </div>
        <div>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortOption)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            <option value="Recent">Recent</option>
            <option value="Company Name">Company Name</option>
            <option value="Score (High-Low)">Score (High-Low)</option>
          </select>
        </div>
      </div>

      {error && <ErrorMessage message={error} onRetry={fetchAnalyses} />}

      {filteredAnalyses.length === 0 && !loading && !error && (
        <div className="card mt-6 text-center py-12">
          <Building2 size={48} className="mx-auto text-gray-400 mb-4" />
          <p className="text-gray-500 text-lg">
            {searchQuery
              ? 'No companies match your search'
              : 'No analyzed companies yet. Start a batch analysis from the Analysis Queue page!'}
          </p>
        </div>
      )}

      {filteredAnalyses.length > 0 && (
        <>
          <p className="text-gray-700 font-medium mt-6">
            <strong>{filteredAnalyses.length}</strong> companies analyzed
          </p>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-4">
            {filteredAnalyses.map((analysis) => (
              <div key={analysis.company_id} className="card hover:shadow-lg transition-shadow">
                {/* Company header */}
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h3 className="text-xl font-bold text-gray-900">{analysis.company_name}</h3>
                    <p className="text-gray-600 text-sm mt-1">
                      Ticker: {analysis.company_ticker} | CIK: {analysis.company_cik}
                    </p>
                  </div>
                  <div className={`${getScoreColor(analysis.top_match_score)} text-white px-3 py-1 rounded-lg font-bold`}>
                    {analysis.top_match_score}/100
                  </div>
                </div>

                {/* Stats */}
                <div className="flex items-center gap-4 mt-4 text-sm text-gray-700">
                  <span className="flex items-center gap-1">
                    <AlertCircle size={16} className="text-pain-500" />
                    {analysis.pain_points_count} pain points
                  </span>
                  <span className="flex items-center gap-1">
                    <CheckCircle size={16} className="text-success-500" />
                    {analysis.matches_count} matches
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock size={16} className="text-gray-500" />
                    {analysis.completed_at ? new Date(analysis.completed_at).toLocaleDateString() : 'N/A'}
                  </span>
                </div>

                {/* Action buttons */}
                <div className="flex gap-2 mt-4">
                  <button
                    onClick={() => openFilingDocument(analysis.company_id)}
                    className="flex-1 py-2 px-4 bg-primary-500 hover:bg-primary-600 text-white rounded-lg flex items-center justify-center gap-2 transition-colors"
                    title="View 10-K Filing Document"
                  >
                    <FileText size={18} />
                    View 10-K
                    <ExternalLink size={14} />
                  </button>
                  
                  <button
                    onClick={() => loadCompanyDetails(analysis.company_id)}
                    className="flex-1 py-2 px-4 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg flex items-center justify-center gap-2 transition-colors"
                  >
                    {expandedCompanyId === analysis.company_id ? (
                      <>
                        <ChevronUp size={18} />
                        Hide Details
                      </>
                    ) : (
                      <>
                        <ChevronDown size={18} />
                        View Details
                      </>
                    )}
                  </button>
                </div>

                {/* Expanded details */}
                {expandedCompanyId === analysis.company_id && (
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    {loadingDetails ? (
                      <LoadingSpinner size="sm" text="Loading details..." />
                    ) : companyDetails ? (
                      <div className="space-y-6">
                        {/* Analysis summary */}
                        <div>
                          <h4 className="font-bold text-gray-900 flex items-center gap-2 mb-3">
                            <FileText size={18} />
                            Analysis Summary
                          </h4>
                          <div className="grid grid-cols-3 gap-4">
                            <div className="text-center p-3 bg-gray-50 rounded-lg">
                              <p className="text-xs text-gray-600">Filing Date</p>
                              <p className="font-semibold text-gray-900 mt-1">
                                {companyDetails.analysis.filing_date?.substring(0, 10) || 'N/A'}
                              </p>
                            </div>
                            <div className="text-center p-3 bg-gray-50 rounded-lg">
                              <p className="text-xs text-gray-600">Processing Time</p>
                              <p className="font-semibold text-gray-900 mt-1">
                                {formatDuration(companyDetails.analysis.time_taken_seconds || 0)}
                              </p>
                            </div>
                            <div className="text-center p-3 bg-gray-50 rounded-lg">
                              <p className="text-xs text-gray-600">Tokens Used</p>
                              <p className="font-semibold text-gray-900 mt-1">
                                {formatNumber(companyDetails.analysis.total_tokens_used || 0)}
                              </p>
                            </div>
                          </div>
                        </div>

                        {/* Pain points */}
                        {companyDetails.pain_points && companyDetails.pain_points.length > 0 && (
                          <div>
                            <h4 className="font-bold text-gray-900 flex items-center gap-2 mb-3">
                              <AlertCircle size={18} className="text-pain-500" />
                              Identified Pain Points
                            </h4>
                            <div className="space-y-3">
                              {companyDetails.pain_points.map((pain, idx) => (
                                <div key={idx} className="pain-card">
                                  <div className="flex justify-between items-start mb-2">
                                    <h5 className="font-bold text-gray-900">{idx + 1}. {pain.theme}</h5>
                                    <span className="bg-success-500 text-white text-xs px-2 py-1 rounded">
                                      {Math.round((pain.confidence || 0) * 100)}% confidence
                                    </span>
                                  </div>
                                  <p className="text-gray-700 text-sm mb-2">{pain.rationale}</p>
                                  
                                  {/* Display quotes/references from 10-K */}
                                  {pain.quotes && pain.quotes.length > 0 && (
                                    <div className="mt-3 pt-3 border-t border-gray-200">
                                      <div className="flex items-center gap-2 mb-2">
                                        <Quote size={14} className="text-primary-500" />
                                        <span className="text-xs font-semibold text-gray-700">
                                          References from 10-K:
                                        </span>
                                      </div>
                                      <div className="space-y-2">
                                        {pain.quotes.map((quote, qIdx) => (
                                          <div key={qIdx} className="bg-gray-50 border-l-4 border-primary-500 pl-3 pr-2 py-2 rounded">
                                            <p className="text-xs text-gray-700 italic">"{quote}"</p>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Product matches */}
                        {companyDetails.product_matches && companyDetails.product_matches.length > 0 && (
                          <div>
                            <h4 className="font-bold text-gray-900 flex items-center gap-2 mb-3">
                              <CheckCircle size={18} className="text-success-500" />
                              Recommended Solutions
                            </h4>
                            <div className="space-y-3">
                              {companyDetails.product_matches.slice(0, 5).map((match, idx) => (
                                <div key={idx} className="match-card">
                                  <div className="flex justify-between items-start mb-2">
                                    <h5 className="font-bold text-gray-900">{idx + 1}. {match.product_name}</h5>
                                    <span className={`${getScoreColor(match.fit_score)} text-white text-xs px-2 py-1 rounded`}>
                                      Score: {match.fit_score}/100
                                    </span>
                                  </div>
                                  <p className="text-gray-700 text-sm"><strong>Why it fits:</strong> {match.why_fits}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ) : null}
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};


export default CompanyInsights;
