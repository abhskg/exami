import React, { useEffect, useState } from 'react';
import { Loader2, CheckCircle, AlertTriangle, Save, X } from 'lucide-react';

interface ReviewPanelProps {
  apiUrl: string;
  token: string | null;
  jobId: string;
  topicId: string;
  documentId: string;
  onComplete: () => void;
}

export const ReviewPanel: React.FC<ReviewPanelProps> = ({
  apiUrl,
  token,
  jobId,
  topicId,
  documentId,
  onComplete,
}) => {
  const [concepts, setConcepts] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStaged = async () => {
      try {
        const res = await fetch(`${apiUrl}/api/jobs/${jobId}/staged-concepts`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error('Failed to fetch staged concepts');
        const data = await res.json();
        setConcepts(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };
    fetchStaged();
  }, [apiUrl, token, jobId]);

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      const res = await fetch(`${apiUrl}/api/knowledge/${topicId}/review`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          job_id: jobId,
          document_id: documentId,
          approved_concepts: concepts,
        }),
      });
      if (!res.ok) throw new Error('Failed to submit review');
      onComplete();
    } catch (err: any) {
      setError(err.message);
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8 bg-white rounded-lg shadow border border-gray-200">
        <Loader2 className="w-6 h-6 animate-spin text-indigo-600 mr-3" />
        <span className="text-gray-600">Loading staged concepts for review...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-red-500 p-4 border border-red-200 bg-red-50 rounded-lg">{error}</div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
      <h2 className="text-xl font-semibold mb-4 text-gray-800">Review Extracted Concepts</h2>
      <p className="text-sm text-gray-500 mb-6">
        The AI has extracted the following OKF concepts. Flagged concepts require your attention.
      </p>

      <div className="space-y-4 max-h-[60vh] overflow-y-auto mb-6 pr-2">
        {concepts.map((concept, idx) => (
          <div
            key={idx}
            className={`p-4 border rounded-md ${concept.flagged ? 'border-amber-300 bg-amber-50' : 'border-gray-200'}`}
          >
            <div className="flex justify-between items-start mb-2">
              <h3 className="font-bold text-gray-800 flex items-center gap-2">
                {concept.flagged ? (
                  <AlertTriangle className="w-5 h-5 text-amber-500" />
                ) : (
                  <CheckCircle className="w-5 h-5 text-green-500" />
                )}
                {concept.title}
              </h3>
              <span className="text-xs font-mono bg-white px-2 py-1 rounded border border-gray-300">
                Conf: {Math.round(concept.confidence * 100)}%
              </span>
            </div>
            <p className="text-sm text-gray-600 mb-2">{concept.description}</p>
            {concept.flagged && (
              <p className="text-xs text-amber-700 bg-amber-100 p-2 rounded mt-2">
                <strong>Reason:</strong> {concept.flagged_reason}
              </p>
            )}
          </div>
        ))}
      </div>

      <div className="flex justify-end pt-4 border-t border-gray-100">
        <button
          onClick={handleSubmit}
          disabled={isSubmitting}
          className="flex items-center gap-2 bg-indigo-600 text-white px-6 py-2 rounded-md hover:bg-indigo-700 disabled:opacity-50 font-medium"
        >
          {isSubmitting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          Approve All Concepts
        </button>
      </div>
    </div>
  );
};
