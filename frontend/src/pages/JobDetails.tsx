import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle, XCircle, Clock, AlertCircle, ExternalLink } from 'lucide-react';
import apiClient, { type JobStatus } from '../services/api';
import { LoadingSpinner, ErrorMessage, InfoMessage } from '../components/common/Feedback';

const JobDetails: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [companies, setCompanies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchJobDetails = async () => {
    if (!jobId) return;
    
    try {
      setRefreshing(true);
      // Fetch job status
      const status = await apiClient.getJobStatus(jobId);
      setJobStatus(status);
      
      // Fetch companies in this job
      const companiesData = await apiClient.getJobCompanies(jobId);
      setCompanies(companiesData.companies || []);
      
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load job details');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchJobDetails();
    
    // Auto-refresh every 5 seconds if job is active
    const interval = setInterval(() => {
      if (jobStatus?.status === 'IN_PROGRESS' || jobStatus?.status === 'QUEUED') {
        fetchJobDetails();
      }
    }, 5000);
    
    return () => clearInterval(interval);
  }, [jobId, jobStatus?.status]);

  if (loading) {
    return (
      <div className="p-8">
        <LoadingSpinner text="Loading job details..." />
      </div>
    );
  }

  if (error || !jobStatus) {
    return (
      <div className="p-8">
        <ErrorMessage message={error || 'Job not found'} onRetry={fetchJobDetails} />
      </div>
    );
  }

  const progress = jobStatus.total_companies > 0
    ? ((jobStatus.completed + jobStatus.failed + jobStatus.skipped) / jobStatus.total_companies) * 100
    : 0;

  const isActive = jobStatus.status === 'QUEUED' || jobStatus.status === 'IN_PROGRESS';

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/analysis-queue')}
          className="flex items-center gap-2 text-primary-600 hover:text-primary-700 mb-4"
        >
          <ArrowLeft size={20} />
          Back to Analysis Queue
        </button>
        
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
              Analysis Job
            </h1>
            <p className="text-gray-600 mt-1">Job ID: {jobId}</p>
          </div>
          
          <div className="flex items-center gap-3">
            <span className={`px-4 py-2 rounded-lg text-sm font-semibold ${
              jobStatus.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
              jobStatus.status === 'IN_PROGRESS' ? 'bg-blue-100 text-blue-800' :
              jobStatus.status === 'FAILED' ? 'bg-red-100 text-red-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {jobStatus.status === 'QUEUED' && '⏳ Queued'}
              {jobStatus.status === 'IN_PROGRESS' && '🔄 In Progress'}
              {jobStatus.status === 'COMPLETED' && '✅ Completed'}
              {jobStatus.status === 'FAILED' && '❌ Failed'}
            </span>
            
            {isActive && (
              <button
                onClick={fetchJobDetails}
                disabled={refreshing}
                className="text-sm text-primary-600 hover:text-primary-700"
              >
                {refreshing ? 'Refreshing...' : 'Refresh'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Progress Card */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Overall Progress</h2>
        
        {/* Live Progress Indicator */}
        {isActive && jobStatus.current_company && (
          <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center gap-2 text-blue-800 mb-2">
              <div className="animate-pulse w-2 h-2 bg-blue-600 rounded-full"></div>
              <span className="font-medium">Currently analyzing:</span>
            </div>
            <div className="text-gray-900 font-semibold text-lg">{jobStatus.current_company}</div>
            {jobStatus.current_step && (
              <div className="text-sm text-gray-600 mt-1">
                Step: {jobStatus.current_step}
              </div>
            )}
          </div>
        )}

        {/* Progress Bar */}
        <div className="mb-6">
          <div className="flex justify-between text-sm text-gray-600 mb-2">
            <span>Progress: {jobStatus.completed + jobStatus.failed + jobStatus.skipped} / {jobStatus.total_companies}</span>
            <span className="font-semibold">{progress.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
            <div
              className={`h-4 rounded-full transition-all duration-500 ease-out ${
                isActive ? 'bg-primary-500' : jobStatus.status === 'COMPLETED' ? 'bg-green-500' : 'bg-red-500'
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-5 gap-4">
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <div className="text-3xl font-bold text-gray-800">{jobStatus.total_companies}</div>
            <div className="text-sm text-gray-600 mt-1">Total</div>
          </div>
          <div className="text-center p-4 bg-green-50 rounded-lg">
            <div className="text-3xl font-bold text-green-600">{jobStatus.completed}</div>
            <div className="text-sm text-gray-600 mt-1">Completed</div>
          </div>
          <div className="text-center p-4 bg-red-50 rounded-lg">
            <div className="text-3xl font-bold text-red-600">{jobStatus.failed}</div>
            <div className="text-sm text-gray-600 mt-1">Failed</div>
          </div>
          <div className="text-center p-4 bg-yellow-50 rounded-lg">
            <div className="text-3xl font-bold text-yellow-600">{jobStatus.skipped}</div>
            <div className="text-sm text-gray-600 mt-1">Skipped</div>
          </div>
          <div className="text-center p-4 bg-blue-50 rounded-lg">
            <div className="text-3xl font-bold text-blue-600">{jobStatus.total_tokens.toLocaleString()}</div>
            <div className="text-sm text-gray-600 mt-1">Tokens Used</div>
          </div>
        </div>

        {/* Time Information */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Started:</span>
              <span className="ml-2 font-medium">
                {jobStatus.started_at ? new Date(jobStatus.started_at).toLocaleString() : 'Not started'}
              </span>
            </div>
            <div>
              <span className="text-gray-600">Completed:</span>
              <span className="ml-2 font-medium">
                {jobStatus.completed_at ? new Date(jobStatus.completed_at).toLocaleString() : 'In progress'}
              </span>
            </div>
          </div>
          
          {isActive && jobStatus.estimated_time_remaining && (
            <div className="mt-2 text-sm">
              <span className="text-gray-600">Estimated time remaining:</span>
              <span className="ml-2 font-medium text-blue-600">
                {Math.ceil(jobStatus.estimated_time_remaining / 60)} minutes
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Companies List */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold mb-4">Companies in this Job ({companies.length})</h2>
        
        {companies.length === 0 ? (
          <InfoMessage message="No companies found for this job." />
        ) : (
          <div className="space-y-2">
            {companies.map((company, idx) => (
              <div 
                key={idx}
                className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex-1">
                  <div className="font-semibold text-gray-900">{company.name}</div>
                  <div className="text-sm text-gray-600 mt-1">
                    {company.ticker && <span className="mr-4">Ticker: {company.ticker}</span>}
                    {company.cik && <span>CIK: {company.cik}</span>}
                  </div>
                </div>
                
                <div className="flex items-center gap-4">
                  {/* Status Badge */}
                  {company.status === 'completed' && (
                    <div className="flex items-center gap-2 text-green-600">
                      <CheckCircle size={20} />
                      <span className="text-sm font-medium">Completed</span>
                    </div>
                  )}
                  {company.status === 'failed' && (
                    <div className="flex items-center gap-2 text-red-600">
                      <XCircle size={20} />
                      <span className="text-sm font-medium">Failed</span>
                    </div>
                  )}
                  {company.status === 'skipped' && (
                    <div className="flex items-center gap-2 text-yellow-600">
                      <AlertCircle size={20} />
                      <span className="text-sm font-medium">Skipped</span>
                    </div>
                  )}
                  {company.status === 'in_progress' && (
                    <div className="flex items-center gap-2 text-blue-600">
                      <Clock size={20} className="animate-spin" />
                      <span className="text-sm font-medium">In Progress</span>
                    </div>
                  )}
                  {!company.status && (
                    <div className="flex items-center gap-2 text-gray-400">
                      <Clock size={20} />
                      <span className="text-sm font-medium">Pending</span>
                    </div>
                  )}
                  
                  {/* View Insights Button */}
                  {company.status === 'completed' && company.company_id && (
                    <button
                      onClick={() => navigate(`/company-insights?id=${company.company_id}`)}
                      className="flex items-center gap-2 text-primary-600 hover:text-primary-700 text-sm font-medium"
                    >
                      View Insights
                      <ExternalLink size={16} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default JobDetails;
