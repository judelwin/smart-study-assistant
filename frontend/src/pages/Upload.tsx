import React, { useState } from 'react';
import { useClassContext } from '../context/ClassContext';
import { useNavigate } from 'react-router-dom';
import { useDocumentRefresh } from '../context/DocumentRefreshContext';
import { useUserContext } from '../context/UserContext';

const Upload: React.FC = () => {
  const { selectedClass, selectClass } = useClassContext();
  const { triggerRefresh } = useDocumentRefresh();
  const { token, usage } = useUserContext();
  const [files, setFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const navigate = useNavigate();
  const [isUploading, setIsUploading] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const filesToAdd = Array.from(e.target.files);
      setFiles(prev => [...prev, ...filesToAdd]);
    }
  };

  const removeFile = (fileName: string) => {
    setFiles(prev => prev.filter(f => f.name !== fileName));
  };

  const handleDragEnter = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files) {
      const filesToAdd = Array.from(e.dataTransfer.files);
      setFiles(prev => [...prev, ...filesToAdd]);
    }
  };

  const handleUpload = async () => {
    if (!selectedClass || files.length === 0 || isUploading) return;
    
    setIsUploading(true);
    const formData = new FormData();
    formData.append('class_id', selectedClass.id);
    files.forEach(file => formData.append('files', file));
    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
      if (res.ok) {
        setFiles([]);
        setSuccessMsg('Upload successful!');
        selectClass(selectedClass.id);
        triggerRefresh();
        setTimeout(() => {
          setSuccessMsg('');
          navigate('/chat');
        }, 1200);
      } else {
        const err = await res.json();
        // Show user-friendly error messages
        if (err.detail) {
          alert(err.detail);
        } else if (res.status === 429) {
          alert('Too many uploads. Please wait before trying again.');
        } else if (res.status === 413) {
          alert('File too large. Maximum file size is 10MB.');
        } else {
          alert('Upload failed. Please try again.');
        }
      }
    } catch (err) {
      alert('Network error. Please check your connection and try again.');
    }
    setIsUploading(false);
  };

  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800">
            Upload Documents
          </h1>
          {selectedClass ? (
            <p className="text-lg text-gray-600 mt-2">
              Add materials to <span className="font-semibold text-blue-600">{selectedClass.name}</span>
            </p>
          ) : (
            <p className="text-lg text-gray-600 mt-2">
              Please select a class from the sidebar to upload documents.
            </p>
          )}
        </div>
        
        {selectedClass ? (
          <div className="bg-white shadow-xl rounded-lg p-8">
            <div 
              onDragEnter={handleDragEnter}
              onDragOver={handleDragEnter}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`border-2 border-dashed border-gray-300 rounded-lg p-12 text-center transition-colors duration-200 ${isDragging ? 'bg-blue-50 border-blue-400' : 'bg-gray-50'}`}
            >
              <div className="space-y-4">
                <div className="text-gray-400">
                  <svg className="mx-auto h-16 w-16" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                    <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
                <div>
                  <label htmlFor="file-upload" className="cursor-pointer bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-md transition duration-200 inline-block">
                    Choose files
                  </label>
                  <input id="file-upload" name="file-upload" type="file" className="sr-only" multiple onChange={handleFileChange} accept=".pdf,.docx,.pptx,.txt" />
                </div>
                <p className="text-sm text-gray-500">
                  or drag and drop
                </p>
                <p className="text-xs text-gray-500">
                  PDF, DOCX, PPTX, or TXT files up to 10MB
                </p>
              </div>
            </div>

            {files.length > 0 && (
                <div className="mt-8">
                    <h3 className="text-lg font-medium text-gray-800 mb-4">Selected Files:</h3>
                    <ul className="space-y-3 bg-gray-50 p-4 rounded-md border">
                        {files.map((file, index) => (
                            <li key={index} className="flex items-center justify-between text-sm p-2 rounded-md hover:bg-gray-200">
                                <span className="text-gray-800 truncate pr-2">{file.name}</span>
                                <div className="flex items-center space-x-2 flex-shrink-0">
                                    <span className="text-gray-500 text-xs w-20 text-right">{ (file.size / 1024 / 1024).toFixed(2) } MB</span>
                                    <button 
                                        onClick={() => removeFile(file.name)} 
                                        className="text-gray-400 hover:text-red-600 h-6 w-6 rounded-full flex items-center justify-center hover:bg-red-100 transition-colors duration-200"
                                        aria-label={`Remove ${file.name}`}
                                    >
                                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                        </svg>
                                    </button>
                                </div>
                            </li>
                        ))}
                    </ul>
                    <div className="mt-6 text-right">
                        <button
                            onClick={handleUpload}
                            className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-6 rounded-md transition duration-200 disabled:bg-gray-400"
                            disabled={files.length === 0 || isUploading}
                        >
                            {isUploading ? "Uploading..." : `Upload ${files.length} ${files.length === 1 ? 'File' : 'Files'}`}
                        </button>
                    </div>
                </div>
            )}
          </div>
        ) : (
          <div className="bg-white shadow rounded-lg p-12 text-center">
            <div className="text-gray-500">
              <svg className="mx-auto h-12 w-12 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h3 className="text-lg font-medium text-gray-700">No class selected</h3>
              <p className="text-sm mt-1">Select a class from the sidebar to start uploading documents.</p>
            </div>
          </div>
        )}
        {successMsg && (
          <div className="mb-4 text-green-700 bg-green-100 border border-green-300 rounded p-3 text-center font-semibold">
            {successMsg}
          </div>
        )}
      </div>
    </div>
  );
};

export default Upload; 