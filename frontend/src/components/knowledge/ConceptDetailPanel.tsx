import React, { useEffect, useState } from 'react';
import { X, Loader2, PlusCircle, Check } from 'lucide-react';

interface ConceptDetailPanelProps {
  apiUrl: string;
  token: string | null;
  topicId: string;
  conceptSlug: string;
  conceptTitle: string;
  onClose: () => void;
}

export const ConceptDetailPanel: React.FC<ConceptDetailPanelProps> = ({
  apiUrl,
  token,
  topicId,
  conceptSlug,
  conceptTitle,
  onClose,
}) => {
  const [body, setBody] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [isDeepening, setIsDeepening] = useState(false);
  const [deepenSuccess, setDeepenSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchBody = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiUrl}/api/knowledge/${topicId}/concept/${conceptSlug}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        setError('Failed to fetch concept details');
        return;
      }
      const data = await res.json();
      setBody(data.body);
    } catch (err) {
      setError('Network error loading concept');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchBody();
  }, [apiUrl, token, topicId, conceptSlug]);

  const handleDeepen = async () => {
    setIsDeepening(true);
    setDeepenSuccess(false);
    setError(null);
    try {
      const res = await fetch(`${apiUrl}/api/knowledge/${topicId}/concept/${conceptSlug}/deepen`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mode: 'merge',
          new_raw_data: 'Trigger automatic deeper web search for this concept',
        }),
      });
      if (!res.ok) {
        throw new Error('Failed to deepen concept');
      }
      setDeepenSuccess(true);
      fetchBody(); // reload the updated markdown
      setTimeout(() => setDeepenSuccess(false), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsDeepening(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="flex justify-between items-center p-4 border-b border-gray-100">
        <h2 className="text-lg font-semibold text-gray-800">{conceptTitle}</h2>
        <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-full">
          <X className="w-5 h-5 text-gray-500" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <Loader2 className="w-8 h-8 animate-spin mb-4" />
            <p>Loading concept...</p>
          </div>
        ) : error ? (
          <div className="text-red-500 text-center p-4">{error}</div>
        ) : (
          <div className="prose prose-sm prose-indigo max-w-none">
            {/* Simple Markdown Render - in a real app use react-markdown */}
            {body.split('\n').map((line, i) => {
              if (line.startsWith('## ')) {
                return (
                  <h3 key={i} className="text-md font-bold mt-6 mb-2 text-gray-800">
                    {line.replace('## ', '')}
                  </h3>
                );
              }
              if (line.startsWith('### ')) {
                return (
                  <h4 key={i} className="font-semibold mt-4 mb-2 text-gray-800">
                    {line.replace('### ', '')}
                  </h4>
                );
              }
              if (line.startsWith('- ')) {
                return (
                  <li key={i} className="ml-4 text-gray-700">
                    {line.replace('- ', '')}
                  </li>
                );
              }
              if (line.trim() === '') return <br key={i} />;
              return (
                <p key={i} className="mb-2 text-gray-700">
                  {line}
                </p>
              );
            })}
          </div>
        )}
      </div>

      <div className="p-4 border-t border-gray-100 bg-gray-50">
        <button
          className="w-full flex items-center justify-center gap-2 py-2 px-4 bg-indigo-50 text-indigo-700 rounded-md hover:bg-indigo-100 transition-colors text-sm font-medium disabled:opacity-50"
          onClick={handleDeepen}
          disabled={isDeepening}
        >
          {isDeepening ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : deepenSuccess ? (
            <Check className="w-4 h-4 text-green-600" />
          ) : (
            <PlusCircle className="w-4 h-4" />
          )}
          {isDeepening
            ? 'Researching deeper...'
            : deepenSuccess
              ? 'Concept Updated!'
              : `Go Deeper on ${conceptTitle}`}
        </button>
      </div>
    </div>
  );
};
