import React, { useEffect, useRef, useState } from 'react';
import {
  AlertTriangle,
  BookOpen,
  Check,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Loader2,
  PlusCircle,
  Save,
  Sparkles,
  Trash2,
  WandSparkles,
  X,
} from 'lucide-react';

// ──────────────────────────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────────────────────────

interface StagedConcept {
  slug: string;
  title: string;
  description: string;
  body?: string;
  tags?: string[];
  related?: string[];
  confidence?: number;
  flagged?: boolean;
  flagged_reason?: string;
  depth_level?: number;
}

interface ReviewPanelProps {
  apiUrl: string;
  token: string | null;
  jobId: string;
  topicId: string;
  documentId: string;
  onComplete: () => void;
}

// ──────────────────────────────────────────────────────────────────────────────
// Minimal Markdown renderer (keeps external deps to zero)
// ──────────────────────────────────────────────────────────────────────────────

const MarkdownBody: React.FC<{ body: string }> = ({ body }) => (
  <div style={{ color: 'var(--text-secondary)', lineHeight: 1.7, fontSize: '0.9rem' }}>
    {body.split('\n').map((line, i) => {
      if (line.startsWith('## '))
        return (
          <h3
            key={i}
            style={{
              fontSize: '1.05rem',
              fontWeight: 700,
              marginTop: '20px',
              marginBottom: '6px',
              color: 'var(--text-primary)',
            }}
          >
            {line.replace('## ', '')}
          </h3>
        );
      if (line.startsWith('### '))
        return (
          <h4
            key={i}
            style={{
              fontSize: '0.95rem',
              fontWeight: 600,
              marginTop: '14px',
              marginBottom: '4px',
              color: 'var(--text-primary)',
            }}
          >
            {line.replace('### ', '')}
          </h4>
        );
      if (line.startsWith('- '))
        return (
          <li key={i} style={{ marginLeft: '20px', marginBottom: '4px' }}>
            {line.replace('- ', '')}
          </li>
        );
      if (line.trim() === '') return <br key={i} />;
      return (
        <p key={i} style={{ marginBottom: '6px' }}>
          {line}
        </p>
      );
    })}
  </div>
);

// ──────────────────────────────────────────────────────────────────────────────
// Inline concept card
// ──────────────────────────────────────────────────────────────────────────────

interface ConceptCardProps {
  concept: StagedConcept;
  apiUrl: string;
  token: string | null;
  jobId: string;
  onDelete: (slug: string) => void;
  onRefined: (slug: string, updatedBody: string) => void;
}

