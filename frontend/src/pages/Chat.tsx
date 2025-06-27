import React, { useState, useEffect, useRef } from 'react';
import { useClassContext } from '../context/ClassContext';
import { useDocumentRefresh } from '../context/DocumentRefreshContext';
import { useUserContext } from '../context/UserContext';

const Chat: React.FC = () => {
  const { selectedClass } = useClassContext();
  const { refreshCount } = useDocumentRefresh();
  const { token } = useUserContext();
  const [messages, setMessages] = useState<Array<{id: number, text: string, isUser: boolean, citations?: any[]}>>([
    { id: 1, text: "Hello! I'm your ClassGPT assistant. Ask me anything about your course materials.", isUser: false }
  ]);
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<null | HTMLDivElement>(null);
  const [docIdToFilename, setDocIdToFilename] = useState<Record<string, string>>({});

  const refreshDocumentMapping = async () => {
    if (!selectedClass) return;
    try {
      const res = await fetch(`/api/documents?class_id=${selectedClass.id}`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const docs = await res.json();
        const map: Record<string, string> = {};
        docs.forEach((doc: any) => { map[doc.id] = doc.filename; });
        setDocIdToFilename(map);
      }
    } catch (err) {
      console.error('Failed to refresh document mapping:', err);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Reset chat when class changes
    setMessages([
      { id: 1, text: "Hello! I'm your ClassGPT assistant. Ask me anything about your course materials.", isUser: false }
    ]);
    // Fetch document list for mapping document_id to filename
    if (selectedClass) {
      fetch(`/api/documents?class_id=${selectedClass.id}`)
        .then(res => res.json())
        .then(docs => {
          const map: Record<string, string> = {};
          docs.forEach((doc: any) => { map[doc.id] = doc.filename; });
          setDocIdToFilename(map);
        });
    } else {
      setDocIdToFilename({});
    }
  }, [selectedClass, refreshCount]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || !selectedClass) return;

    const userMessage = { id: Date.now(), text: inputValue, isUser: true };
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');

    try {
      const res = await fetch('/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          query: userMessage.text,
          class_id: selectedClass.id,
          top_k: 3
        })
      });
      let data;
      try {
        data = await res.json();
      } catch (jsonErr) {
        throw new Error('Invalid JSON response from server.');
      }
      if (!res.ok) {
        const errorMsg = data?.detail || data?.message || 'Unknown error from backend.';
        throw new Error(errorMsg);
      }
      // Collect citations from returned chunks, deduplicated by filename+page_number
      const seen = new Set<string>();
      let citations = (data.chunks || []).map((chunk: any) => ({
        document_id: chunk.document_id,
        page_number: chunk.page_number,
        filename: docIdToFilename[chunk.document_id] || 'Unknown document'
      })).filter((c: {filename: string, page_number: number}) => {
        // Skip citations for unknown documents
        if (c.filename === 'Unknown document') return false;
        const key = `${c.filename}|${c.page_number}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });

      // If we have unknown documents, refresh the mapping and retry
      const hasUnknownDocuments = (data.chunks || []).some((chunk: any) => !docIdToFilename[chunk.document_id]);
      if (hasUnknownDocuments) {
        await refreshDocumentMapping();
        // Retry citation generation with updated mapping
        const seenRetry = new Set<string>();
        citations = (data.chunks || []).map((chunk: any) => ({
          document_id: chunk.document_id,
          page_number: chunk.page_number,
          filename: docIdToFilename[chunk.document_id] || 'Unknown document'
        })).filter((c: {filename: string, page_number: number}) => {
          if (c.filename === 'Unknown document') return false;
          const key = `${c.filename}|${c.page_number}`;
          if (seenRetry.has(key)) return false;
          seenRetry.add(key);
          return true;
        });
      }
      const aiMessage = {
        id: Date.now() + 1,
        text: data.answer || 'Sorry, I could not find an answer.',
        isUser: false,
        citations
      };
      setMessages(prev => [...prev, aiMessage]);
    } catch (err: any) {
      const aiMessage = {
        id: Date.now() + 1,
        text: `Sorry, there was an error contacting the assistant. ${err.message ? 'Details: ' + err.message : ''}`,
        isUser: false
      };
      setMessages(prev => [...prev, aiMessage]);
    }
  };

  return (
    <div className="h-full flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-4xl mx-auto">
                {selectedClass ? (
                    <div className="space-y-5">
                        {messages.map((message) => (
                        <div
                            key={message.id}
                            className={`flex items-end ${message.isUser ? 'justify-end' : 'justify-start'}`}
                        >
                            <div
                            className={`max-w-xl px-4 py-3 rounded-2xl shadow ${
                                message.isUser
                                ? 'bg-blue-600 text-white'
                                : 'bg-white text-gray-800'
                            }`}
                            >
                            <p className="text-base">{message.text}</p>
                            {/* Citations for AI messages */}
                            {message.citations && message.citations.length > 0 && message.text.trim().toLowerCase() !== "i don't know." && (
                              <div className="mt-2 text-xs text-gray-500">
                                Sources: {message.citations.map((c, i) => (
                                  <span key={i} className="mr-2">
                                    {c.filename}{c.page_number && c.page_number > 0 ? `, page ${c.page_number}` : ''}
                                  </span>
                                ))}
                              </div>
                            )}
                            </div>
                        </div>
                        ))}
                        <div ref={messagesEndRef} />
                    </div>
                ) : (
                    <div className="h-full flex items-center justify-center">
                        <div className="text-center text-gray-500">
                        <svg className="mx-auto h-16 w-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                        <h3 className="text-xl font-medium text-gray-700">No class selected</h3>
                        <p className="text-base mt-1">Select a class from the sidebar to start chatting.</p>
                        </div>
                    </div>
                )}
            </div>
        </div>

        {/* Input */}
        <div className="bg-white border-t p-4 shadow-inner">
            <div className="max-w-4xl mx-auto">
            <form onSubmit={handleSubmit} className="flex space-x-4 items-center">
                <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder={selectedClass ? `Ask a question about ${selectedClass.name}...` : "Select a class to start"}
                disabled={!selectedClass}
                className="flex-1 w-full border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                />
                <button
                type="submit"
                disabled={!selectedClass || !inputValue.trim()}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-bold px-6 py-3 rounded-lg transition duration-200"
                >
                Send
                </button>
            </form>
            </div>
        </div>
    </div>
  );
};

export default Chat; 