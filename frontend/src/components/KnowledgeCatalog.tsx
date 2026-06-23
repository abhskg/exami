import React, { useState, useEffect } from 'react';
import {
  FileText,
  Search,
  Edit3,
  Trash2,
  CheckCircle2,
  X,
  Loader2,
  Database,
  BookOpen,
  Tag as TagIcon,
  Filter,
  Save,
  Sparkles,
} from 'lucide-react';

interface Topic {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

interface Document {
  id: string;
  user_id: string;
  topic_id: string;
  source_type: string;
  storage_path?: string;
  original_filename: string;
  status: string;
  ingested_at: string;
}

interface ContentChunk {
  id: string;
  document_id: string;
  user_id: string;
  topic_id: string;
  chunk_text: string;
  chunk_index: number;
}

interface QuestionOption {
  id: string;
  option_text: string;
  is_correct: boolean;
  option_order: number;
}

interface Question {
  id: string;
  user_id: string;
  topic_id: string;
  question_text: string;
  explanation?: string;
  difficulty: string;
  generated_by: string;
  is_active: boolean;
  created_at: string;
  options: QuestionOption[];
  tags: string[];
}

interface Tag {
  id: string;
  name: string;
  topic_id: string;
}

interface TagAnalytics {
  tag_name: string;
  question_count: number;
}

interface TopicAnalytics {
  topic_name: string;
  question_count: number;
}

interface QuestionAnalytics {
  total_questions: number;
  difficulty_breakdown: { [key: string]: number };
  tag_breakdown: TagAnalytics[];
  topic_breakdown: TopicAnalytics[];
}

interface KnowledgeCatalogProps {
  apiUrl: string;
  token: string | null;
  selectedTopic: Topic | null;
  showToast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  onDocumentsChange: () => void;
}

export const KnowledgeCatalog: React.FC<KnowledgeCatalogProps> = ({
  apiUrl,
  token,
  selectedTopic,
  showToast,
  onDocumentsChange,
}) => {
  const [subTab, setSubTab] = useState<'documents' | 'questions' | 'tags'>('documents');

  // --- Documents state ---
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);
  const [editingDocId, setEditingDocId] = useState<string | null>(null);
  const [editingDocName, setEditingDocName] = useState('');
  const [isSavingDoc, setIsSavingDoc] = useState(false);

  // --- Chunks state ---
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [chunks, setChunks] = useState<ContentChunk[]>([]);
  const [isLoadingChunks, setIsLoadingChunks] = useState(false);
  const [chunkSearch, setChunkSearch] = useState('');
  const [editingChunkId, setEditingChunkId] = useState<string | null>(null);
  const [editingChunkText, setEditingChunkText] = useState('');
  const [isSavingChunk, setIsSavingChunk] = useState(false);

  // --- Questions state ---
  const [questions, setQuestions] = useState<Question[]>([]);
  const [isLoadingQuestions, setIsLoadingQuestions] = useState(false);
  const [questionSearch, setQuestionSearch] = useState('');
  const [difficultyFilter, setDifficultyFilter] = useState<string>('all');
  const [tagFilter, setTagFilter] = useState<string>('all');
  const [allTags, setAllTags] = useState<Tag[]>([]);
  const [analytics, setAnalytics] = useState<QuestionAnalytics | null>(null);
  const [isLoadingAnalytics, setIsLoadingAnalytics] = useState(false);

  // Edit Question Modal / Form State
  const [editingQuestion, setEditingQuestion] = useState<Question | null>(null);
  const [eqText, setEqText] = useState('');
  const [eqExplanation, setEqExplanation] = useState('');
  const [eqDifficulty, setEqDifficulty] = useState('medium');
  const [eqTagsInput, setEqTagsInput] = useState('');
  const [eqOptions, setEqOptions] = useState<{ id?: string; text: string; isCorrect: boolean }[]>([
    { text: '', isCorrect: true },
    { text: '', isCorrect: false },
    { text: '', isCorrect: false },
    { text: '', isCorrect: false },
  ]);
  const [isSavingQuestion, setIsSavingQuestion] = useState(false);

  // --- Tags state ---
  const [tags, setTags] = useState<Tag[]>([]);
  const [isLoadingTags, setIsLoadingTags] = useState(false);
  const [editingTagId, setEditingTagId] = useState<string | null>(null);
  const [editingTagName, setEditingTagName] = useState('');
  const [isSavingTag, setIsSavingTag] = useState(false);