const ConceptCard: React.FC<ConceptCardProps> = ({
  concept,
  apiUrl,
  token,
  jobId,
  onDelete,
  onRefined,
}) => {
  const [expanded, setExpanded] = useState(false);
  const [showRefinePanel, setShowRefinePanel] = useState(false);
  const [refinePrompt, setRefinePrompt] = useState('');
  const [isRefining, setIsRefining] = useState(false);
  const [refineSuccess, setRefineSuccess] = useState(false);
  const [localBody, setLocalBody] = useState(concept.body || '');
  const [refineError, setRefineError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    if (!window.confirm(`Remove "${concept.title}" from the review list?`)) return;
    setIsDeleting(true);
    try {
      const res = await fetch(`${apiUrl}/api/jobs/${jobId}/staged-concepts/${concept.slug}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to remove concept');
      onDelete(concept.slug);
    } catch (err: any) {
      alert(err.message);
      setIsDeleting(false);
    }
  };

  const handleRefine = async () => {
    setIsRefining(true);
    setRefineError(null);
    try {
      const res = await fetch(
        `${apiUrl}/api/jobs/${jobId}/staged-concepts/${concept.slug}/refine`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: refinePrompt }),
        }
      );
      if (!res.ok) throw new Error('Failed to refine concept');
      const data = await res.json();
      setLocalBody(data.updated_body);
      onRefined(concept.slug, data.updated_body);
      setRefineSuccess(true);
      setRefinePrompt('');
      setShowRefinePanel(false);
      setTimeout(() => setRefineSuccess(false), 3000);
    } catch (err: any) {
      setRefineError(err.message);
    } finally {
      setIsRefining(false);
    }
  };

  const confidence = concept.confidence ?? 0;
  const confidenceColor =
    confidence >= 0.8 ? '#10b981' : confidence >= 0.6 ? '#f59e0b' : '#ef4444';

  return (
    <div
      style={{
        borderRadius: '14px',
        border: concept.flagged
          ? '1px solid rgba(245, 158, 11, 0.4)'
          : refineSuccess
            ? '1px solid rgba(16, 185, 129, 0.4)'
            : '1px solid var(--border-color)',
        background: concept.flagged
          ? 'rgba(245, 158, 11, 0.04)'
          : 'rgba(255, 255, 255, 0.02)',
        transition: 'all 0.2s ease',
      }}
    >
      {/* ── Card Header ─────────────────────────────────────────────────── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: '12px',
          padding: '16px 18px',
        }}
      >
        {/* Status Icon */}
        <div style={{ flexShrink: 0, marginTop: '2px' }}>
          {concept.flagged ? (
            <AlertTriangle size={18} color="#f59e0b" />
          ) : refineSuccess ? (
            <Check size={18} color="#10b981" />
          ) : (
            <CheckCircle size={18} color="#10b981" />
          )}
        </div>

        {/* Title + meta */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              flexWrap: 'wrap',
              marginBottom: '4px',
            }}
          >
            <span
              style={{
                fontSize: '1rem',
                fontWeight: 600,
                color: 'var(--text-primary)',
              }}
            >
              {concept.title}
            </span>
            {/* Confidence badge */}
            <span
              style={{
                fontSize: '0.7rem',
                padding: '2px 8px',
                borderRadius: '20px',
                background: `${confidenceColor}22`,
                color: confidenceColor,
                border: `1px solid ${confidenceColor}44`,
                fontWeight: 600,
              }}
            >
              {Math.round(confidence * 100)}% confidence
            </span>
            {concept.flagged && concept.flagged_reason && (
              <span
                style={{
                  fontSize: '0.7rem',
                  padding: '2px 8px',
                  borderRadius: '20px',
                  background: 'rgba(245, 158, 11, 0.1)',
                  color: '#f59e0b',
                  border: '1px solid rgba(245, 158, 11, 0.3)',
                }}
              >
                ⚠ {concept.flagged_reason}
              </span>
            )}
          </div>
          <p
            style={{
              fontSize: '0.85rem',
              color: 'var(--text-secondary)',
              margin: 0,
              lineHeight: 1.5,
            }}
          >
            {concept.description}
          </p>

          {/* Tags row */}
          {concept.tags && concept.tags.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '10px' }}>
              {concept.tags.map((tag, i) => (
                <span
                  key={i}
                  style={{
                    fontSize: '0.7rem',
                    padding: '3px 9px',
                    borderRadius: '20px',
                    background: 'rgba(99, 102, 241, 0.1)',
                    color: 'var(--accent-primary)',
                    border: '1px solid rgba(99, 102, 241, 0.2)',
                  }}
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div style={{ display: 'flex', gap: '6px', flexShrink: 0 }}>
          {/* Expand/Collapse body */}
          <button
            onClick={() => setExpanded(e => !e)}
            title={expanded ? 'Collapse' : 'View full content'}
            style={{
              background: 'rgba(99, 102, 241, 0.1)',
              border: '1px solid rgba(99, 102, 241, 0.2)',
              borderRadius: '8px',
              padding: '6px 10px',
              cursor: 'pointer',
              color: 'var(--accent-primary)',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '0.78rem',
              fontWeight: 500,
            }}
          >
            <BookOpen size={13} />
            {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>

          {/* Refine toggle */}
          <button
            onClick={() => {
              setShowRefinePanel(r => !r);
              if (!expanded) setExpanded(true);
            }}
            title="Refine / Go deeper"
            style={{
              background: showRefinePanel
                ? 'rgba(139, 92, 246, 0.2)'
                : 'rgba(139, 92, 246, 0.08)',
              border: '1px solid rgba(139, 92, 246, 0.3)',
              borderRadius: '8px',
              padding: '6px 10px',
              cursor: 'pointer',
              color: '#8b5cf6',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '0.78rem',
              fontWeight: 500,
            }}
          >
            <WandSparkles size={13} />
            Refine
          </button>

          {/* Delete */}
          <button
            onClick={handleDelete}
            disabled={isDeleting}
            title="Remove this concept"
            style={{
              background: 'rgba(239, 68, 68, 0.07)',
              border: '1px solid rgba(239, 68, 68, 0.2)',
              borderRadius: '8px',
              padding: '6px 8px',
              cursor: 'pointer',
              color: '#ef4444',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            {isDeleting ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
          </button>
        </div>
      </div>

      {/* ── Expanded Body ───────────────────────────────────────────────── */}
      {expanded && (
        <div
          style={{
            padding: '0 18px 16px 18px',
            borderTop: '1px solid var(--border-color)',
            paddingTop: '16px',
          }}
        >
          {localBody ? (
            <MarkdownBody body={localBody} />
          ) : (
            <p style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '0.85rem' }}>
              No detailed body available for this concept.
            </p>
          )}
        </div>
      )}

      {/* ── Refine Panel ────────────────────────────────────────────────── */}
      {showRefinePanel && (
        <div
          style={{
            padding: '14px 18px',
            borderTop: '1px solid rgba(139, 92, 246, 0.2)',
            background: 'rgba(139, 92, 246, 0.04)',
          }}
        >
          <p
            style={{
              fontSize: '0.8rem',
              color: '#8b5cf6',
              marginBottom: '10px',
              fontWeight: 500,
            }}
          >
            ✦ Describe how to refine or deepen this concept (or leave blank for auto-expansion):
          </p>
          <textarea
            placeholder="e.g. 'Add more examples', 'Explain advanced use cases', 'Include historical context'…"
            value={refinePrompt}
            onChange={e => setRefinePrompt(e.target.value)}
            disabled={isRefining}
            style={{
              width: '100%',
              minHeight: '64px',
              padding: '10px 12px',
              borderRadius: '8px',
              background: 'rgba(0,0,0,0.2)',
              border: '1px solid rgba(139, 92, 246, 0.3)',
              color: 'var(--text-primary)',
              fontSize: '0.85rem',
              resize: 'vertical',
              boxSizing: 'border-box',
            }}
          />
          {refineError && (
            <p style={{ fontSize: '0.8rem', color: '#ef4444', marginTop: '6px' }}>{refineError}</p>
          )}
          <button
            onClick={handleRefine}
            disabled={isRefining}
            style={{
              marginTop: '10px',
              padding: '9px 18px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #8b5cf6, #6d28d9)',
              border: 'none',
              color: '#fff',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: isRefining ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              opacity: isRefining ? 0.7 : 1,
            }}
          >
            {isRefining ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                Refining with AI…
              </>
            ) : (
              <>
                <Sparkles size={14} />
                Go Deeper
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
};

// ──────────────────────────────────────────────────────────────────────────────
// Suggest New Concept Dialog
// ──────────────────────────────────────────────────────────────────────────────

interface SuggestPanelProps {
  apiUrl: string;
  token: string | null;
  jobId: string;
  onAdded: (concept: StagedConcept) => void;
  onClose: () => void;
}

const SuggestPanel: React.FC<SuggestPanelProps> = ({
  apiUrl,
  token,
  jobId,
  onAdded,
  onClose,
}) => {
  const [topicInput, setTopicInput] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSuggest = async () => {
    if (!topicInput.trim()) return;
    setIsGenerating(true);
    setError(null);
    try {
      const res = await fetch(`${apiUrl}/api/jobs/${jobId}/staged-concepts/suggest`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: topicInput.trim() }),
      });
      if (!res.ok) throw new Error('Failed to generate concept');
      const data = await res.json();
      onAdded(data.concept);
    } catch (err: any) {
      setError(err.message);
      setIsGenerating(false);
    }
  };

  return (
    <div
      style={{
        padding: '20px',
        borderRadius: '14px',
        border: '1px solid rgba(16, 185, 129, 0.3)',
        background: 'rgba(16, 185, 129, 0.04)',
        marginTop: '8px',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '12px',
        }}
      >
        <p style={{ fontSize: '0.9rem', color: '#10b981', fontWeight: 600, margin: 0 }}>
          ✦ Suggest a new concept to add
        </p>
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: 'var(--text-muted)',
          }}
        >
          <X size={16} />
        </button>
      </div>
      <textarea
        ref={inputRef}
        placeholder="Describe the topic you want to add, e.g. 'Explain Big-O complexity analysis'"
        value={topicInput}
        onChange={e => setTopicInput(e.target.value)}
        disabled={isGenerating}
        onKeyDown={e => {
          if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleSuggest();
        }}
        style={{
          width: '100%',
          minHeight: '72px',
          padding: '10px 12px',
          borderRadius: '8px',
          background: 'rgba(0,0,0,0.2)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          color: 'var(--text-primary)',
          fontSize: '0.85rem',
          resize: 'vertical',
          boxSizing: 'border-box',
        }}
      />
      {error && (
        <p style={{ fontSize: '0.8rem', color: '#ef4444', marginTop: '6px' }}>{error}</p>
      )}
      <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
        <button
          onClick={handleSuggest}
          disabled={isGenerating || !topicInput.trim()}
          style={{
            padding: '9px 18px',
            borderRadius: '8px',
            background: 'linear-gradient(135deg, #10b981, #059669)',
            border: 'none',
            color: '#fff',
            fontSize: '0.85rem',
            fontWeight: 600,
            cursor: isGenerating || !topicInput.trim() ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            opacity: isGenerating || !topicInput.trim() ? 0.6 : 1,
          }}
        >
          {isGenerating ? (
            <>
              <Loader2 size={14} className="animate-spin" />
              Generating…
            </>
          ) : (
            <>
              <Sparkles size={14} />
              Generate &amp; Add (Ctrl+Enter)
            </>
          )}
        </button>
        <button
          onClick={onClose}
          disabled={isGenerating}
          style={{
            padding: '9px 16px',
            borderRadius: '8px',
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid var(--border-color)',
            color: 'var(--text-secondary)',
            fontSize: '0.85rem',
            cursor: 'pointer',
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  );
};

// ──────────────────────────────────────────────────────────────────────────────
// Main ReviewPanel
// ──────────────────────────────────────────────────────────────────────────────

export const ReviewPanel: React.FC<ReviewPanelProps> = ({
  apiUrl,
  token,
  jobId,
  topicId,
  documentId,
  onComplete,
}) => {
  const [concepts, setConcepts] = useState<StagedConcept[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSuggestPanel, setShowSuggestPanel] = useState(false);

  // ── Fetch staged concepts ──────────────────────────────────────────────────
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

  // ── Handlers ───────────────────────────────────────────────────────────────
  const handleDelete = (slug: string) => {
    setConcepts(prev => prev.filter(c => c.slug !== slug));
  };

  const handleRefined = (slug: string, updatedBody: string) => {
    setConcepts(prev =>
      prev.map(c =>
        c.slug === slug ? { ...c, body: updatedBody, flagged: false, flagged_reason: '' } : c
      )
    );
  };

  const handleConceptAdded = (concept: StagedConcept) => {
    setConcepts(prev => [...prev, concept]);
    setShowSuggestPanel(false);
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      const res = await fetch(`${apiUrl}/api/knowledge/${topicId}/review`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
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

  // ── Summary counts ─────────────────────────────────────────────────────────
  const flaggedCount = concepts.filter(c => c.flagged).length;
  const okCount = concepts.length - flaggedCount;

  // ── Loading state ──────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div
        className="glass-card"
        style={{
          padding: '48px 32px',
          textAlign: 'center',
          borderRadius: '16px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Loader2 size={36} className="animate-spin" color="var(--accent-primary)" style={{ marginBottom: '16px' }} />
        <span style={{ color: 'var(--text-secondary)' }}>Loading extracted concepts…</span>
      </div>
    );
  }

  // ── Error state ────────────────────────────────────────────────────────────
  if (error) {
    return (
      <div
        className="glass-card"
        style={{
          padding: '24px',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          borderRadius: '12px',
          background: 'rgba(239, 68, 68, 0.05)',
        }}
      >
        <div style={{ color: '#ef4444', fontWeight: 600 }}>{error}</div>
      </div>
    );
  }

  // ── Main render ────────────────────────────────────────────────────────────
  return (
    <div
      className="glass-card"
      style={{
        borderRadius: '18px',
        border: '1px solid var(--border-color)',
        display: 'flex',
        flexDirection: 'column',
        maxHeight: '90vh',
        overflow: 'hidden',
      }}
    >
      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div
        style={{
          padding: '24px 28px 20px',
          borderBottom: '1px solid var(--border-color)',
          background: 'rgba(255,255,255,0.01)',
          flexShrink: 0,
        }}
      >
        <h2
          style={{
            fontSize: '1.4rem',
            fontWeight: 700,
            color: 'var(--text-primary)',
            margin: '0 0 4px',
          }}
        >
          Review Extracted Concepts
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: 0 }}>
          The AI extracted{' '}
          <strong style={{ color: 'var(--text-primary)' }}>{concepts.length}</strong> concept
          {concepts.length !== 1 ? 's' : ''}.{' '}
          <span style={{ color: '#10b981' }}>{okCount} ready</span>
          {flaggedCount > 0 && (
            <>
              {' · '}
              <span style={{ color: '#f59e0b' }}>{flaggedCount} flagged for review</span>
            </>
          )}
          . Expand any card to read it, refine with AI, or remove it before ingesting.
        </p>
      </div>

      {/* ── Scrollable concept list ───────────────────────────────────────── */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '20px 28px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
        }}
      >
        {concepts.length === 0 ? (
          <div
            style={{
              padding: '40px',
              textAlign: 'center',
              color: 'var(--text-muted)',
              fontSize: '0.9rem',
            }}
          >
            No concepts remain. Use the button below to suggest a new one.
          </div>
        ) : (
          concepts.map(concept => (
            <ConceptCard
              key={concept.slug}
              concept={concept}
              apiUrl={apiUrl}
              token={token}
              jobId={jobId}
              onDelete={handleDelete}
              onRefined={handleRefined}
            />
          ))
        )}

        {/* Suggest new concept panel / button */}
        {showSuggestPanel ? (
          <SuggestPanel
            apiUrl={apiUrl}
            token={token}
            jobId={jobId}
            onAdded={handleConceptAdded}
            onClose={() => setShowSuggestPanel(false)}
          />
        ) : (
          <button
            onClick={() => setShowSuggestPanel(true)}
            style={{
              padding: '12px',
              borderRadius: '12px',
              border: '1px dashed rgba(16, 185, 129, 0.35)',
              background: 'rgba(16, 185, 129, 0.04)',
              color: '#10b981',
              fontSize: '0.85rem',
              fontWeight: 500,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              transition: 'all 0.2s',
            }}
          >
            <PlusCircle size={15} />
            Suggest a new concept to add
          </button>
        )}
      </div>

      {/* ── Footer / Approve Button ───────────────────────────────────────── */}
      <div
        style={{
          padding: '16px 28px',
          borderTop: '1px solid var(--border-color)',
          flexShrink: 0,
          background: 'rgba(255,255,255,0.01)',
        }}
      >
        {error && (
          <p style={{ color: '#ef4444', fontSize: '0.85rem', marginBottom: '10px' }}>{error}</p>
        )}
        <button
          className="btn btn-primary"
          onClick={handleSubmit}
          disabled={isSubmitting || concepts.length === 0}
          style={{ width: '100%', padding: '14px', fontSize: '1rem' }}
        >
          {isSubmitting ? (
            <>
              <Loader2 size={18} className="animate-spin" />
              <span>Finalizing Knowledge Base…</span>
            </>
          ) : (
            <>
              <Save size={18} />
              <span>
                Approve &amp; Ingest {concepts.length} Concept{concepts.length !== 1 ? 's' : ''}
              </span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
