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
      <div className="glass-card" style={{ padding: '32px', textAlign: 'center', borderRadius: '16px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <Loader2 size={32} className="animate-spin" color="var(--accent-primary)" style={{ marginBottom: '16px' }} />
        <span style={{ color: 'var(--text-secondary)' }}>Loading staged concepts for review...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card" style={{ padding: '24px', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '12px', background: 'rgba(239, 68, 68, 0.05)' }}>
        <div style={{ color: '#ef4444', fontWeight: 600 }}>{error}</div>
      </div>
    );
  }

  return (
    <div className="glass-card" style={{ padding: '32px', borderRadius: '16px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', maxHeight: '85vh' }}>
      <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '8px', color: 'var(--text-primary)' }}>
        Review Extracted Concepts
      </h2>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '24px' }}>
        The AI has extracted the following OKF concepts. Flagged concepts require your attention.
      </p>

      <div style={{ flex: 1, overflowY: 'auto', paddingRight: '12px', display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '24px' }}>
        {concepts.map((concept, idx) => (
          <div
            key={idx}
            style={{
              padding: '20px',
              borderRadius: '12px',
              background: concept.flagged ? 'rgba(245, 158, 11, 0.05)' : 'rgba(255, 255, 255, 0.02)',
              border: concept.flagged ? '1px solid rgba(245, 158, 11, 0.3)' : '1px solid var(--border-color)',
              transition: 'all 0.2s ease',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                {concept.flagged ? (
                  <AlertTriangle size={20} color="#f59e0b" />
                ) : (
                  <CheckCircle size={20} color="#10b981" />
                )}
                {concept.title}
              </h3>
            </div>
            
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '16px', lineHeight: 1.6 }}>
              {concept.description}
            </p>
            
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {concept.tags && concept.tags.map((tag: string, tIdx: number) => (
                <span key={tIdx} style={{ fontSize: '0.75rem', padding: '4px 10px', borderRadius: '20px', background: 'rgba(99, 102, 241, 0.1)', color: 'var(--accent-primary)', border: '1px solid rgba(99, 102, 241, 0.2)' }}>
                  {tag}
                </span>
              ))}
            </div>
          </div>
        ))}
        {concepts.length === 0 && (
          <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)' }}>
            No concepts found.
          </div>
        )}
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
        <button
          className="btn btn-primary"
          onClick={handleSubmit}
          disabled={isSubmitting || concepts.length === 0}
          style={{ width: '100%', padding: '14px', fontSize: '1rem' }}
        >
          {isSubmitting ? (
            <>
              <Loader2 size={18} className="animate-spin" />
              <span>Finalizing Database...</span>
            </>
          ) : (
            <>
              <Save size={18} />
              <span>Approve All & Ingest</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
