import React, { useState, useEffect } from 'react';
import { Rocket, Search, Filter, Play, CheckSquare, Square } from 'lucide-react';
import apiClient, { type JobStatus } from '../services/api';
import { LoadingSpinner, ErrorMessage, InfoMessage, SuccessMessage } from '../components/common/Feedback';

const AnalysisQueue: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'list' | 'filter' | 'jobs'>('list');
  const [companyNames, setCompanyNames] = useState('');
  const [marketCaps, setMarketCaps] = useState<string[]>([]);
  const [industries, setIndustries] = useState<string[]>([]);
  const [sectors, setSectors] = useState<string[]>([]);
  const [limit, setLimit] = useState(10);
  const [forceReanalyze, setForceReanalyze] = useState(false);
  const [activeJobs, setActiveJobs] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [previewCompanies, setPreviewCompanies] = useState<any[]>([]);
  const [showPreview, setShowPreview] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);
  
  // New state for features
  const [useRealtimeLookup, setUseRealtimeLookup] = useState(false);
  const [selectedCompanies, setSelectedCompanies] = useState<Set<number>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [loadingSearch, setLoadingSearch] = useState(false);

  // Fetch active jobs on mount and periodically
  useEffect(() => {
    const fetchActiveJobs = async () => {
      try {
        const response = await apiClient.getAllJobs(false); // Only active jobs
        const jobIds = response.jobs.map(job => job.job_id);
        setActiveJobs(jobIds);
      } catch (err) {
        console.error('Failed to fetch active jobs:', err);
      }
    };

    // Fetch on mount
    fetchActiveJobs();

    // Refresh active jobs every 10 seconds
    const interval = setInterval(fetchActiveJobs, 10000);

    return () => clearInterval(interval);
  }, []);

  const startBatchJob = async (params: { 
    company_names?: string[]; 
    filters?: any; 
    limit?: number; 
    force_reanalyze?: boolean;
    selected_companies?: Array<{ cik: string; ticker: string; name: string }>;
  }) => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await apiClient.startBatchAnalysis(params);
      setSuccess(`✅ ${response.message}`);
      setActiveJobs([...activeJobs, response.job_id]);
      setActiveTab('jobs');
      
      // Clear selections after starting
      setSelectedCompanies(new Set());
      setShowPreview(false);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to start batch job');
    } finally {
      setLoading(false);
    }
  };

  const handleDirectSubmit = () => {
    const names = companyNames
      .split('\n')
      .map((n) => n.trim())
      .filter((n) => n.length > 0);

    if (names.length === 0) {
      setError('Please enter at least one company name');
      return;
    }

    startBatchJob({ company_names: names, force_reanalyze: forceReanalyze });
  };

  const handleFilterSubmit = () => {
    if (marketCaps.length === 0 && industries.length === 0 && sectors.length === 0) {
      setError('Please select at least one filter');
      return;
    }

    const filters: any = {};
    if (marketCaps.length > 0) filters.market_cap = marketCaps;
    if (industries.length > 0) filters.industry = industries;
    if (sectors.length > 0) filters.sector = sectors;

    startBatchJob({ filters, limit, force_reanalyze: forceReanalyze });
  };

  const handlePreviewSEC = async () => {
    if (marketCaps.length === 0 && industries.length === 0 && sectors.length === 0) {
      setError('Please select at least one filter');
      return;
    }

    setLoadingPreview(true);
    setError(null);
    
    // Show estimated time for real-time lookup with more accurate estimates
    if (useRealtimeLookup) {
      const minSeconds = Math.ceil(limit / 10 * 2); // ~2 seconds per batch of 10
      const maxSeconds = Math.ceil(limit / 10 * 4); // ~4 seconds per batch of 10
      const minMinutes = Math.floor(minSeconds / 60);
      const maxMinutes = Math.ceil(maxSeconds / 60);
      
      if (maxSeconds < 60) {
        setSuccess(`⏳ Starting real-time lookup... This will take approximately ${minSeconds}-${maxSeconds} seconds. Please wait...`);
      } else {
        setSuccess(`⏳ Starting real-time lookup... This will take approximately ${minMinutes}-${maxMinutes} minutes. Please be patient...`);
      }
    }

    try {
      const result = await apiClient.searchSECCompanies({
        market_cap: marketCaps.length > 0 ? marketCaps : undefined,
        industry: industries.length > 0 ? industries : undefined,
        sector: sectors.length > 0 ? sectors : undefined,
        limit: limit,
        use_realtime: useRealtimeLookup,
      });

      setPreviewCompanies(result.companies);
      setShowPreview(true);
      setSelectedCompanies(new Set()); // Reset selections
      setSuccess(`Found ${result.count} companies from ${result.source} (${result.lookup_method})`);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to search SEC companies';
      setError(`${errorMsg}. ${useRealtimeLookup ? 'Try reducing the limit or disabling real-time lookup.' : ''}`);
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleSearchByName = async () => {
    if (!searchQuery.trim()) {
      setError('Please enter a company name or ticker');
      return;
    }

    setLoadingSearch(true);
    setError(null);

    try {
      const result = await apiClient.searchCompanyByName(searchQuery, 20);
      setSearchResults(result.companies);
      setSuccess(`Found ${result.count} companies matching "${searchQuery}"`);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to search company');
    } finally {
      setLoadingSearch(false);
    }
  };

  const handleToggleCompany = (index: number) => {
    const newSelected = new Set(selectedCompanies);
    if (newSelected.has(index)) {
      newSelected.delete(index);
    } else {
      newSelected.add(index);
    }
    setSelectedCompanies(newSelected);
  };

  const handleToggleAll = () => {
    if (selectedCompanies.size === previewCompanies.length) {
      setSelectedCompanies(new Set());
    } else {
      setSelectedCompanies(new Set(previewCompanies.map((_, idx) => idx)));
    }
  };

  const handleAnalyzeSelected = () => {
    if (selectedCompanies.size === 0) {
      setError('Please select at least one company to analyze');
      return;
    }

    const selected = Array.from(selectedCompanies).map(idx => previewCompanies[idx]);
    startBatchJob({ 
      selected_companies: selected,
      force_reanalyze: forceReanalyze 
    });
  };

  const handleAnalyzePreviewedCompanies = () => {
    if (previewCompanies.length === 0) {
      setError('No companies to analyze');
      return;
    }

    // Analyze ALL previewed companies
    const names = previewCompanies.map(c => c.name || c.title);
    startBatchJob({ company_names: names, limit: names.length, force_reanalyze: forceReanalyze });
    setShowPreview(false);
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-primary-500 flex items-center gap-3">
          <Rocket size={32} />
          Analysis Queue Manager
        </h1>
        <p className="text-gray-600 mt-2">Configure and launch batch analysis jobs for multiple companies</p>
      </div>

      {/* Feedback Messages */}
      {error && <ErrorMessage message={error} onRetry={() => setError(null)} />}
      {success && <SuccessMessage message={success} />}

      {/* Tabs */}
      <div className="flex space-x-4 border-b border-gray-200 mb-6">
        <button
          onClick={() => setActiveTab('list')}
          className={`pb-3 px-4 font-medium transition-colors ${
            activeTab === 'list'
              ? 'text-primary-500 border-b-2 border-primary-500'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          📋 Company List
        </button>
        <button
          onClick={() => setActiveTab('filter')}
          className={`pb-3 px-4 font-medium transition-colors ${
            activeTab === 'filter'
              ? 'text-primary-500 border-b-2 border-primary-500'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          🔍 Filter Search
        </button>
        <button
          onClick={() => setActiveTab('jobs')}
          className={`pb-3 px-4 font-medium transition-colors ${
            activeTab === 'jobs'
              ? 'text-primary-500 border-b-2 border-primary-500'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          ⏱️ Active Jobs {activeJobs.length > 0 && `(${activeJobs.length})`}
        </button>
      </div>

      {/* Tab Content */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        {/* Company List Tab */}
        {activeTab === 'list' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Enter Company Names</h2>
            <p className="text-gray-600 mb-4">Add specific companies you want to analyze (one per line)</p>

            <textarea
              value={companyNames}
              onChange={(e) => setCompanyNames(e.target.value)}
              placeholder="Microsoft&#10;Apple&#10;Tesla&#10;Google&#10;Amazon"
              className="input-field w-full h-64 font-mono text-sm"
            />

            {companyNames && (
              <InfoMessage
                message={`📝 ${companyNames.split('\n').filter((n) => n.trim()).length} companies entered`}
              />
            )}

            {/* Force Re-analyze Option */}
            <div className="mt-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={forceReanalyze}
                  onChange={(e) => setForceReanalyze(e.target.checked)}
                  className="w-4 h-4 text-primary-600 bg-gray-100 border-gray-300 rounded focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700">
                  Force re-analyze (skip cache and re-process companies already analyzed)
                </span>
              </label>
            </div>

            <button
              onClick={handleDirectSubmit}
              disabled={loading || !companyNames.trim()}
              className="btn-primary mt-4 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Play size={18} />
              Start Analysis
            </button>
          </div>
        )}

        {/* Filter Search Tab */}
        {activeTab === 'filter' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Search SEC Companies by Filters</h2>
            <p className="text-gray-600 mb-6">
              Search the SEC EDGAR database (14,000+ companies), preview results, and select which ones to analyze
            </p>

            {/* Direct Company Search */}
            <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h3 className="font-bold text-gray-900 mb-3">🔍 Direct Company Search</h3>
              <p className="text-sm text-gray-600 mb-3">Search for specific companies by name or ticker symbol</p>
              <div className="flex gap-3">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearchByName()}
                  placeholder="Enter company name or ticker (e.g., Apple, AAPL)"
                  className="input-field flex-1"
                />
                <button
                  onClick={handleSearchByName}
                  disabled={loadingSearch || !searchQuery.trim()}
                  className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Search size={18} />
                  {loadingSearch ? 'Searching...' : 'Search'}
                </button>
              </div>
              
              {/* Search Results */}
              {searchResults.length > 0 && (
                <div className="mt-4 max-h-60 overflow-y-auto space-y-2">
                  {searchResults.map((company, idx) => (
                    <div 
                      key={idx} 
                      className="bg-white p-3 rounded border border-gray-200 flex items-center justify-between hover:bg-gray-50 cursor-pointer"
                      onClick={() => {
                        setPreviewCompanies([company]);
                        setShowPreview(true);
                        setSelectedCompanies(new Set([0]));
                      }}
                    >
                      <div>
                        <div className="font-semibold text-gray-900">{company.name || company.title}</div>
                        <div className="text-sm text-gray-600 mt-1">
                          {company.ticker && <span className="mr-3">Ticker: {company.ticker}</span>}
                          {company.cik && <span>CIK: {company.cik}</span>}
                        </div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          startBatchJob({ 
                            selected_companies: [company],
                            force_reanalyze: forceReanalyze 
                          });
                        }}
                        className="text-primary-600 hover:text-primary-700 text-sm font-medium"
                      >
                        Analyze →
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Filter by Market Cap/Sector */}
            <h3 className="font-bold text-gray-900 mb-3">Or filter by criteria:</h3>
            <div className="grid grid-cols-2 gap-6 mb-6">
              {/* Market Cap */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Market Capitalization</label>
                <div className="space-y-2">
                  {['small', 'mid', 'large', 'mega'].map((cap) => (
                    <label key={cap} className="flex items-center">
                      <input
                        type="checkbox"
                        checked={marketCaps.includes(cap)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setMarketCaps([...marketCaps, cap]);
                          } else {
                            setMarketCaps(marketCaps.filter((c) => c !== cap));
                          }
                        }}
                        className="mr-2"
                      />
                      <span className="capitalize">{cap}</span>
                      <span className="text-xs text-gray-500 ml-2">
                        {cap === 'small' && '< $2B'}
                        {cap === 'mid' && '$2B - $10B'}
                        {cap === 'large' && '$10B - $200B'}
                        {cap === 'mega' && '> $200B'}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Sector */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Sector</label>
                <select
                  multiple
                  value={sectors}
                  onChange={(e) => {
                    const selected = Array.from(e.target.selectedOptions, (option) => option.value);
                    setSectors(selected);
                  }}
                  className="select-field w-full h-32"
                >
                  <option value="Technology">Technology</option>
                  <option value="Healthcare">Healthcare</option>
                  <option value="Financials">Financials</option>
                  <option value="Consumer Discretionary">Consumer Discretionary</option>
                  <option value="Consumer Cyclical">Consumer Cyclical</option>
                  <option value="Industrials">Industrials</option>
                  <option value="Energy">Energy</option>
                  <option value="Materials">Materials</option>
                  <option value="Consumer Staples">Consumer Staples</option>
                  <option value="Utilities">Utilities</option>
                  <option value="Real Estate">Real Estate</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">Hold Ctrl/Cmd to select multiple</p>
              </div>
            </div>

            {/* Limit */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Max Companies to Preview: {limit}
              </label>
              <input
                type="range"
                min="1"
                max="100"
                value={limit}
                onChange={(e) => setLimit(parseInt(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>1</span>
                <span>100</span>
              </div>
            </div>

            {/* Real-time Lookup Toggle */}
            <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useRealtimeLookup}
                  onChange={(e) => setUseRealtimeLookup(e.target.checked)}
                  className="rounded border-gray-300"
                />
                <span className="text-sm font-medium">
                  Use real-time market cap lookup
                  <span className="text-gray-600 ml-1 font-normal">
                    (slower but covers all 14,000+ companies)
                  </span>
                </span>
              </label>
              
              {useRealtimeLookup && (
                <div className="mt-2 ml-6 space-y-1">
                  {limit <= 20 && (
                    <div className="mb-2 p-2 bg-orange-50 border border-orange-200 rounded">
                      <p className="text-xs text-orange-700 font-medium">
                        ⚡ For {limit} companies, <strong>static mode is faster</strong> (instant results)
                      </p>
                      <p className="text-xs text-orange-600 mt-1">
                        Real-time mode checks ALL 14,000+ companies to find matches. For small queries, this is overkill.
                      </p>
                    </div>
                  )}
                  <p className="text-xs text-yellow-700">
                    ⚠️ Real-time lookup queries Yahoo Finance. Expected time:
                  </p>
                  <p className="text-xs text-yellow-600 ml-3">
                    • 10 companies: ~30-60 seconds (checking 50-100 companies)
                  </p>
                  <p className="text-xs text-yellow-600 ml-3">
                    • 25 companies: ~60-120 seconds (checking 100-200 companies)
                  </p>
                  <p className="text-xs text-yellow-600 ml-3">
                    • 50 companies: ~2-3 minutes (checking 200-300 companies)
                  </p>
                  <p className="text-xs text-yellow-600 ml-3">
                    • 100 companies: ~3-5 minutes (checking 300-500 companies)
                  </p>
                  <p className="text-xs text-yellow-700 mt-1 font-medium">
                    💡 Recommendation: Disable real-time for queries under 20 companies
                  </p>
                </div>
              )}
              
              {!useRealtimeLookup && (
                <p className="text-xs text-gray-600 mt-2 ml-6">
                  ℹ️ Using fast static mapping (~100 well-known companies). Enable real-time only if you need lesser-known companies.
                </p>
              )}
            </div>

            {/* Force Re-analyze Option */}
            <div className="mb-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={forceReanalyze}
                  onChange={(e) => setForceReanalyze(e.target.checked)}
                  className="w-4 h-4 text-primary-600 bg-gray-100 border-gray-300 rounded focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700">
                  Force re-analyze (skip cache and re-process companies already analyzed)
                </span>
              </label>
            </div>

            <div className="flex gap-3">
              <button
                onClick={handlePreviewSEC}
                disabled={loadingPreview || (marketCaps.length === 0 && industries.length === 0 && sectors.length === 0)}
                className="flex-1 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Search size={18} />
                {loadingPreview ? 'Searching SEC...' : '🔍 Preview Companies from SEC'}
              </button>
            </div>

            {/* Preview Results with Selection */}
            {showPreview && (
              <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-bold text-gray-900 flex items-center gap-2">
                    <Search size={18} />
                    Found {previewCompanies.length} Companies from SEC EDGAR
                  </h3>
                  <button
                    onClick={handleToggleAll}
                    className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-2"
                  >
                    {selectedCompanies.size === previewCompanies.length ? (
                      <>
                        <CheckSquare size={16} />
                        Deselect All
                      </>
                    ) : (
                      <>
                        <Square size={16} />
                        Select All
                      </>
                    )}
                  </button>
                </div>

                {previewCompanies.length > 0 ? (
                  <>
                    <div className="max-h-96 overflow-y-auto space-y-2 mb-4">
                      {previewCompanies.map((company, idx) => (
                        <div 
                          key={idx} 
                          className={`bg-white p-3 rounded border-2 transition-all cursor-pointer ${
                            selectedCompanies.has(idx) 
                              ? 'border-primary-500 bg-primary-50' 
                              : 'border-gray-200 hover:border-gray-300'
                          }`}
                          onClick={() => handleToggleCompany(idx)}
                        >
                          <div className="flex items-start gap-3">
                            <div className="mt-1">
                              {selectedCompanies.has(idx) ? (
                                <CheckSquare size={20} className="text-primary-600" />
                              ) : (
                                <Square size={20} className="text-gray-400" />
                              )}
                            </div>
                            <div className="flex-1">
                              <div className="font-semibold text-gray-900">{company.name || company.title}</div>
                              <div className="text-sm text-gray-600 mt-1">
                                {company.ticker && <span className="mr-3">Ticker: {company.ticker}</span>}
                                {company.cik && <span className="mr-3">CIK: {company.cik}</span>}
                                {company.market_cap_tier && (
                                  <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">
                                    {company.market_cap_tier}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Action Buttons */}
                    <div className="flex gap-3">
                      <button
                        onClick={handleAnalyzeSelected}
                        disabled={loading || selectedCompanies.size === 0}
                        className="flex-1 btn-primary flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <Play size={18} />
                        Analyze Selected ({selectedCompanies.size})
                      </button>
                      
                      <button
                        onClick={handleAnalyzePreviewedCompanies}
                        disabled={loading}
                        className="flex-1 bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        <Play size={18} />
                        Analyze All ({previewCompanies.length})
                      </button>
                    </div>
                  </>
                ) : (
                  <p className="text-gray-600">No companies found matching your filters.</p>
                )}

                <p className="text-sm text-gray-600 mt-4">
                  ℹ️ Selected companies will have their latest 10-K filings fetched from SEC and analyzed for pain points and product matches.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Active Jobs Tab */}
        {activeTab === 'jobs' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Active & Recent Jobs</h2>

            {activeJobs.length === 0 ? (
              <InfoMessage message="No active jobs. Start a new analysis from the other tabs!" />
            ) : (
              <div className="space-y-4">
                {activeJobs.map((jobId) => (
                  <JobMonitor key={jobId} jobId={jobId} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Job Monitor Component
interface JobMonitorProps {
  jobId: string;
}

const JobMonitor: React.FC<JobMonitorProps> = ({ jobId }) => {
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchJobStatus = async () => {
    try {
      const status = await apiClient.getJobStatus(jobId);
      setJobStatus(status);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch job status');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobStatus();
    
    // Poll every 2 seconds for live progress updates
    const interval = setInterval(() => {
      if (jobStatus?.status === 'QUEUED' || jobStatus?.status === 'IN_PROGRESS') {
        fetchJobStatus();
      } else if (jobStatus?.status === 'COMPLETED' || jobStatus?.status === 'FAILED') {
        // Stop polling for terminal states
        clearInterval(interval);
      }
    }, 2000); // Reduced from 5000ms to 2000ms for more responsive updates

    return () => clearInterval(interval);
  }, [jobId, jobStatus?.status]);

  if (loading) return <LoadingSpinner size="sm" text="Loading job status..." />;
  if (error) return <ErrorMessage message={error} onRetry={fetchJobStatus} />;
  if (!jobStatus) return null;

  const progress = jobStatus.total_companies > 0
    ? ((jobStatus.completed + jobStatus.failed + jobStatus.skipped) / jobStatus.total_companies) * 100
    : 0;

  const isActive = jobStatus.status === 'QUEUED' || jobStatus.status === 'IN_PROGRESS';

  return (
    <div className="card">
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <h3 className="font-semibold text-lg">Job: {jobId.slice(0, 8)}...</h3>
          
          {/* Live Progress Indicator */}
          {isActive && jobStatus.current_company && (
            <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center gap-2 text-blue-800">
                <div className="animate-pulse w-2 h-2 bg-blue-600 rounded-full"></div>
                <span className="font-medium">Currently analyzing:</span>
              </div>
              <div className="text-gray-900 font-semibold mt-1">{jobStatus.current_company}</div>
              {jobStatus.current_step && (
                <div className="text-sm text-gray-600 mt-1">
                  Step: {jobStatus.current_step}
                </div>
              )}
            </div>
          )}

          {/* Completion Message */}
          {!isActive && (
            <p className="text-sm text-gray-600 mt-2">
              {jobStatus.status === 'COMPLETED' ? '✅ Analysis complete!' : '⚠️ Job terminated'}
            </p>
          )}
        </div>
        
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${
          jobStatus.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
          jobStatus.status === 'IN_PROGRESS' ? 'bg-blue-100 text-blue-800' :
          jobStatus.status === 'FAILED' ? 'bg-red-100 text-red-800' :
          'bg-gray-100 text-gray-800'
        }`}>
          {jobStatus.status}
        </span>
      </div>

      {/* Progress Bar with smooth animation */}
      <div className="mb-4">
        <div className="flex justify-between text-sm text-gray-600 mb-1">
          <span>Progress: {jobStatus.completed + jobStatus.failed + jobStatus.skipped} / {jobStatus.total_companies}</span>
          <span className="font-semibold">{progress.toFixed(1)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
          <div
            className={`h-3 rounded-full transition-all duration-500 ease-out ${
              isActive ? 'bg-primary-500' : 'bg-green-500'
            }`}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-4 text-center">
        <div>
          <div className="text-2xl font-bold text-gray-800">{jobStatus.total_companies}</div>
          <div className="text-xs text-gray-500">Total</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-green-600">{jobStatus.completed}</div>
          <div className="text-xs text-gray-500">Completed</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-red-600">{jobStatus.failed}</div>
          <div className="text-xs text-gray-500">Failed</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-yellow-600">{jobStatus.skipped}</div>
          <div className="text-xs text-gray-500">Skipped</div>
        </div>
      </div>

      {/* Error Details (if any) */}
      {jobStatus.errors && jobStatus.errors.length > 0 && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <h4 className="font-semibold text-red-800 mb-2 flex items-center gap-2">
            <span className="text-lg">⚠️</span>
            Recent Errors ({jobStatus.errors.length})
          </h4>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {jobStatus.errors.map((err, idx) => (
              <div key={idx} className="text-sm bg-white p-2 rounded border border-red-100">
                <div className="font-medium text-gray-900">{err.company}</div>
                <div className="text-red-700 text-xs mt-1">{err.error}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ETA Display for active jobs */}
      {isActive && jobStatus.estimated_time_remaining && (
        <div className="mt-4 text-center text-sm text-gray-600">
          ⏱️ Estimated time remaining: {Math.ceil(jobStatus.estimated_time_remaining / 60)} minutes
        </div>
      )}
    </div>
  );
};

export default AnalysisQueue;
