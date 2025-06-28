import React, { useState, useEffect, useImperativeHandle, forwardRef } from 'react';
import { useClassContext } from '../context/ClassContext';
import { useDocumentRefresh } from '../context/DocumentRefreshContext';
import { useUserContext } from '../context/UserContext';

const POLL_INTERVAL = 5000; // 5 seconds

const ClassSelector = forwardRef((_, ref) => {
  const { classes, selectedClass, addClass, selectClass, deleteClass } = useClassContext();
  const { refreshCount } = useDocumentRefresh();
  const { token, usage } = useUserContext();
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newClassName, setNewClassName] = useState('');
  const [documents, setDocuments] = useState<any[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [presignedUrls, setPresignedUrls] = useState<Record<string, string>>({});
  const [urlCacheExpiry, setUrlCacheExpiry] = useState<Record<string, number>>({});
  const [deletingDocId, setDeletingDocId] = useState<string | null>(null);

  // Document fetch logic as a function
  const refreshDocuments = async () => {
    if (!selectedClass) {
      setDocuments([]);
      return;
    }
    setLoadingDocs(true);
    try {
      console.log('Fetching documents for class:', selectedClass.id);
      const res = await fetch(`/api/documents?class_id=${selectedClass.id}`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
      console.log('Documents API response status:', res.status);
      if (res.ok) {
        const data = await res.json();
        console.log('Documents API response data:', data);
        setDocuments(data);
      } else {
        console.log('Documents API error:', res.status, res.statusText);
        setDocuments([]);
      }
    } catch (err) {
      console.error('Documents API exception:', err);
      setDocuments([]);
    }
    setLoadingDocs(false);
  };

  // Expose refreshDocuments to parent via ref
  useImperativeHandle(ref, () => ({
    refreshDocuments,
  }));

  useEffect(() => {
    refreshDocuments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedClass, refreshCount]);

  // Polling for document status updates
  useEffect(() => {
    if (!selectedClass || documents.length === 0) return;
    const hasPending = documents.some(doc => doc.status && doc.status !== 'processed');
    if (!hasPending) return;
    const interval = setInterval(() => {
      refreshDocuments();
    }, POLL_INTERVAL);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedClass, documents]);

  const handleDeleteDocument = async (docId: string) => {
    if (deletingDocId) return; // Prevent multiple deletes
    if (!window.confirm('Delete this document?')) return;
    setDeletingDocId(docId);
    await fetch(`/api/documents/${docId}`, { 
      method: 'DELETE',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
    });
    setDeletingDocId(null);
    refreshDocuments();
  };

  const handleCreateClass = (e: React.FormEvent) => {
    e.preventDefault();
    if (newClassName.trim()) {
      addClass(newClassName.trim());
      setNewClassName('');
      setIsModalOpen(false);
    }
  };

  const getBatchPresignedUrls = async (docIds: string[]) => {
    try {
      const res = await fetch('/api/presign/batch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ document_ids: docIds }),
      });
      if (res.ok) {
        const data = await res.json();
        return data;
      }
    } catch (err) {
      console.error('Failed to get batch presigned URLs:', err);
    }
    return {};
  };

  const getPresignedUrl = async (docId: string) => {
    // Check cache first
    const now = Date.now();
    const expiry = urlCacheExpiry[docId] || 0;
    
    if (presignedUrls[docId] && now < expiry) {
      return presignedUrls[docId];
    }
    
    // Fetch new URL
    const urls = await getBatchPresignedUrls([docId]);
    const url = urls[docId];
    
    if (url) {
      // Cache for 50 minutes (URLs expire in 1 hour)
      setPresignedUrls(prev => ({ ...prev, [docId]: url }));
      setUrlCacheExpiry(prev => ({ ...prev, [docId]: now + (50 * 60 * 1000) }));
    }
    
    return url;
  };

  // Pre-fetch URLs when documents load
  useEffect(() => {
    if (documents.length > 0) {
      const docIds = documents.map(doc => doc.id || doc.document_id);
      getBatchPresignedUrls(docIds).then(urls => {
        const now = Date.now();
        const expiry = now + (50 * 60 * 1000); // 50 minutes
        
        setPresignedUrls(prev => ({ ...prev, ...urls }));
        const newExpiry = { ...urlCacheExpiry };
        docIds.forEach(id => {
          if (urls[id]) {
            newExpiry[id] = expiry;
          }
        });
        setUrlCacheExpiry(newExpiry);
      });
    }
  }, [documents, token]);

  return (
    <div className="w-80 bg-white shadow-lg border-r border-gray-200 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-800">Classes</h2>
      </div>

      {/* Class Selector Sidebar */}
      <div className="p-4">
        <div className="relative">
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="w-full flex items-center justify-between px-3 py-2 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <span>{selectedClass?.name || 'Select a class'}</span>
            <svg className="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {/* Dropdown Menu */}
          {isDropdownOpen && (
            <div className="absolute z-10 mt-1 w-full bg-white shadow-lg border border-gray-200 rounded-md">
              <div className="py-1">
                {classes.map((cls) => (
                  <div key={cls.id} className={`flex items-center justify-between px-3 text-sm hover:bg-gray-100 ${
                      selectedClass?.id === cls.id ? 'bg-blue-50' : ''
                  }`}>
                      <button
                          onClick={() => {
                              selectClass(cls.id);
                              setIsDropdownOpen(false);
                          }}
                          className={`w-full text-left py-2 ${selectedClass?.id === cls.id ? 'text-blue-700' : 'text-gray-700'}`}
                      >
                          {cls.name}
                      </button>
                      <button
                          onClick={(e) => {
                              e.stopPropagation();
                              if (window.confirm(`Are you sure you want to delete "${cls.name}"? This action cannot be undone.`)) {
                                  deleteClass(cls.id);
                              }
                          }}
                          className="text-gray-400 hover:text-red-600 p-1 rounded-full"
                          aria-label={`Delete ${cls.name}`}
                      >
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                      </button>
                  </div>
                ))}
                <div className="border-t border-gray-200">
                  <button
                    onClick={() => {
                      setIsModalOpen(true);
                      setIsDropdownOpen(false);
                    }}
                    className="w-full text-left px-3 py-2 text-sm text-blue-600 hover:bg-blue-50"
                  >
                    + Create New Class
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Selected Class Info */}
        {selectedClass && (
          <div className="mt-4 p-3 bg-gray-50 rounded-md">
            <h3 className="text-sm font-medium text-gray-900">{selectedClass.name}</h3>
            {'createdAt' in selectedClass && selectedClass.createdAt ? (
              <p className="text-xs text-gray-500 mt-1">
                Created {new Date((selectedClass as any).createdAt).toLocaleDateString()}
              </p>
            ) : null}
            {/* Document List */}
            <div className="mt-4">
              <h4 className="text-xs font-semibold text-gray-700 mb-2">Documents</h4>
              {loadingDocs ? (
                <p className="text-xs text-gray-400">Loading...</p>
              ) : documents.length === 0 ? (
                <p className="text-xs text-gray-400">No documents uploaded.</p>
              ) : (
                <ul className="space-y-2">
                  {documents.map((doc) => (
                    <li key={doc.id || doc.document_id} className="flex items-center justify-between text-xs bg-white rounded px-2 py-1 border overflow-hidden">
                      <div className="flex items-center min-w-0">
                        {/* File icon */}
                        <svg className="h-4 w-4 text-gray-400 flex-shrink-0 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7V3a1 1 0 011-1h8a1 1 0 011 1v18a1 1 0 01-1 1H8a1 1 0 01-1-1v-4" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h10M7 7v10m0 0h10" />
                        </svg>
                        {/* Truncated filename with tooltip */}
                        <span className="truncate max-w-[110px]" title={doc.filename || doc.name}>{doc.filename || doc.name}</span>
                        {/* Show status only if not processed */}
                        {doc.status && doc.status !== 'processed' && (
                          <span className="ml-2 px-2 py-0.5 rounded bg-yellow-100 text-yellow-800 text-[10px] font-semibold">{doc.status}</span>
                        )}
                      </div>
                      {/* Download button */}
                      <button
                        className="ml-2 text-gray-400 hover:text-blue-600 h-6 w-6 rounded-full flex items-center justify-center hover:bg-blue-100 transition-colors duration-200"
                        title="Download document"
                        style={{ flexShrink: 0 }}
                        onClick={async () => {
                          const url = await getPresignedUrl(doc.id || doc.document_id);
                          if (url) {
                            window.open(url, '_blank');
                          } else {
                            alert('Failed to get download link');
                          }
                        }}
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" />
                        </svg>
                      </button>
                      {/* Delete button or Deleting... */}
                      {deletingDocId === (doc.id || doc.document_id) ? (
                        <span className="ml-2 text-gray-400">Deleting...</span>
                      ) : (
                        <button
                          className="ml-2 text-gray-400 hover:text-red-600 h-6 w-6 rounded-full flex items-center justify-center hover:bg-red-100 transition-colors duration-200"
                          onClick={() => handleDeleteDocument(doc.id || doc.document_id)}
                          title="Delete document"
                          style={{ flexShrink: 0 }}
                          disabled={!!deletingDocId}
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Create Class Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Create New Class</h3>
              <form onSubmit={handleCreateClass}>
                <div className="mb-4">
                  <label htmlFor="className" className="block text-sm font-medium text-gray-700 mb-2">
                    Class Name
                  </label>
                  <input
                    type="text"
                    id="className"
                    value={newClassName}
                    onChange={(e) => setNewClassName(e.target.value)}
                    placeholder="e.g., CMSC351, MATH240"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    autoFocus
                  />
                </div>
                <div className="flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => {
                      setIsModalOpen(false);
                      setNewClassName('');
                    }}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    Create
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
});

export default ClassSelector as React.FC<any>; 