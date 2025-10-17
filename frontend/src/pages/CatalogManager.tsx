import React, { useState, useEffect } from 'react';
import { Package, Upload, Trash2, AlertCircle, CheckCircle, FileText, Plus, X } from 'lucide-react';
import apiClient from '../services/api';
import { LoadingSpinner, ErrorMessage } from '../components/common/Feedback';

interface Product {
  product_id: string;
  title: string;
  summary: string;
  capabilities: string[];
  icp: {
    industries: string[];
    min_emp: number;
  };
  proof_points: string[];
}

const CatalogManager: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  
  // Upload form state
  const [catalogText, setCatalogText] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [mergeWithExisting, setMergeWithExisting] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState('');

  useEffect(() => {
    fetchCatalog();
  }, []);

  const fetchCatalog = async () => {
    try {
      setLoading(true);
      setError('');
      const response = await fetch('http://localhost:8000/api/v2/catalog/current');
      const data = await response.json();
      setProducts(data.products || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load catalog');
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async () => {
    if (!catalogText.trim()) {
      setError('Please enter product/service descriptions');
      return;
    }

    try {
      setUploading(true);
      setError('');
      setUploadSuccess('');

      const response = await fetch('http://localhost:8000/api/v2/catalog/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text_content: catalogText,
          company_name: companyName || 'Your Company',
          merge_with_existing: mergeWithExisting
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const data = await response.json();
      setUploadSuccess(`✅ Successfully parsed and saved ${data.products_count} products!`);
      
      // Refresh catalog
      await fetchCatalog();
      
      // Reset form
      setCatalogText('');
      setCompanyName('');
      
      // Close modal after 2 seconds
      setTimeout(() => {
        setShowUploadModal(false);
        setUploadSuccess('');
      }, 2000);
      
    } catch (err: any) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (productId: string) => {
    if (!confirm(`Are you sure you want to delete this product?`)) {
      return;
    }

    try {
      const response = await fetch(`http://localhost:8000/api/v2/catalog/products/${productId}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error('Failed to delete product');
      }

      await fetchCatalog();
    } catch (err: any) {
      setError(err.message);
    }
  };

  if (loading) {
    return <LoadingSpinner text="Loading product catalog..." />;
  }

  return (
    <div className="p-8">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-3xl font-bold text-primary-500 flex items-center gap-3">
            <Package size={32} />
            Product Catalog Manager
          </h1>
          <p className="text-gray-600 mt-2">
            Manage your product/service catalog for analysis matching
          </p>
        </div>
        
        <button
          onClick={() => setShowUploadModal(true)}
          className="btn btn-primary flex items-center gap-2"
        >
          <Upload size={18} />
          Upload New Catalog
        </button>
      </div>

      {error && <ErrorMessage message={error} onRetry={fetchCatalog} />}

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Total Products/Services</p>
              <p className="text-3xl font-bold text-primary-500">{products.length}</p>
            </div>
            <Package size={40} className="text-primary-200" />
          </div>
        </div>
        
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Total Capabilities</p>
              <p className="text-3xl font-bold text-success-500">
                {products.reduce((sum, p) => sum + p.capabilities.length, 0)}
              </p>
            </div>
            <CheckCircle size={40} className="text-success-200" />
          </div>
        </div>
        
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Industries Covered</p>
              <p className="text-3xl font-bold text-accent-500">
                {new Set(products.flatMap(p => p.icp.industries)).size}
              </p>
            </div>
            <AlertCircle size={40} className="text-accent-200" />
          </div>
        </div>
      </div>

      {/* Product List */}
      {products.length === 0 ? (
        <div className="card text-center py-12">
          <Package size={48} className="mx-auto text-gray-400 mb-4" />
          <p className="text-gray-500 text-lg mb-4">
            No products in catalog yet
          </p>
          <button
            onClick={() => setShowUploadModal(true)}
            className="btn btn-primary mx-auto"
          >
            <Upload size={18} className="inline mr-2" />
            Upload Your First Catalog
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          {products.map((product) => (
            <div key={product.product_id} className="card hover:shadow-lg transition-shadow">
              <div className="flex justify-between items-start mb-4">
                <div className="flex-1">
                  <h3 className="text-xl font-bold text-gray-900">{product.title}</h3>
                  <p className="text-sm text-gray-600 mt-1">ID: {product.product_id}</p>
                </div>
                <button
                  onClick={() => handleDelete(product.product_id)}
                  className="text-red-500 hover:text-red-700 p-2 hover:bg-red-50 rounded"
                  title="Delete product"
                >
                  <Trash2 size={18} />
                </button>
              </div>

              <p className="text-gray-700 mb-4">{product.summary}</p>

              {/* Capabilities */}
              <div className="mb-4">
                <p className="text-sm font-semibold text-gray-700 mb-2">Capabilities:</p>
                <div className="flex flex-wrap gap-2">
                  {product.capabilities.map((cap, idx) => (
                    <span
                      key={idx}
                      className="bg-primary-100 text-primary-700 px-3 py-1 rounded-full text-sm"
                    >
                      {cap}
                    </span>
                  ))}
                </div>
              </div>

              {/* ICP */}
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <p className="text-sm font-semibold text-gray-700 mb-1">Target Industries:</p>
                  <p className="text-sm text-gray-600">{product.icp.industries.join(', ')}</p>
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-700 mb-1">Min Company Size:</p>
                  <p className="text-sm text-gray-600">{product.icp.min_emp}+ employees</p>
                </div>
              </div>

              {/* Proof Points */}
              <div>
                <p className="text-sm font-semibold text-gray-700 mb-2">Proof Points:</p>
                <ul className="space-y-1">
                  {product.proof_points.map((point, idx) => (
                    <li key={idx} className="text-sm text-gray-600 flex items-start gap-2">
                      <CheckCircle size={16} className="text-success-500 mt-0.5 flex-shrink-0" />
                      {point}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                  <Upload size={24} />
                  Upload Product Catalog
                </h2>
                <button
                  onClick={() => setShowUploadModal(false)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  <X size={24} />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Company Name (Optional)
                  </label>
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="e.g., Atidan Technologies"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Product/Service Descriptions
                  </label>
                  <p className="text-xs text-gray-500 mb-2">
                    Paste your product/service descriptions, brochures, or website content. 
                    The AI will automatically extract and format them.
                  </p>
                  <textarea
                    value={catalogText}
                    onChange={(e) => setCatalogText(e.target.value)}
                    placeholder="Paste your product descriptions here..."
                    rows={12}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent font-mono text-sm"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="merge"
                    checked={mergeWithExisting}
                    onChange={(e) => setMergeWithExisting(e.target.checked)}
                    className="w-4 h-4 text-primary-500"
                  />
                  <label htmlFor="merge" className="text-sm text-gray-700">
                    Merge with existing catalog (otherwise replaces completely)
                  </label>
                </div>

                {uploadSuccess && (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <p className="text-green-800 font-semibold">{uploadSuccess}</p>
                  </div>
                )}

                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <p className="text-red-800">{error}</p>
                  </div>
                )}

                <div className="flex gap-3 justify-end">
                  <button
                    onClick={() => setShowUploadModal(false)}
                    className="btn bg-gray-200 hover:bg-gray-300 text-gray-700"
                    disabled={uploading}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleUpload}
                    className="btn btn-primary flex items-center gap-2"
                    disabled={uploading || !catalogText.trim()}
                  >
                    {uploading ? (
                      <>
                        <LoadingSpinner size="sm" />
                        Parsing...
                      </>
                    ) : (
                      <>
                        <Upload size={18} />
                        Parse & Upload
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CatalogManager;
