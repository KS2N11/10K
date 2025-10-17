import React, { useState, useEffect } from 'react';
import { Target, Sliders, ChevronDown, ChevronUp, Mail, Copy, Building2, Package } from 'lucide-react';
import apiClient, { Pitch } from '../services/api';
import { LoadingSpinner, ErrorMessage, InfoMessage } from '../components/common/Feedback';

// Full implementation mirroring Streamlit's top_pitches.py
const TopPitches: React.FC = () => {
  const [pitches, setPitches] = useState<Pitch[]>([]);
  const [minScore, setMinScore] = useState(75);
  const [personaFilter, setPersonaFilter] = useState<string[]>(['All']);
  const [limit, setLimit] = useState(50);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedPitchId, setExpandedPitchId] = useState<number | null>(null);

  const personas = ['All', 'CEO', 'CFO', 'CTO', 'CIO', 'COO', 'VP', 'Director', 'Manager'];

  useEffect(() => {
    fetchPitches();
  }, [minScore, limit, personaFilter]);

  const fetchPitches = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await apiClient.getTopPitches(minScore, limit);
      
      // Filter by persona
      let filtered = data.pitches;
      if (personaFilter.length > 0 && !personaFilter.includes('All')) {
        filtered = filtered.filter(pitch =>
          personaFilter.some(persona => pitch.persona?.includes(persona))
        );
      }
      
      setPitches(filtered);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const togglePersona = (persona: string) => {
    if (persona === 'All') {
      setPersonaFilter(['All']);
    } else {
      const newFilter = personaFilter.includes('All')
        ? [persona]
        : personaFilter.includes(persona)
        ? personaFilter.filter(p => p !== persona)
        : [...personaFilter, persona];
      
      setPersonaFilter(newFilter.length === 0 ? ['All'] : newFilter);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 85) return 'bg-success-500';
    if (score >= 75) return 'bg-yellow-500';
    return 'bg-blue-500';
  };

  const getScoreBadgeColor = (score: number) => {
    if (score >= 85) return 'bg-success-500';
    if (score >= 75) return 'bg-yellow-500';
    return 'bg-blue-500';
  };

  const copyToClipboard = (pitch: Pitch) => {
    const text = `Subject: ${pitch.subject}\n\n${pitch.body}`;
    navigator.clipboard.writeText(text);
    alert('Pitch copied to clipboard!');
  };

  const avgScore = pitches.length > 0
    ? Math.round(pitches.reduce((sum, p) => sum + p.overall_score, 0) / pitches.length)
    : 0;
  const maxScore = pitches.length > 0
    ? Math.max(...pitches.map(p => p.overall_score))
    : 0;
  const uniqueCompanies = new Set(pitches.map(p => p.company_name)).size;

  if (loading) {
    return <LoadingSpinner text="Loading top pitches..." />;
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-primary-500 flex items-center gap-3">
        <Target size={32} />
        Best Opportunities
      </h1>
      <p className="text-gray-600 mt-2">Discover the highest-scoring sales pitches across your analyzed companies</p>

      {/* Filters */}
      <div className="card mt-6">
        <div className="flex items-center gap-2 mb-4">
          <Sliders size={20} className="text-gray-700" />
          <h3 className="font-bold text-gray-900">Filters</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Min Score Slider */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Minimum Score: {minScore}
            </label>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-500"
            />
            <p className="text-xs text-gray-500 mt-1">Only show pitches with scores ≥ {minScore}</p>
          </div>

          {/* Persona Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Target Persona
            </label>
            <div className="flex flex-wrap gap-2">
              {personas.map(persona => (
                <button
                  key={persona}
                  onClick={() => togglePersona(persona)}
                  className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                    personaFilter.includes(persona)
                      ? 'bg-primary-500 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  {persona}
                </button>
              ))}
            </div>
          </div>

          {/* Max Results */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Max Results: {limit}
            </label>
            <input
              type="number"
              min="10"
              max="200"
              step="10"
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
        </div>
      </div>

      {error && <ErrorMessage message={error} onRetry={fetchPitches} />}

      {pitches.length === 0 && !loading && !error && (
        <InfoMessage message={`No pitches found with score ≥ ${minScore}. Try lowering the threshold!`} />
      )}

      {pitches.length > 0 && (
        <>
          {/* Summary Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
            <div className="card text-center">
              <p className="text-gray-600 text-sm">Total Pitches</p>
              <p className="text-3xl font-bold text-primary-500 mt-1">{pitches.length}</p>
            </div>
            <div className="card text-center">
              <p className="text-gray-600 text-sm">Avg Score</p>
              <p className="text-3xl font-bold text-primary-500 mt-1">{avgScore}</p>
            </div>
            <div className="card text-center">
              <p className="text-gray-600 text-sm">Top Score</p>
              <p className="text-3xl font-bold text-success-500 mt-1">{maxScore}</p>
            </div>
            <div className="card text-center">
              <p className="text-gray-600 text-sm">Companies</p>
              <p className="text-3xl font-bold text-primary-500 mt-1">{uniqueCompanies}</p>
            </div>
          </div>

          {/* Pitch Cards */}
          <div className="space-y-4 mt-6">
            {pitches.map((pitch, index) => (
              <div key={pitch.id} className="pitch-card hover:shadow-lg transition-shadow">
                {/* Header */}
                <div className="flex justify-between items-start mb-4">
                  <div className="flex-1">
                    <h3 className="text-xl font-bold text-gray-900">
                      #{index + 1}. {pitch.company_name} ({pitch.company_ticker})
                    </h3>
                    <div className="flex flex-wrap gap-2 mt-2 text-sm text-gray-600">
                      <span className="flex items-center gap-1">
                        <Building2 size={14} />
                        Target: <strong>{pitch.persona}</strong>
                      </span>
                      <span className="flex items-center gap-1">
                        <Package size={14} />
                        Product: <strong>{pitch.product_name}</strong>
                      </span>
                      <span className="text-gray-500">
                        {new Date(pitch.created_at || '').toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                  <div className={`${getScoreBadgeColor(pitch.overall_score)} text-white px-4 py-2 rounded-lg font-bold text-lg`}>
                    {pitch.overall_score}/100
                  </div>
                </div>

                {/* Subject Preview */}
                <p className="text-gray-900 font-medium text-lg mb-3">
                  <strong>Subject:</strong> {pitch.subject}
                </p>

                {/* Expand Button */}
                <button
                  onClick={() => setExpandedPitchId(expandedPitchId === pitch.id ? null : pitch.id)}
                  className="w-full py-2 px-4 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg flex items-center justify-center gap-2 transition-colors"
                >
                  <Mail size={18} />
                  {expandedPitchId === pitch.id ? (
                    <>
                      <ChevronUp size={18} />
                      Hide Full Pitch
                    </>
                  ) : (
                    <>
                      <ChevronDown size={18} />
                      View Full Pitch
                    </>
                  )}
                </button>

                {/* Expanded Content */}
                {expandedPitchId === pitch.id && (
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <h4 className="font-bold text-gray-900 mb-2">Message:</h4>
                    <div className="bg-gray-50 p-4 rounded-lg border-l-4 border-primary-500">
                      <pre className="whitespace-pre-wrap text-gray-800 leading-relaxed font-sans">
                        {pitch.body}
                      </pre>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex gap-3 mt-4">
                      <button
                        onClick={() => copyToClipboard(pitch)}
                        className="flex-1 btn-primary flex items-center justify-center gap-2"
                      >
                        <Copy size={18} />
                        Copy to Clipboard
                      </button>
                      <a
                        href={`mailto:?subject=${encodeURIComponent(pitch.subject)}&body=${encodeURIComponent(pitch.body)}`}
                        className="flex-1 bg-success-500 hover:bg-success-600 text-white px-4 py-2 rounded-lg flex items-center justify-center gap-2 transition-colors"
                      >
                        <Mail size={18} />
                        Open in Email
                      </a>
                    </div>
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

export default TopPitches;

