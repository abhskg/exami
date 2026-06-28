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
  const [promptText, setPromptText] = useState('');
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
          new_raw_data: promptText || 'Trigger automatic deeper web search for this concept',
        }),
      });
      if (!res.ok) {
        throw new Error('Failed to deepen concept');
      }
      setDeepenSuccess(true);
      setPromptText('');
      fetchBody(); // reload the updated markdown
      setTimeout(() => setDeepenSuccess(false), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsDeepening(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg-secondary)', borderRadius: '12px', overflow: 'hidden' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid var(--border-color)', background: 'rgba(255, 255, 255, 0.02)' }}>
        <h2 style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>{conceptTitle}</h2>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '50%', color: 'var(--text-secondary)' }}>
          <X size={20} />
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
        {isLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
            <Loader2 size={32} className="animate-spin" style={{ marginBottom: '16px', color: 'var(--accent-primary)' }} />
            <p>Loading concept...</p>
          </div>
        ) : error ? (
          <div style={{ padding: '16px', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '12px', background: 'rgba(239, 68, 68, 0.05)', color: '#ef4444', textAlign: 'center' }}>
            {error}
          </div>
        ) : (
          <div style={{ color: 'var(--text-secondary)', lineHeight: 1.6, fontSize: '0.95rem' }}>
            {/* Simple Markdown Render - in a real app use react-markdown */}
            {body.split('\n').map((line, i) => {
              if (line.startsWith('## ')) {
                return (
                  <h3 key={i} style={{ fontSize: '1.25rem', fontWeight: 700, marginTop: '24px', marginBottom: '8px', color: 'var(--text-primary)' }}>
                    {line.replace('## ', '')}
                  </h3>
                );
              }
              if (line.startsWith('### ')) {
                return (
                  <h4 key={i} style={{ fontSize: '1.1rem', fontWeight: 600, marginTop: '16px', marginBottom: '8px', color: 'var(--text-primary)' }}>
                    {line.replace('### ', '')}
                  </h4>
                );
              }
              if (line.startsWith('- ')) {
                return (
                  <li key={i} style={{ marginLeft: '16px', marginBottom: '4px', color: 'var(--text-secondary)' }}>
                    {line.replace('- ', '')}
                  </li>
                );
              }
              if (line.trim() === '') return <br key={i} />;
              return (
                <p key={i} style={{ marginBottom: '8px' }}>
                  {line}
                </p>
              );
            })}
          </div>
        )}
      </div>

      <div style={{ padding: '16px', borderTop: '1px solid var(--border-color)', background: 'rgba(255, 255, 255, 0.01)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <textarea
          placeholder="How would you like to refine or deepen this concept? (e.g. 'Add more examples', 'Explain the history')"
          value={promptText}
          onChange={(e) => setPromptText(e.target.value)}
          disabled={isDeepening}
          style={{
            width: '100%',
            minHeight: '60px',
            padding: '12px',
            borderRadius: '8px',
            background: 'rgba(0,0,0,0.2)',
            border: '1px solid var(--border-color)',
            color: 'var(--text-primary)',
            fontSize: '0.9rem',
            resize: 'vertical'
          }}
        />
        <button
          className="btn btn-primary"
          onClick={handleDeepen}
          disabled={isDeepening}
          style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
        >
          {isDeepening ? (
            <Loader2 size={16} className="animate-spin" />
          ) : deepenSuccess ? (
            <Check size={16} style={{ color: '#10b981' }} />
          ) : (
            <PlusCircle size={16} />
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