  // Fetch Documents
  const fetchLocalDocuments = async () => {
    if (!token || !selectedTopic) return;
    setIsLoadingDocs(true);
    try {
      const res = await fetch(`${apiUrl}/api/documents/?topic_id=${selectedTopic.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      }
    } catch (err) {
      console.error('Error loading documents:', err);
    } finally {
      setIsLoadingDocs(false);
    }
  };

  // Fetch Chunks for selected document
  const fetchChunks = async (docId: string) => {
    if (!token) return;
    setIsLoadingChunks(true);
    try {
      const res = await fetch(`${apiUrl}/api/documents/${docId}/chunks`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setChunks(data);
      }
    } catch (err) {
      console.error('Error loading chunks:', err);
    } finally {
      setIsLoadingChunks(false);
    }
  };

  // Fetch Analytics
  const fetchAnalytics = async () => {
    if (!token || !selectedTopic) return;
    setIsLoadingAnalytics(true);
    try {
      const res = await fetch(`${apiUrl}/api/questions/analytics?topic_id=${selectedTopic.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setAnalytics(data);
      }
    } catch (err) {
      console.error('Error loading question analytics:', err);
    } finally {
      setIsLoadingAnalytics(false);
    }
  };

  // Fetch Questions
  const fetchQuestions = async () => {
    if (!token || !selectedTopic) return;
    setIsLoadingQuestions(true);
    try {
      const res = await fetch(`${apiUrl}/api/questions/?topic_id=${selectedTopic.id}&limit=100`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setQuestions(data);
      }
      // Also fetch analytics to keep dashboard in sync
      fetchAnalytics();
    } catch (err) {
      console.error('Error loading questions:', err);
    } finally {
      setIsLoadingQuestions(false);
    }
  };

  // Fetch Tags
  const fetchTags = async () => {
    if (!token || !selectedTopic) return;
    setIsLoadingTags(true);
    try {
      const res = await fetch(`${apiUrl}/api/questions/tags?topic_id=${selectedTopic.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setTags(data);
        setAllTags(data);
      }
    } catch (err) {
      console.error('Error loading tags:', err);
    } finally {
      setIsLoadingTags(false);
    }
  };

  // Trigger loads on topic/tab changes
  useEffect(() => {
    if (selectedTopic) {
      fetchLocalDocuments();
      fetchQuestions();
      fetchTags();
      setSelectedDocId(null);
      setChunks([]);
    }
  }, [selectedTopic, subTab]);

  // Rename document
  const handleRenameDoc = async (docId: string) => {
    if (!editingDocName.trim() || !token) return;
    setIsSavingDoc(true);
    try {
      const res = await fetch(`${apiUrl}/api/documents/${docId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ original_filename: editingDocName.trim() }),
      });
      if (res.ok) {
        showToast('Document renamed successfully', 'success');
        setEditingDocId(null);
        fetchLocalDocuments();
        onDocumentsChange();
      } else {
        const errData = await res.json();
        showToast(errData.detail || 'Failed to rename document', 'error');
      }
    } catch (err) {
      showToast('Network error renaming document', 'error');
    } finally {
      setIsSavingDoc(false);
    }
  };

  // Delete document
  const handleDeleteDoc = async (docId: string) => {
    if (
      !window.confirm(
        'Are you sure you want to delete this document? This will delete all its content chunks and embeddings!'
      )
    )
      return;
    try {
      const res = await fetch(`${apiUrl}/api/documents/${docId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        showToast('Document and embeddings deleted successfully', 'success');
        if (selectedDocId === docId) {
          setSelectedDocId(null);
          setChunks([]);
        }
        fetchLocalDocuments();
        onDocumentsChange();
      } else {
        showToast('Failed to delete document', 'error');
      }
    } catch (err) {
      showToast('Network error deleting document', 'error');
    }
  };

  // Edit chunk text (Re-generates pgvector embedding!)
  const handleUpdateChunk = async (chunkId: string) => {
    if (!editingChunkText.trim() || !token) return;
    setIsSavingChunk(true);
    try {
      const res = await fetch(`${apiUrl}/api/documents/chunks/${chunkId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ chunk_text: editingChunkText.trim() }),
      });
      if (res.ok) {
        showToast('Chunk text updated and embedding vector re-generated!', 'success');
        setEditingChunkId(null);
        if (selectedDocId) fetchChunks(selectedDocId);
      } else {
        const errData = await res.json();
        showToast(errData.detail || 'Failed to update chunk embedding', 'error');
      }
    } catch (err) {
      showToast('Network error updating chunk embedding', 'error');
    } finally {
      setIsSavingChunk(false);
    }
  };

  // Delete chunk
  const handleDeleteChunk = async (chunkId: string) => {
    if (
      !window.confirm(
        'Are you sure you want to delete this chunk? Any questions linked to this chunk will lose their chunk attribution.'
      )
    )
      return;
    try {
      const res = await fetch(`${apiUrl}/api/documents/chunks/${chunkId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        showToast('Chunk deleted successfully', 'success');
        if (selectedDocId) fetchChunks(selectedDocId);
      } else {
        showToast('Failed to delete chunk', 'error');
      }
    } catch (err) {
      showToast('Network error deleting chunk', 'error');
    }
  };

  // Edit question triggers
  const startEditQuestion = (q: Question) => {
    setEditingQuestion(q);
    setEqText(q.question_text);
    setEqExplanation(q.explanation || '');
    setEqDifficulty(q.difficulty);
    setEqTagsInput(q.tags.join(', '));
    setEqOptions(
      q.options.map(opt => ({
        id: opt.id,
        text: opt.option_text,
        isCorrect: opt.is_correct,
      }))
    );
  };

  // Save question updates
  const handleSaveQuestion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingQuestion || !token) return;

    // Validation
    if (!eqText.trim()) {
      showToast('Question text cannot be empty', 'error');
      return;
    }
    if (eqOptions.some(opt => !opt.text.trim())) {
      showToast('All 4 options must have text', 'error');
      return;
    }
    if (!eqOptions.some(opt => opt.isCorrect)) {
      showToast('At least one option must be marked as correct', 'error');
      return;
    }

    setIsSavingQuestion(true);
    const payload = {
      question_text: eqText.trim(),
      explanation: eqExplanation.trim() || null,
      difficulty: eqDifficulty,
      tags: eqTagsInput
        .split(',')
        .map(t => t.trim().toLowerCase())
        .filter(Boolean),
      options: eqOptions.map((opt, idx) => ({
        id: opt.id || null,
        option_text: opt.text.trim(),
        is_correct: opt.isCorrect,
        option_order: idx,
      })),
    };

    try {
      const res = await fetch(`${apiUrl}/api/questions/${editingQuestion.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        showToast('Question updated successfully!', 'success');
        setEditingQuestion(null);
        fetchQuestions();
        fetchTags(); // refresh chips
      } else {
        const errData = await res.json();
        showToast(errData.detail || 'Failed to update question', 'error');
      }
    } catch (err) {
      showToast('Network error saving question', 'error');
    } finally {
      setIsSavingQuestion(false);
    }
  };

  // Delete question
  const handleDeleteQuestion = async (qId: string) => {
    if (!window.confirm('Are you sure you want to delete this question?')) return;
    try {
      const res = await fetch(`${apiUrl}/api/questions/${qId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        showToast('Question deleted successfully', 'success');
        fetchQuestions();
      } else {
        showToast('Failed to delete question', 'error');
      }
    } catch (err) {
      showToast('Network error deleting question', 'error');
    }
  };

  // Rename tag (handles merge if target tag already exists!)
  const handleRenameTag = async (tagId: string) => {
    const targetName = editingTagName.trim().toLowerCase();
    if (!targetName || !token) return;
    setIsSavingTag(true);
    try {
      const res = await fetch(`${apiUrl}/api/questions/tags/${tagId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name: targetName }),
      });
      if (res.ok) {
        showToast('Tag renamed and updated successfully', 'success');
        setEditingTagId(null);
        fetchTags();
        fetchQuestions();
      } else {
        const errData = await res.json();
        showToast(errData.detail || 'Failed to update tag', 'error');
      }
    } catch (err) {
      showToast('Network error renaming tag', 'error');
    } finally {
      setIsSavingTag(false);
    }
  };

  // Delete tag
  const handleDeleteTag = async (tagId: string) => {
    if (
      !window.confirm(
        'Are you sure you want to delete this tag? It will be unlinked from all questions.'
      )
    )
      return;
    try {
      const res = await fetch(`${apiUrl}/api/questions/tags/${tagId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        showToast('Tag deleted successfully', 'success');
        fetchTags();
        fetchQuestions();
      } else {
        showToast('Failed to delete tag', 'error');
      }
    } catch (err) {
      showToast('Network error deleting tag', 'error');
    }
  };

  // Option Correctness toggler for Question form
  const toggleOptionCorrectness = (idx: number) => {
    setEqOptions(prev =>
      prev.map((opt, i) => ({
        ...opt,
        isCorrect: i === idx, // enforce single correct option for MCQs
      }))
    );
  };

  const handleOptionTextChange = (idx: number, text: string) => {
    setEqOptions(prev => prev.map((opt, i) => (i === idx ? { ...opt, text } : opt)));
  };

  // Filters for questions list
  const filteredQuestions = questions.filter(q => {
    const matchSearch = q.question_text.toLowerCase().includes(questionSearch.toLowerCase());
    const matchDifficulty = difficultyFilter === 'all' || q.difficulty === difficultyFilter;
    const matchTag = tagFilter === 'all' || q.tags.includes(tagFilter.toLowerCase());
    return matchSearch && matchDifficulty && matchTag;
  });

  const filteredChunks = chunks.filter(c =>
    c.chunk_text.toLowerCase().includes(chunkSearch.toLowerCase())
  );

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>
      {/* Sub-tabs header */}
      <div
        style={{
          display: 'flex',
          borderBottom: '1px solid var(--border-color)',
          gap: '16px',
          paddingBottom: '4px',
        }}
      >
        <button
          onClick={() => setSubTab('documents')}
          style={{
            padding: '12px 18px',
            background: 'none',
            border: 'none',
            color: subTab === 'documents' ? 'var(--accent-primary)' : 'var(--text-secondary)',
            fontWeight: subTab === 'documents' ? 700 : 400,
            cursor: 'pointer',
            borderBottom:
              subTab === 'documents' ? '2px solid var(--accent-primary)' : '2px solid transparent',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.15s ease',
          }}
        >
          <FileText size={18} />
          <span>Documents & Embeddings</span>
        </button>
        <button
          onClick={() => setSubTab('questions')}
          style={{
            padding: '12px 18px',
            background: 'none',
            border: 'none',
            color: subTab === 'questions' ? 'var(--accent-primary)' : 'var(--text-secondary)',
            fontWeight: subTab === 'questions' ? 700 : 400,
            cursor: 'pointer',
            borderBottom:
              subTab === 'questions' ? '2px solid var(--accent-primary)' : '2px solid transparent',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.15s ease',
          }}
        >
          <BookOpen size={18} />
          <span>Questions Bank</span>
        </button>
        <button
          onClick={() => setSubTab('tags')}
          style={{
            padding: '12px 18px',
            background: 'none',
            border: 'none',
            color: subTab === 'tags' ? 'var(--accent-primary)' : 'var(--text-secondary)',
            fontWeight: subTab === 'tags' ? 700 : 400,
            cursor: 'pointer',
            borderBottom:
              subTab === 'tags' ? '2px solid var(--accent-primary)' : '2px solid transparent',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.15s ease',
          }}
        >
          <TagIcon size={18} />
          <span>Topic Tags</span>
        </button>
      </div>

      {/* SUB-VIEW 1: Documents & Embeddings */}
      {subTab === 'documents' && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '2fr 3fr',
            gap: '30px',
            alignItems: 'start',
          }}
        >
          {/* Document list */}
          <div className="glass-card">
            <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Database size={18} color="var(--accent-primary)" />
              Knowledge Documents
            </h3>

            {isLoadingDocs ? (
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'center',
                  padding: '40px 0',
                  color: 'var(--text-secondary)',
                }}
              >
                <Loader2 size={24} className="animate-spin" />
              </div>
            ) : documents.length === 0 ? (
              <div
                style={{
                  padding: '30px',
                  textAlign: 'center',
                  border: '1px dashed var(--border-color)',
                  borderRadius: '8px',
                  color: 'var(--text-secondary)',
                }}
              >
                No documents found for this topic. Upload materials in the Setup tab first.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {documents.map(doc => {
                  const isSelected = selectedDocId === doc.id;
                  const isEditing = editingDocId === doc.id;

                  return (
                    <div
                      key={doc.id}
                      style={{
                        padding: '14px',
                        borderRadius: '10px',
                        background: isSelected ? 'rgba(99,102,241,0.06)' : 'rgba(255,255,255,0.01)',
                        border: isSelected
                          ? '1px solid var(--accent-primary)'
                          : '1px solid var(--border-color)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '10px',
                        transition: 'all 0.2s ease',
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          gap: '10px',
                        }}
                      >
                        <div
                          onClick={() => {
                            if (!isEditing) {
                              setSelectedDocId(doc.id);
                              fetchChunks(doc.id);
                            }
                          }}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '10px',
                            cursor: 'pointer',
                            flex: 1,
                            minWidth: 0,
                          }}
                        >
                          <FileText
                            size={18}
                            color="var(--accent-secondary)"
                            style={{ flexShrink: 0 }}
                          />
                          {isEditing ? (
                            <input
                              type="text"
                              value={editingDocName}
                              onChange={e => setEditingDocName(e.target.value)}
                              onClick={e => e.stopPropagation()}
                              onKeyDown={e => {
                                if (e.key === 'Enter') handleRenameDoc(doc.id);
                                if (e.key === 'Escape') setEditingDocId(null);
                              }}
                              autoFocus
                              style={{
                                flex: 1,
                                padding: '4px 8px',
                                fontSize: '0.85rem',
                                background: 'rgba(0,0,0,0.3)',
                                border: '1px solid var(--accent-primary)',
                                color: '#fff',
                                borderRadius: '4px',
                              }}
                            />
                          ) : (
                            <strong
                              style={{
                                fontSize: '0.9rem',
                                color: 'var(--text-primary)',
                                whiteSpace: 'nowrap',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                              }}
                            >
                              {doc.original_filename}
                            </strong>
                          )}
                        </div>

                        {/* Document Actions */}
                        <div
                          style={{
                            display: 'flex',
                            gap: '6px',
                            alignItems: 'center',
                            flexShrink: 0,
                          }}
                        >
                          {isEditing ? (
                            <>
                              <button
                                onClick={() => handleRenameDoc(doc.id)}
                                disabled={isSavingDoc}
                                style={{
                                  background: 'none',
                                  border: 'none',
                                  cursor: 'pointer',
                                  color: 'var(--accent-teal)',
                                }}
                              >
                                {isSavingDoc ? (
                                  <Loader2 size={16} className="animate-spin" />
                                ) : (
                                  <Save size={16} />
                                )}
                              </button>
                              <button
                                onClick={() => setEditingDocId(null)}
                                style={{
                                  background: 'none',
                                  border: 'none',
                                  cursor: 'pointer',
                                  color: 'var(--text-muted)',
                                }}
                              >
                                <X size={16} />
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                onClick={e => {
                                  e.stopPropagation();
                                  setEditingDocId(doc.id);
                                  setEditingDocName(doc.original_filename);
                                }}
                                style={{
                                  background: 'none',
                                  border: 'none',
                                  cursor: 'pointer',
                                  color: 'var(--text-secondary)',
                                }}
                                title="Rename"
                              >
                                <Edit3 size={15} />
                              </button>
                              <button
                                onClick={e => {
                                  e.stopPropagation();
                                  handleDeleteDoc(doc.id);
                                }}
                                style={{
                                  background: 'none',
                                  border: 'none',
                                  cursor: 'pointer',
                                  color: '#ef4444',
                                }}
                                title="Delete"
                              >
                                <Trash2 size={15} />
                              </button>
                            </>
                          )}
                        </div>
                      </div>

                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          fontSize: '0.72rem',
                          color: 'var(--text-muted)',
                        }}
                      >
                        <span style={{ textTransform: 'capitalize' }}>
                          Source: {doc.source_type.replace('upload_', '')}
                        </span>
                        <span>
                          Status:{' '}
                          <strong
                            style={{
                              color: doc.status === 'parsed' ? 'var(--accent-teal)' : '#f59e0b',
                            }}
                          >
                            {doc.status}
                          </strong>
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Chunks Explorer */}
          <div className="glass-card" style={{ minHeight: '380px' }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                gap: '16px',
                marginBottom: '20px',
                flexWrap: 'wrap',
              }}
            >
              <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sparkles size={18} color="var(--accent-teal)" />
                Vector Embeddings Explorer
              </h3>

              {selectedDocId && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    position: 'relative',
                    width: '220px',
                  }}
                >
                  <input
                    type="text"
                    placeholder="Search chunk text..."
                    value={chunkSearch}
                    onChange={e => setChunkSearch(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '6px 12px 6px 32px',
                      fontSize: '0.8rem',
                      background: 'rgba(0,0,0,0.2)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '6px',
                      color: '#fff',
                    }}
                  />
                  <Search
                    size={14}
                    color="var(--text-muted)"
                    style={{ position: 'absolute', left: '10px' }}
                  />
                </div>
              )}
            </div>

            {!selectedDocId ? (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '80px 20px',
                  color: 'var(--text-muted)',
                  textAlign: 'center',
                  gap: '12px',
                }}
              >
                <Database size={36} color="var(--text-muted)" style={{ opacity: 0.5 }} />
                <p style={{ fontSize: '0.9rem', margin: 0 }}>
                  Select a document on the left to browse, search, and edit its raw chunk vector
                  embeddings.
                </p>
              </div>
            ) : isLoadingChunks ? (
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'center',
                  padding: '60px 0',
                  color: 'var(--text-secondary)',
                }}
              >
                <Loader2 size={24} className="animate-spin" />
              </div>
            ) : filteredChunks.length === 0 ? (
              <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                No chunks found matching search query.
              </div>
            ) : (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '16px',
                  overflowY: 'auto',
                  maxHeight: '550px',
                  paddingRight: '4px',
                }}
              >
                {filteredChunks.map(chunk => {
                  const isEditing = editingChunkId === chunk.id;

                  return (
                    <div
                      key={chunk.id}
                      style={{
                        padding: '16px',
                        borderRadius: '10px',
                        background: 'rgba(255,255,255,0.02)',
                        border: '1px solid var(--border-color)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '12px',
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          borderBottom: '1px solid rgba(255,255,255,0.04)',
                          paddingBottom: '8px',
                        }}
                      >
                        <span
                          style={{
                            fontSize: '0.78rem',
                            color: 'var(--accent-teal)',
                            fontWeight: 600,
                          }}
                        >
                          Chunk #{chunk.chunk_index + 1}
                        </span>

                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          {isEditing ? (
                            <>
                              <button
                                onClick={() => handleUpdateChunk(chunk.id)}
                                disabled={isSavingChunk}
                                className="btn btn-secondary"
                                style={{
                                  padding: '4px 10px',
                                  borderRadius: '4px',
                                  fontSize: '0.75rem',
                                  background: 'var(--accent-primary-glow)',
                                  color: 'var(--accent-primary)',
                                  border: '1px solid var(--accent-primary)',
                                }}
                              >
                                {isSavingChunk ? (
                                  <Loader2 size={13} className="animate-spin" />
                                ) : (
                                  'Save & Embed'
                                )}
                              </button>
                              <button
                                onClick={() => setEditingChunkId(null)}
                                style={{
                                  background: 'none',
                                  border: 'none',
                                  cursor: 'pointer',
                                  color: 'var(--text-muted)',
                                }}
                              >
                                <X size={16} />
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                onClick={() => {
                                  setEditingChunkId(chunk.id);
                                  setEditingChunkText(chunk.chunk_text);
                                }}
                                style={{
                                  background: 'none',
                                  border: 'none',
                                  cursor: 'pointer',
                                  color: 'var(--text-secondary)',
                                }}
                                title="Edit chunk text & recalculate embedding"
                              >
                                <Edit3 size={14} />
                              </button>
                              <button
                                onClick={() => handleDeleteChunk(chunk.id)}
                                style={{
                                  background: 'none',
                                  border: 'none',
                                  cursor: 'pointer',
                                  color: '#ef4444',
                                }}
                                title="Delete chunk"
                              >
                                <Trash2 size={14} />
                              </button>
                            </>
                          )}
                        </div>
                      </div>

                      {isEditing ? (
                        <textarea
                          value={editingChunkText}
                          onChange={e => setEditingChunkText(e.target.value)}
                          rows={4}
                          style={{
                            width: '100%',
                            fontSize: '0.85rem',
                            background: 'rgba(0,0,0,0.3)',
                            border: '1px solid var(--border-focus)',
                            color: '#fff',
                            borderRadius: '6px',
                            resize: 'vertical',
                          }}
                        />
                      ) : (
                        <p
                          style={{
                            fontSize: '0.85rem',
                            color: 'var(--text-secondary)',
                            margin: 0,
                            lineHeight: 1.6,
                          }}
                        >
                          {chunk.chunk_text}
                        </p>
                      )}

                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          fontSize: '0.7rem',
                          color: 'var(--text-muted)',
                        }}
                      >
                        <span>ID: {chunk.id.substring(0, 8)}...</span>
                        <span>Vector Size: 768 float32s</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* SUB-VIEW 2: Questions Bank */}
      {subTab === 'questions' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Broad level analytics panel */}
          {analytics && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                gap: '20px',
                width: '100%',
              }}
              className="analytics-grid"
            >
              {/* Left Column: Topic Stats & Difficulty distribution */}
              <div
                className="glass-card"
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '20px',
                  padding: '24px',
                  background:
                    'linear-gradient(135deg, rgba(99,102,241,0.03) 0%, rgba(255,255,255,0.01) 100%)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '16px',
                }}
              >
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                >
                  <h4
                    style={{
                      margin: 0,
                      fontSize: '1.1rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      color: 'var(--text-primary)',
                    }}
                  >
                    <Sparkles size={16} color="var(--accent-primary)" />
                    Topic Analytics: {selectedTopic?.name}
                  </h4>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    Total Questions: <strong>{analytics.total_questions}</strong>
                  </span>
                </div>

                {/* Stat cards row */}
                <div
                  style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}
                >
                  <div
                    style={{
                      padding: '12px 16px',
                      background: 'rgba(20,184,166,0.03)',
                      border: '1px solid rgba(20,184,166,0.15)',
                      borderRadius: '10px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px',
                    }}
                  >
                    <span
                      style={{
                        fontSize: '0.72rem',
                        color: 'var(--accent-teal)',
                        fontWeight: 600,
                        textTransform: 'uppercase',
                      }}
                    >
                      Easy
                    </span>
                    <strong style={{ fontSize: '1.25rem', color: '#fff' }}>
                      {analytics.difficulty_breakdown.easy || 0}
                    </strong>
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                      {analytics.total_questions > 0
                        ? Math.round(
                            ((analytics.difficulty_breakdown.easy || 0) /
                              analytics.total_questions) *
                              100
                          )
                        : 0}
                      %
                    </span>
                  </div>

                  <div
                    style={{
                      padding: '12px 16px',
                      background: 'rgba(168,85,247,0.03)',
                      border: '1px solid rgba(168,85,247,0.15)',
                      borderRadius: '10px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px',
                    }}
                  >
                    <span
                      style={{
                        fontSize: '0.72rem',
                        color: 'var(--accent-secondary)',
                        fontWeight: 600,
                        textTransform: 'uppercase',
                      }}
                    >
                      Medium
                    </span>
                    <strong style={{ fontSize: '1.25rem', color: '#fff' }}>
                      {analytics.difficulty_breakdown.medium || 0}
                    </strong>
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                      {analytics.total_questions > 0
                        ? Math.round(
                            ((analytics.difficulty_breakdown.medium || 0) /
                              analytics.total_questions) *
                              100
                          )
                        : 0}
                      %
                    </span>
                  </div>

                  <div
                    style={{
                      padding: '12px 16px',
                      background: 'rgba(239,68,68,0.03)',
                      border: '1px solid rgba(239,68,68,0.15)',
                      borderRadius: '10px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px',
                    }}
                  >
                    <span
                      style={{
                        fontSize: '0.72rem',
                        color: '#ef4444',
                        fontWeight: 600,
                        textTransform: 'uppercase',
                      }}
                    >
                      Hard
                    </span>
                    <strong style={{ fontSize: '1.25rem', color: '#fff' }}>
                      {analytics.difficulty_breakdown.hard || 0}
                    </strong>
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                      {analytics.total_questions > 0
                        ? Math.round(
                            ((analytics.difficulty_breakdown.hard || 0) /
                              analytics.total_questions) *
                              100
                          )
                        : 0}
                      %
                    </span>
                  </div>
                </div>

                {/* Stacked distribution progress bar */}
                {analytics.total_questions > 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                      Difficulty Distribution Breakdown
                    </span>
                    <div
                      style={{
                        display: 'flex',
                        height: '8px',
                        borderRadius: '4px',
                        overflow: 'hidden',
                        background: 'rgba(255,255,255,0.05)',
                      }}
                    >
                      <div
                        style={{
                          width: `${((analytics.difficulty_breakdown.easy || 0) / analytics.total_questions) * 100}%`,
                          background: 'var(--accent-teal)',
                        }}
                        title={`Easy: ${analytics.difficulty_breakdown.easy}`}
                      />
                      <div
                        style={{
                          width: `${((analytics.difficulty_breakdown.medium || 0) / analytics.total_questions) * 100}%`,
                          background: 'var(--accent-secondary)',
                        }}
                        title={`Medium: ${analytics.difficulty_breakdown.medium}`}
                      />
                      <div
                        style={{
                          width: `${((analytics.difficulty_breakdown.hard || 0) / analytics.total_questions) * 100}%`,
                          background: '#ef4444',
                        }}
                        title={`Hard: ${analytics.difficulty_breakdown.hard}`}
                      />
                    </div>
                  </div>
                )}

                {/* Concept/Tag breakdown */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <span
                    style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}
                  >
                    Concept / Tag Breakdown:
                  </span>
                  {analytics.tag_breakdown.length === 0 ? (
                    <span
                      style={{
                        fontSize: '0.78rem',
                        color: 'var(--text-muted)',
                        fontStyle: 'italic',
                      }}
                    >
                      No concepts defined yet.
                    </span>
                  ) : (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                      {analytics.tag_breakdown.map(t => (
                        <div
                          key={t.tag_name}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '4px 10px',
                            background: 'rgba(99,102,241,0.06)',
                            border: '1px solid rgba(99,102,241,0.15)',
                            borderRadius: '20px',
                            fontSize: '0.75rem',
                          }}
                        >
                          <span style={{ color: 'var(--accent-primary)', fontFamily: 'monospace' }}>
                            {t.tag_name}
                          </span>
                          <span
                            style={{
                              background: 'rgba(99,102,241,0.2)',
                              color: '#fff',
                              borderRadius: '10px',
                              padding: '1px 6px',
                              fontSize: '0.65rem',
                              fontWeight: 700,
                            }}
                          >
                            {t.question_count}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column: Global Topic Distribution */}
              <div
                className="glass-card"
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '16px',
                  padding: '24px',
                  background: 'rgba(255,255,255,0.01)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '16px',
                }}
              >
                <h4
                  style={{
                    margin: 0,
                    fontSize: '1rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    color: 'var(--text-primary)',
                  }}
                >
                  <BookOpen size={16} color="var(--accent-teal)" />
                  Questions Across Subjects
                </h4>

                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '10px',
                    overflowY: 'auto',
                    maxHeight: '180px',
                    paddingRight: '4px',
                  }}
                >
                  {analytics.topic_breakdown.map(tb => {
                    const isCurrent = tb.topic_name === selectedTopic?.name;
                    return (
                      <div
                        key={tb.topic_name}
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '4px',
                          padding: '8px 12px',
                          borderRadius: '8px',
                          background: isCurrent
                            ? 'rgba(20,184,166,0.06)'
                            : 'rgba(255,255,255,0.01)',
                          border: isCurrent
                            ? '1px solid rgba(20,184,166,0.2)'
                            : '1px solid rgba(255,255,255,0.03)',
                        }}
                      >
                        <div
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            fontSize: '0.82rem',
                          }}
                        >
                          <span
                            style={{
                              fontWeight: isCurrent ? 700 : 400,
                              color: isCurrent ? 'var(--accent-teal)' : 'var(--text-secondary)',
                            }}
                          >
                            {tb.topic_name} {isCurrent && ' (Active)'}
                          </span>
                          <span style={{ fontWeight: 600, color: '#fff' }}>
                            {tb.question_count} Qs
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Question search and filter panel */}
          <div
            className="glass-card"
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '16px',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '16px 24px',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '16px',
                flex: 1,
                minWidth: '280px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', position: 'relative', flex: 1 }}>
                <input
                  type="text"
                  placeholder="Search questions by keyword..."
                  value={questionSearch}
                  onChange={e => setQuestionSearch(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px 8px 36px',
                    fontSize: '0.9rem',
                    background: 'rgba(255, 255, 255, 0.02)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    color: '#fff',
                  }}
                />
                <Search
                  size={16}
                  color="var(--text-muted)"
                  style={{ position: 'absolute', left: '12px' }}
                />
              </div>
            </div>

            {/* Filter controls */}
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Filter size={14} color="var(--text-secondary)" />
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Difficulty:
                </span>
                <select
                  value={difficultyFilter}
                  onChange={e => setDifficultyFilter(e.target.value)}
                  style={{ padding: '6px 12px', fontSize: '0.82rem', borderRadius: '6px' }}
                >
                  <option value="all">All Difficulties</option>
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <TagIcon size={14} color="var(--text-secondary)" />
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Tag:</span>
                <select
                  value={tagFilter}
                  onChange={e => setTagFilter(e.target.value)}
                  style={{ padding: '6px 12px', fontSize: '0.82rem', borderRadius: '6px' }}
                >
                  <option value="all">All Tags</option>
                  {allTags.map(t => (
                    <option key={t.id} value={t.name}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Question List */}
          {isLoadingQuestions ? (
            <div
              style={{
                display: 'flex',
                justifyContent: 'center',
                padding: '60px 0',
                color: 'var(--text-secondary)',
              }}
            >
              <Loader2 size={24} className="animate-spin" />
            </div>
          ) : filteredQuestions.length === 0 ? (
            <div
              className="glass-card"
              style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}
            >
              No questions found for this topic with active filters. Generate some MCQs or check
              details.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {filteredQuestions.map((q, qi) => (
                <div
                  key={q.id}
                  className="glass-card"
                  style={{
                    padding: '24px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '16px',
                    borderLeft: '4px solid var(--accent-primary)',
                  }}
                >
                  {/* Item Header */}
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      gap: '10px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span
                        style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 600 }}
                      >
                        Question {qi + 1}
                      </span>
                      <span
                        style={{
                          padding: '2px 8px',
                          borderRadius: '10px',
                          fontSize: '0.7rem',
                          fontWeight: 600,
                          textTransform: 'capitalize',
                          background:
                            q.difficulty === 'easy'
                              ? 'rgba(20,184,166,0.1)'
                              : q.difficulty === 'hard'
                                ? 'rgba(239,68,68,0.1)'
                                : 'rgba(168,85,247,0.1)',
                          color:
                            q.difficulty === 'easy'
                              ? 'var(--accent-teal)'
                              : q.difficulty === 'hard'
                                ? '#ef4444'
                                : 'var(--accent-secondary)',
                        }}
                      >
                        {q.difficulty}
                      </span>
                    </div>

                    <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                      <button
                        onClick={() => startEditQuestion(q)}
                        className="btn btn-secondary"
                        style={{
                          padding: '6px 12px',
                          borderRadius: '6px',
                          fontSize: '0.8rem',
                          gap: '4px',
                        }}
                      >
                        <Edit3 size={13} />
                        <span>Edit</span>
                      </button>
                      <button
                        onClick={() => handleDeleteQuestion(q.id)}
                        className="btn btn-secondary"
                        style={{
                          padding: '6px 12px',
                          borderRadius: '6px',
                          fontSize: '0.8rem',
                          gap: '4px',
                          color: '#ef4444',
                          borderColor: 'rgba(239,68,68,0.2)',
                          background: 'rgba(239,68,68,0.02)',
                        }}
                      >
                        <Trash2 size={13} />
                        <span>Delete</span>
                      </button>
                    </div>
                  </div>

                  {/* Question body text */}
                  <p
                    style={{
                      margin: 0,
                      fontSize: '1rem',
                      fontWeight: 600,
                      color: 'var(--text-primary)',
                      lineHeight: 1.5,
                    }}
                  >
                    {q.question_text}
                  </p>

                  {/* Options */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                    {q.options.map(opt => (
                      <div
                        key={opt.id}
                        style={{
                          padding: '10px 14px',
                          borderRadius: '8px',
                          background: opt.is_correct
                            ? 'rgba(20,184,166,0.06)'
                            : 'rgba(255,255,255,0.01)',
                          border: opt.is_correct
                            ? '1px solid rgba(20,184,166,0.3)'
                            : '1px solid var(--border-color)',
                          color: opt.is_correct ? 'var(--accent-teal)' : 'var(--text-secondary)',
                          fontSize: '0.88rem',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                        }}
                      >
                        <span
                          style={{
                            width: '20px',
                            height: '20px',
                            borderRadius: '50%',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '0.72rem',
                            fontWeight: 700,
                            background: opt.is_correct
                              ? 'var(--accent-teal)'
                              : 'rgba(255,255,255,0.05)',
                            color: opt.is_correct ? '#fff' : 'var(--text-muted)',
                          }}
                        >
                          {String.fromCharCode(65 + opt.option_order)}
                        </span>
                        <span>{opt.option_text}</span>
                        {opt.is_correct && (
                          <CheckCircle2 size={14} style={{ marginLeft: 'auto' }} />
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Explanation and Tags */}
                  <div
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '10px',
                      paddingTop: '10px',
                      borderTop: '1px solid rgba(255,255,255,0.03)',
                    }}
                  >
                    {q.explanation && (
                      <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: 0 }}>
                        <strong style={{ color: 'var(--accent-primary)' }}>Explanation:</strong>{' '}
                        {q.explanation}
                      </p>
                    )}

                    {q.tags.length > 0 && (
                      <div
                        style={{
                          display: 'flex',
                          flexWrap: 'wrap',
                          gap: '6px',
                          alignItems: 'center',
                        }}
                      >
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          Tags:
                        </span>
                        {q.tags.map(t => (
                          <span
                            key={t}
                            style={{
                              padding: '2px 8px',
                              borderRadius: '12px',
                              background: 'rgba(99,102,241,0.08)',
                              border: '1px solid rgba(99,102,241,0.2)',
                              color: 'var(--accent-primary)',
                              fontSize: '0.7rem',
                            }}
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Edit Question Modal */}
          {editingQuestion && (
            <div
              style={{
                position: 'fixed',
                top: 0,
                left: 0,
                width: '100vw',
                height: '100vh',
                background: 'rgba(0,0,0,0.6)',
                backdropFilter: 'blur(4px)',
                zIndex: 2000,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '20px',
              }}
            >
              <div
                className="glass-card fade-in"
                style={{
                  width: '100%',
                  maxWidth: '700px',
                  maxHeight: '90vh',
                  overflowY: 'auto',
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
                  padding: '30px',
                  borderRadius: '16px',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '24px',
                  }}
                >
                  <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Sparkles size={18} color="var(--accent-primary)" />
                    Edit Question Details
                  </h3>
                  <button
                    onClick={() => setEditingQuestion(null)}
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      color: 'var(--text-secondary)',
                    }}
                  >
                    <X size={20} />
                  </button>
                </div>

                <form
                  onSubmit={handleSaveQuestion}
                  style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}
                >
                  <div className="form-group">
                    <label>Question Text</label>
                    <textarea
                      value={eqText}
                      onChange={e => setEqText(e.target.value)}
                      rows={3}
                      required
                      style={{ width: '100%', resize: 'vertical' }}
                    />
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                    <div className="form-group">
                      <label>Difficulty</label>
                      <select
                        value={eqDifficulty}
                        onChange={e => setEqDifficulty(e.target.value)}
                        style={{ width: '100%' }}
                      >
                        <option value="easy">Easy</option>
                        <option value="medium">Medium</option>
                        <option value="hard">Hard</option>
                      </select>
                    </div>

                    <div className="form-group">
                      <label>Concept Tags (comma separated)</label>
                      <input
                        type="text"
                        value={eqTagsInput}
                        onChange={e => setEqTagsInput(e.target.value)}
                        placeholder="e.g. recursion, sorting, arrays"
                        style={{ width: '100%' }}
                      />
                    </div>
                  </div>

                  {/* Options management */}
                  <div>
                    <label style={{ display: 'block', marginBottom: '10px' }}>
                      Answer Options (Exactly one correct)
                    </label>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {eqOptions.map((opt, idx) => (
                        <div
                          key={idx}
                          style={{ display: 'flex', alignItems: 'center', gap: '10px' }}
                        >
                          <button
                            type="button"
                            onClick={() => toggleOptionCorrectness(idx)}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              width: '32px',
                              height: '32px',
                              borderRadius: '50%',
                              border: opt.isCorrect
                                ? '1px solid var(--accent-teal)'
                                : '1px solid var(--border-color)',
                              background: opt.isCorrect ? 'var(--accent-teal-glow)' : 'transparent',
                              color: opt.isCorrect ? 'var(--accent-teal)' : 'var(--text-muted)',
                              cursor: 'pointer',
                              flexShrink: 0,
                            }}
                            title={opt.isCorrect ? 'Correct Option' : 'Set as Correct Option'}
                          >
                            {opt.isCorrect ? (
                              <CheckCircle2 size={16} />
                            ) : (
                              <span>{String.fromCharCode(65 + idx)}</span>
                            )}
                          </button>

                          <input
                            type="text"
                            value={opt.text}
                            onChange={e => handleOptionTextChange(idx, e.target.value)}
                            placeholder={`Option ${String.fromCharCode(65 + idx)} text`}
                            required
                            style={{ flex: 1, padding: '8px 12px' }}
                          />
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="form-group">
                    <label>Explanation</label>
                    <textarea
                      value={eqExplanation}
                      onChange={e => setEqExplanation(e.target.value)}
                      rows={2}
                      placeholder="Explain why the correct answer is right..."
                      style={{ width: '100%', resize: 'vertical' }}
                    />
                  </div>

                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'flex-end',
                      gap: '12px',
                      marginTop: '10px',
                    }}
                  >
                    <button
                      type="button"
                      onClick={() => setEditingQuestion(null)}
                      className="btn btn-secondary"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSavingQuestion}
                      className="btn btn-primary"
                      style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                    >
                      {isSavingQuestion ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : (
                        <Save size={16} />
                      )}
                      <span>Save Question Changes</span>
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}

      {/* SUB-VIEW 3: Topic Tags */}
      {subTab === 'tags' && (
        <div className="glass-card" style={{ maxWidth: '600px', margin: '0 auto', width: '100%' }}>
          <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <TagIcon size={18} color="var(--accent-primary)" />
            Concept Taxonomy Tags
          </h3>
          <p
            style={{
              fontSize: '0.85rem',
              color: 'var(--text-secondary)',
              marginBottom: '24px',
              lineHeight: 1.5,
            }}
          >
            Manage the conceptual tags registered for this topic. Renaming a tag to match an
            existing tag will automatically **merge** their question associations!
          </p>

          {isLoadingTags ? (
            <div
              style={{
                display: 'flex',
                justifyContent: 'center',
                padding: '40px 0',
                color: 'var(--text-secondary)',
              }}
            >
              <Loader2 size={24} className="animate-spin" />
            </div>
          ) : tags.length === 0 ? (
            <div
              style={{
                padding: '30px',
                textAlign: 'center',
                border: '1px dashed var(--border-color)',
                borderRadius: '8px',
                color: 'var(--text-secondary)',
              }}
            >
              No concept tags defined yet. Ingest documents or generate questions to initialize the
              taxonomy.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {tags.map(tag => {
                const isEditing = editingTagId === tag.id;

                return (
                  <div
                    key={tag.id}
                    style={{
                      padding: '12px 16px',
                      borderRadius: '8px',
                      background: 'rgba(255,255,255,0.01)',
                      border: '1px solid var(--border-color)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      gap: '12px',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        flex: 1,
                        minWidth: 0,
                      }}
                    >
                      <TagIcon size={14} color="var(--accent-primary)" style={{ flexShrink: 0 }} />
                      {isEditing ? (
                        <input
                          type="text"
                          value={editingTagName}
                          onChange={e => setEditingTagName(e.target.value)}
                          onKeyDown={e => {
                            if (e.key === 'Enter') handleRenameTag(tag.id);
                            if (e.key === 'Escape') setEditingTagId(null);
                          }}
                          autoFocus
                          style={{
                            flex: 1,
                            padding: '4px 8px',
                            fontSize: '0.85rem',
                            background: 'rgba(0,0,0,0.3)',
                            border: '1px solid var(--accent-primary)',
                            color: '#fff',
                            borderRadius: '4px',
                          }}
                        />
                      ) : (
                        <span
                          style={{
                            fontSize: '0.9rem',
                            color: 'var(--text-primary)',
                            fontFamily: 'monospace',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                        >
                          {tag.name}
                        </span>
                      )}
                    </div>

                    <div
                      style={{ display: 'flex', gap: '8px', alignItems: 'center', flexShrink: 0 }}
                    >
                      {isEditing ? (
                        <>
                          <button
                            onClick={() => handleRenameTag(tag.id)}
                            disabled={isSavingTag}
                            style={{
                              background: 'none',
                              border: 'none',
                              cursor: 'pointer',
                              color: 'var(--accent-teal)',
                            }}
                          >
                            {isSavingTag ? (
                              <Loader2 size={14} className="animate-spin" />
                            ) : (
                              <Save size={14} />
                            )}
                          </button>
                          <button
                            onClick={() => setEditingTagId(null)}
                            style={{
                              background: 'none',
                              border: 'none',
                              cursor: 'pointer',
                              color: 'var(--text-muted)',
                            }}
                          >
                            <X size={14} />
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            onClick={() => {
                              setEditingTagId(tag.id);
                              setEditingTagName(tag.name);
                            }}
                            style={{
                              background: 'none',
                              border: 'none',
                              cursor: 'pointer',
                              color: 'var(--text-secondary)',
                            }}
                            title="Rename tag"
                          >
                            <Edit3 size={14} />
                          </button>
                          <button
                            onClick={() => handleDeleteTag(tag.id)}
                            style={{
                              background: 'none',
                              border: 'none',
                              cursor: 'pointer',
                              color: '#ef4444',
                            }}
                            title="Delete tag"
                          >
                            <Trash2 size={14} />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
