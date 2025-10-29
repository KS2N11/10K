import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface Company {
  id: number;
  cik: string;
  name: string;
  ticker: string;
  industry: string | null;
  sector: string | null;
  market_cap: string | null;
}

export interface Analysis {
  id: number;
  company_id: number;
  company_name: string;
  company_ticker: string;
  company_cik: string;
  filing_date: string;
  completed_at: string | null;
  pain_points_count: number;
  matches_count: number;
  top_match_score: number;
  status: string;
}

export interface PainPoint {
  id: number;
  theme: string;
  rationale: string;
  confidence: number;
  quotes: string[];
  category: string | null;
}

export interface ProductMatch {
  id: number;
  product_id: string;
  product_name: string;
  fit_score: number;
  why_fits: string;
  evidence: string[];
}

export interface Pitch {
  id: number;
  company_name: string;
  company_ticker: string;
  persona: string;
  subject: string;
  body: string;
  overall_score: number;
  product_id: string;
  product_name: string;
  created_at: string;
}

export interface JobStatus {
  job_id: string;
  status: string;
  total_companies: number;
  completed: number;
  failed: number;
  skipped: number;
  current_company: string | null;
  current_step: string | null;
  estimated_time_remaining: number | null;
  total_tokens: number;
  started_at: string | null;
  completed_at: string | null;
  errors?: Array<{
    company: string;
    error: string;
  }>;
}

export interface CompanyDetails {
  analysis: {
    id: number;
    company_id: number;
    company_name: string;
    filing_date: string;
    accession_number: string;
    filing_path: string | null;
    status: string;
    time_taken_seconds: number;
    total_tokens_used: number;
    completed_at: string | null;
  };
  pain_points: PainPoint[];
  product_matches: ProductMatch[];
  pitches: Pitch[];
}

export interface Metrics {
  total_companies_analyzed: number;
  total_analyses_run: number;
  total_pain_points_found: number;
  total_pitches_generated: number;
  total_processing_time_seconds: number;
  avg_time_per_analysis: number;
  estimated_time_saved_hours: number;
  total_tokens_used: number;
  success_rate: number;
  avg_pain_points_per_company: number;
  avg_matches_per_company: number;
  top_industries: Array<{ industry: string; count: number }>;
  top_sectors: Array<{ sector: string; count: number }>;
}

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 300000, // 5 minutes for long-running queries (real-time market cap lookup)
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        console.log(`API Response: ${response.status} from ${response.config.url}`);
        return response;
      },
      (error) => {
        console.error('API Error:', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  // Health check
  async healthCheck() {
    const response = await this.client.get('/health');
    return response.data;
  }

  // Batch Analysis
  async startBatchAnalysis(params: {
    company_names?: string[];
    filters?: Record<string, any>;
    limit?: number;
    force_reanalyze?: boolean;
    selected_companies?: Array<{ cik: string; ticker: string; name: string }>;
  }) {
    const response = await this.client.post('/api/v2/analysis/batch', params);
    return response.data;
  }

  async getJobStatus(jobId: string): Promise<JobStatus> {
    const response = await this.client.get(`/api/v2/analysis/status/${jobId}`);
    return response.data;
  }

  // Companies
  async searchCompanies(params: {
    query?: string;
    market_cap?: string[];
    industry?: string[];
    sector?: string[];
    limit?: number;
    offset?: number;
  }): Promise<{ companies: Company[]; count: number }> {
    const response = await this.client.post('/api/v2/companies/search', params);
    return response.data;
  }

  async searchSECCompanies(params: {
    market_cap?: string[];
    industry?: string[];
    sector?: string[];
    limit?: number;
    use_realtime?: boolean;
  }): Promise<{ companies: Company[]; count: number; source: string; lookup_method?: string }> {
    const queryParams = params.use_realtime ? '?use_realtime=true' : '';
    const response = await this.client.post(`/api/v2/companies/search-sec${queryParams}`, {
      market_cap: params.market_cap,
      industry: params.industry,
      sector: params.sector,
      limit: params.limit
    });
    return response.data;
  }

  async searchCompanyByName(query: string, limit: number = 20): Promise<{ companies: Company[]; count: number; query: string; source: string }> {
    const response = await this.client.get('/api/v2/companies/search-by-name', {
      params: { query, limit }
    });
    return response.data;
  }

  async getCompanyAnalysis(companyId: number): Promise<CompanyDetails> {
    const response = await this.client.get(`/api/v2/companies/${companyId}/analysis`);
    return response.data;
  }

  // Analyses
  async getAllAnalyses(limit: number = 100, offset: number = 0): Promise<{ analyses: Analysis[]; count: number }> {
    const response = await this.client.get('/api/v2/analyses/all', { 
      params: { limit, offset } 
    });
    return response.data;
  }

  // Pitches
  async getTopPitches(minScore: number = 0, limit: number = 50): Promise<{ pitches: Pitch[]; count: number }> {
    const response = await this.client.get('/api/v2/pitches/top', { 
      params: { min_score: minScore, limit } 
    });
    return response.data;
  }

  // Metrics
  async getMetrics(): Promise<Metrics> {
    const response = await this.client.get('/api/v2/metrics/summary');
    return response.data;
  }

  // Filing Documents
  getFilingDocumentUrl(companyId: number): string {
    return `${API_BASE_URL}/api/v2/filings/${companyId}/document`;
  }

  // Catalog Management
  async getCurrentCatalog(): Promise<{ products: any[] }> {
    const response = await this.client.get('/api/v2/catalog/current');
    return response.data;
  }

  async uploadCatalog(params: {
    text_content: string;
    company_name?: string;
    merge_with_existing?: boolean;
  }): Promise<{ products_count: number; message: string }> {
    const response = await this.client.post('/api/v2/catalog/upload', params);
    return response.data;
  }

  async deleteProduct(productId: string): Promise<void> {
    await this.client.delete(`/api/v2/catalog/products/${productId}`);
  }
}

export const apiClient = new ApiClient();
export default apiClient;
