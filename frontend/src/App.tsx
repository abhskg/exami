import { useState, useEffect, useRef } from 'react';
import { 
  Settings, 
  ChevronRight, 
  Layers, 
  CheckCircle2, 
  Clock, 
  TrendingUp, 
  Database,
  Upload,
  FolderOpen,
  FileText,
  LogOut,
  Plus,
  Loader2,
  AlertCircle
} from 'lucide-react';
import { AuthPage } from './pages/AuthPage';

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

function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'));
  const [user, setUser] = useState<any | null>(() => {
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });
  
  const [activeTab, setActiveTab] = useState<'dashboard' | 'setup' | 'exam' | 'results'>('dashboard');
  const [dbConnected, setDbConnected] = useState<boolean>(false);
  
  // Topics & Documents state
  const [topics, setTopics] = useState<Topic[]>([]);
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoadingTopics, setIsLoadingTopics] = useState<boolean>(false);
  const [isLoadingDocs, setIsLoadingDocs] = useState<boolean>(false);
  
  // Create Topic Form state
  const [newTopicName, setNewTopicName] = useState<string>('');
  const [isCreatingTopic, setIsCreatingTopic] = useState<boolean>(false);
  
  // Upload & Jobs state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [jobProgress, setJobProgress] = useState<number>(0);
  const [jobStatus, setJobStatus] = useState<string>('');
  const [jobMessage, setJobMessage] = useState<string>('');
  
  // Toast Alert state
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollIntervalRef = useRef<any>(null);
  
  const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

  // Show toast notification helper
  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  };

  // 1. Health check: check if database backend is online
  const checkHealth = async () => {
    try {
      const res = await fetch(`${apiUrl}/health`);
      if (res.ok) {
        setDbConnected(true);
      } else {
        setDbConnected(false);
      }
    } catch {
      setDbConnected(false);
    }
  };

  // 2. Fetch Topics from Backend
  const fetchTopics = async (selectFirst: boolean = false) => {
    if (!token) return;
    setIsLoadingTopics(true);
    try {
      const res = await fetch(`${apiUrl}/api/topics/`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setTopics(data);
        
        // Auto-provision default topic if list is empty
        if (data.length === 0) {
          await createDefaultTopic();
        } else if (selectFirst && data.length > 0) {
          setSelectedTopic(data[0]);
        } else if (selectedTopic) {
          // Keep current selection synced
          const updated = data.find((t: Topic) => t.id === selectedTopic.id);
          if (updated) setSelectedTopic(updated);
        } else {
          setSelectedTopic(data[0]);
        }
      } else if (res.status === 401) {
        handleLogout();
      }
    } catch (err) {
      console.error("Error fetching topics:", err);
      showToast("Failed to load topics from database.", "error");
    } finally {
      setIsLoadingTopics(false);
    }
  };

  // 3. Create Default Topic if none exist
  const createDefaultTopic = async () => {
    try {
      const res = await fetch(`${apiUrl}/api/topics/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          name: "DSA & System Design",
          description: "Default topic domain for algorithms, data structures, and architecture."
        })
      });
      if (res.ok) {
        const defaultTopic = await res.json();
        setTopics([defaultTopic]);
        setSelectedTopic(defaultTopic);
        showToast("Auto-provisioned default Topic.", "success");
      }
    } catch (err) {
      console.error("Error creating default topic:", err);
    }
  };

  // 4. Create Custom Topic Form submission
  const handleCreateTopic = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTopicName.trim() || !token) return;
    
    setIsCreatingTopic(true);
    try {
      const res = await fetch(`${apiUrl}/api/topics/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          name: newTopicName.trim(),
          description: "Custom study topic domain."
        })
      });
      
      const data = await res.json();
      if (res.ok) {
        showToast(`Topic "${newTopicName}" created successfully!`, "success");
        setNewTopicName('');
        // Refresh topics list and select the new one
        await fetchTopics();
        setSelectedTopic(data);
      } else {
        showToast(data.detail || "Failed to create topic.", "error");
      }
    } catch (err) {
      console.error("Error creating topic:", err);
      showToast("Network error creating topic.", "error");
    } finally {
      setIsCreatingTopic(false);
    }
  };

  // 5. Fetch Documents for Selected Topic
  const fetchDocuments = async (topicId: string) => {
    if (!token) return;
    setIsLoadingDocs(true);
    try {
      const res = await fetch(`${apiUrl}/api/documents/?topic_id=${topicId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      }
    } catch (err) {
      console.error("Error fetching documents:", err);
    } finally {
      setIsLoadingDocs(false);
    }
  };

  // 6. Handle File Drag & Drop
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (uploading) return;
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      validateAndSetFile(file);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (file: File) => {
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!['.pdf', '.txt', '.md'].includes(ext)) {
      showToast("Unsupported file type. Please upload a PDF, TXT or MD document.", "error");
      return;
    }
    if (file.size > 15 * 1024 * 1024) {
      showToast("File size exceeds 15MB limit.", "error");
      return;
    }
    setSelectedFile(file);
  };

  // 7. Trigger Upload & Ingestion Job
  const handleIngestFile = async () => {
    if (!selectedFile || !selectedTopic || !token) return;
    
    setUploading(true);
    setJobProgress(0);
    setJobStatus('uploading');
    setJobMessage('Uploading file to server...');
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('topic_id', selectedTopic.id);
    
    try {
      const res = await fetch(`${apiUrl}/api/documents/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });
      
      const data = await res.json();
      if (res.status === 202) {
        // Ingestion started successfully, start polling job
        const jobId = data.job_id;
        showToast("Ingestion job started. Processing in background...", "info");
        pollJobStatus(jobId);
      } else {
        showToast(data.detail || "Failed to upload document.", "error");
        setUploading(false);
      }
    } catch (err) {
      console.error("Upload error:", err);
      showToast("Network error uploading document.", "error");
      setUploading(false);
    }
  };

  // 8. Poll Background Job Progress
  const pollJobStatus = (jobId: string) => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    
    pollIntervalRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${apiUrl}/api/jobs/${jobId}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        if (res.ok) {
          const job = await res.json();
          setJobProgress(job.progress);
          setJobStatus(job.status);
          
          if (job.status === 'completed') {
            clearInterval(pollIntervalRef.current);
            setUploading(false);
            setSelectedFile(null);
            showToast("Document ingested, chunked, and vectorized successfully!", "success");
            fetchDocuments(selectedTopic!.id);
          } else if (job.status === 'failed') {
            clearInterval(pollIntervalRef.current);
            setUploading(false);
            setJobMessage(job.message || 'Processing failed.');
            showToast(job.message || "Document processing failed.", "error");
            fetchDocuments(selectedTopic!.id);
          } else {
            // Update message based on progress
            if (job.progress < 30) setJobMessage("Parsing document structures...");
            else if (job.progress < 50) setJobMessage("Extracting text contents...");
            else if (job.progress < 70) setJobMessage("Partitioning semantic chunks...");
            else if (job.progress < 90) setJobMessage("Generating vector embeddings (Gemini API)...");
            else setJobMessage("Writing segments to pgvector database...");
          }
        }
      } catch (err) {
        console.error("Job polling error:", err);
      }
    }, 2000);
  };

  // 9. Initial effects and auth triggers
  useEffect(() => {
    checkHealth();
    if (token) {
      fetchTopics(true);
    }
    
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [token]);

  // Refetch docs when selected topic changes
  useEffect(() => {
    if (selectedTopic) {
      fetchDocuments(selectedTopic.id);
    } else {
      setDocuments([]);
    }
  }, [selectedTopic]);

  const handleAuthSuccess = (newToken: string, newUser: any) => {
    setToken(newToken);
    setUser(newUser);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
    setTopics([]);
    setSelectedTopic(null);
    setDocuments([]);
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
  };

  if (!token) {
    return <AuthPage onAuthSuccess={handleAuthSuccess} />;
  }

  // Format bytes helper
  const formatBytes = (bytes: number = 0) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = 2;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-primary)' }}>
      {/* Toast Notification Banner */}
      {toast && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '20px',
          zIndex: 1000,
          padding: '12px 24px',
          borderRadius: '10px',
          background: toast.type === 'success' ? 'rgba(20, 184, 166, 0.95)' : toast.type === 'error' ? 'rgba(239, 68, 68, 0.95)' : 'rgba(99, 102, 241, 0.95)',
          color: '#ffffff',
          boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.3)',
          backdropFilter: 'blur(8px)',
          fontSize: '0.9rem',
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          animation: 'fadeIn var(--transition-fast) forwards'
        }}>
          {toast.type === 'error' && <AlertCircle size={18} />}
          <span>{toast.message}</span>
        </div>
      )}

      {/* Sidebar Navigation */}
      <aside style={{ 
        width: '280px', 
        borderRight: '1px solid var(--border-color)', 
        background: 'var(--bg-secondary)', 
        display: 'flex', 
        flexDirection: 'column', 
        justifyContent: 'space-between',
        padding: '24px',
        position: 'sticky',
        top: 0,
        height: '100vh'
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', overflowY: 'auto', flex: 1, paddingBottom: '16px' }}>
          {/* Logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '40px' }}>
            <div style={{ 
              background: 'linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%)',
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 800,
              fontSize: '1.25rem',
              color: '#fff',
              fontFamily: 'var(--font-display)'
            }}>
              EP
            </div>
            <div>
              <h1 style={{ fontSize: '1.15rem', margin: 0, padding: 0, background: 'none', WebkitTextFillColor: 'initial', color: 'var(--text-primary)' }}>ExamPrep AI</h1>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Local-First MVP</span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '32px' }}>
            <button 
              onClick={() => setActiveTab('dashboard')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                width: '100%',
                padding: '12px 16px',
                border: 'none',
                background: activeTab === 'dashboard' ? 'rgba(99, 102, 241, 0.1)' : 'transparent',
                color: activeTab === 'dashboard' ? 'var(--accent-primary)' : 'var(--text-secondary)',
                borderRadius: '8px',
                cursor: 'pointer',
                textAlign: 'left',
                fontWeight: activeTab === 'dashboard' ? 600 : 400,
                transition: 'var(--transition-fast)'
              }}
            >
              <Layers size={18} />
              <span>Dashboard</span>
            </button>
            <button 
              onClick={() => setActiveTab('setup')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                width: '100%',
                padding: '12px 16px',
                border: 'none',
                background: activeTab === 'setup' ? 'rgba(99, 102, 241, 0.1)' : 'transparent',
                color: activeTab === 'setup' ? 'var(--accent-primary)' : 'var(--text-secondary)',
                borderRadius: '8px',
                cursor: 'pointer',
                textAlign: 'left',
                fontWeight: activeTab === 'setup' ? 600 : 400,
                transition: 'var(--transition-fast)'
              }}
            >
              <Settings size={18} />
              <span>Setup & Ingestion</span>
            </button>
            <button 
              onClick={() => setActiveTab('exam')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                width: '100%',
                padding: '12px 16px',
                border: 'none',
                background: activeTab === 'exam' ? 'rgba(99, 102, 241, 0.1)' : 'transparent',
                color: activeTab === 'exam' ? 'var(--accent-primary)' : 'var(--text-secondary)',
                borderRadius: '8px',
                cursor: 'pointer',
                textAlign: 'left',
                fontWeight: activeTab === 'exam' ? 600 : 400,
                transition: 'var(--transition-fast)'
              }}
            >
              <Clock size={18} />
              <span>Exam Simulator</span>
            </button>
            <button 
              onClick={() => setActiveTab('results')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                width: '100%',
                padding: '12px 16px',
                border: 'none',
                background: activeTab === 'results' ? 'rgba(99, 102, 241, 0.1)' : 'transparent',
                color: activeTab === 'results' ? 'var(--accent-primary)' : 'var(--text-secondary)',
                borderRadius: '8px',
                cursor: 'pointer',
                textAlign: 'left',
                fontWeight: activeTab === 'results' ? 600 : 400,
                transition: 'var(--transition-fast)'
              }}
            >
              <TrendingUp size={18} />
              <span>Results & Review</span>
            </button>
          </nav>

          {/* Topics Area */}
          <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: '180px' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Your Topics</span>
            
            {/* Scrollable list of topics */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '8px', overflowY: 'auto', maxHeight: '200px' }}>
              {isLoadingTopics ? (
                <div style={{ padding: '12px', display: 'flex', gap: '8px', alignItems: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  <Loader2 size={14} className="animate-spin" />
                  <span>Loading topics...</span>
                </div>
              ) : (
                topics.map((t) => (
                  <div 
                    key={t.id}
                    onClick={() => setSelectedTopic(t)}
                    style={{ 
                      padding: '8px 12px', 
                      borderRadius: '6px', 
                      fontSize: '0.9rem', 
                      cursor: 'pointer',
                      background: selectedTopic?.id === t.id ? 'rgba(255,255,255,0.03)' : 'transparent',
                      borderLeft: selectedTopic?.id === t.id ? '2px solid var(--accent-primary)' : '2px solid transparent',
                      color: selectedTopic?.id === t.id ? 'var(--text-primary)' : 'var(--text-secondary)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    {t.name}
                  </div>
                ))
              )}
            </div>

            {/* Quick Topic Creator */}
            <form onSubmit={handleCreateTopic} style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '12px', paddingTop: '12px', borderTop: '1px solid var(--border-color)' }}>
              <input
                type="text"
                required
                disabled={isCreatingTopic}
                placeholder="Add study topic..."
                value={newTopicName}
                onChange={(e) => setNewTopicName(e.target.value)}
                style={{
                  flex: 1,
                  padding: '8px 10px',
                  fontSize: '0.8rem',
                  borderRadius: '6px',
                  background: 'rgba(0, 0, 0, 0.2)',
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-primary)'
                }}
              />
              <button 
                type="submit" 
                disabled={isCreatingTopic || !newTopicName.trim()}
                className="btn btn-primary"
                style={{ padding: '8px 10px', borderRadius: '6px', fontSize: '0.8rem' }}
              >
                {isCreatingTopic ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
              </button>
            </form>
          </div>
        </div>

        {/* Infrastructure Indicator and Logout */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Database Status Widget */}
          <div className="glass-card" style={{ padding: '16px', background: 'rgba(255,255,255,0.02)', borderRadius: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <Database size={16} color={dbConnected ? 'var(--accent-teal)' : '#f59e0b'} />
              <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Local Infrastructure</span>
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
              {dbConnected ? 'Postgres + pgvector is online and ready.' : 'Database offline or starting...'}
            </p>
            <button 
              onClick={checkHealth}
              className="btn btn-secondary" 
              style={{ width: '100%', padding: '6px 12px', fontSize: '0.8rem', borderRadius: '6px' }}
            >
              Test Connection
            </button>
          </div>

          {/* Logout Button */}
          <button 
            onClick={handleLogout}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              width: '100%',
              padding: '12px 16px',
              border: '1px solid rgba(239, 68, 68, 0.2)',
              background: 'rgba(239, 68, 68, 0.05)',
              color: '#ef4444',
              borderRadius: '8px',
              cursor: 'pointer',
              textAlign: 'left',
              fontWeight: 600,
              transition: 'var(--transition-fast)'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(239, 68, 68, 0.05)';
            }}
          >
            <LogOut size={18} />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Main Panel */}
      <main style={{ flex: 1, padding: '40px', overflowY: 'auto', height: '100vh' }}>
        {/* Header */}
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '40px' }}>
          <div>
            <span style={{ fontSize: '0.85rem', color: 'var(--accent-primary)', fontWeight: 600, textTransform: 'uppercase' }}>Workspace: local_host_dev</span>
            <h2 style={{ fontSize: '1.8rem', fontFamily: 'var(--font-display)', margin: 0 }}>Active Subject: {selectedTopic?.name || 'Loading topics...'}</h2>
          </div>
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
            {/* Database status widget */}
            <div className="glass-card" style={{ padding: '8px 16px', borderRadius: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: dbConnected ? 'var(--accent-teal)' : '#f59e0b' }}></div>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Status: {dbConnected ? 'Online' : 'Configuring'}</span>
            </div>
            
            {/* User Profile widget */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', paddingLeft: '16px', borderLeft: '1px solid var(--border-color)' }}>
              <div style={{ textAlign: 'right' }}>
                <p style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
                  {user?.display_name || user?.email?.split('@')[0]}
                </p>
                <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', margin: 0 }}>
                  {user?.plan_tier ? `${user.plan_tier.toUpperCase()} Member` : 'Free Scholar'}
                </p>
              </div>
              <div style={{
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                border: '2px solid var(--accent-primary-glow)',
                overflow: 'hidden',
                background: 'rgba(255,255,255,0.05)'
              }}>
                <img
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuARmHieBq0AtO28rAhGCQalLv-ogF1Zu5wy0dcWHBEKZNP6LpXLW5sf97h2d9uCWhoYXf5rEHGbT6RTUtN-23wHvh3a7gwNWW4T6hzLx0a15mPrT7J6DmHt_MpRzEbKJbIjrZgq9Adg-Wy6AqfpSTD6hKu3PiE6FHuIRafHFRSTL_lMJl8PTQpSsVIcSlUggAf81z89uLzqG2P6uaGL8FBZqhpyc4a74x9XFOB_QuByoSJaWNcHqts2oGUsXIuWBTz1WHVbUqw7sRXg"
                  alt="Avatar"
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
              </div>
            </div>
          </div>
        </header>

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
            {/* Hero Welcome banner */}
            <div className="glass-card" style={{ 
              background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(168, 85, 247, 0.1) 100%)',
              border: '1px solid rgba(99, 102, 241, 0.2)',
              position: 'relative',
              overflow: 'hidden'
            }}>
              <div style={{ position: 'relative', zIndex: 2 }}>
                <h1 style={{ marginBottom: '12px' }}>Welcome to ExamPrep AI!</h1>
                <p style={{ color: 'var(--text-secondary)', maxWidth: '600px', fontSize: '1.05rem', marginBottom: '20px' }}>
                  A local-first environment for document parsing, semantic chunk database search, and automated mock exam preparation using pgvector and Gemini APIs.
                </p>
                <div style={{ display: 'flex', gap: '12px' }}>
                  <button onClick={() => setActiveTab('setup')} className="btn btn-primary">
                    Start Setup Wizard <ChevronRight size={16} />
                  </button>
                </div>
              </div>
              <div style={{ 
                position: 'absolute', 
                right: '-30px', 
                bottom: '-30px', 
                fontSize: '12rem', 
                opacity: 0.1, 
                userSelect: 'none',
                transform: 'rotate(15deg)'
              }}>
                🎓
              </div>
            </div>

            {/* Config files checklist and Directory Status */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
              <div className="glass-card">
                <h3 style={{ fontSize: '1.25rem', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <CheckCircle2 color="var(--accent-teal)" size={20} />
                  System Pipeline Status
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '12px', borderBottom: '1px solid var(--border-color)' }}>
                    <div>
                      <strong style={{ display: 'block', fontSize: '0.95rem' }}>Active Topic Domain</strong>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Currently selected subject scope</span>
                    </div>
                    <span style={{ color: selectedTopic ? 'var(--accent-teal)' : 'var(--text-muted)', fontSize: '0.85rem', fontWeight: 600 }}>
                      {selectedTopic ? selectedTopic.name : 'None Selected'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '12px', borderBottom: '1px solid var(--border-color)' }}>
                    <div>
                      <strong style={{ display: 'block', fontSize: '0.95rem' }}>Ingested Documents</strong>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Files parsed in active topic</span>
                    </div>
                    <span style={{ color: documents.length > 0 ? 'var(--accent-teal)' : 'var(--text-muted)', fontSize: '0.85rem', fontWeight: 600 }}>
                      {documents.length} File(s)
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '12px', borderBottom: '1px solid var(--border-color)' }}>
                    <div>
                      <strong style={{ display: 'block', fontSize: '0.95rem' }}>Postgres pgvector Vectorizer</strong>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Tracks whether DB structure is loaded</span>
                    </div>
                    <span style={{ color: dbConnected ? 'var(--accent-teal)' : 'var(--text-muted)', fontSize: '0.85rem', fontWeight: 600 }}>
                      {dbConnected ? 'Online' : 'Offline'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="glass-card">
                <h3 style={{ fontSize: '1.25rem', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <FolderOpen color="var(--accent-primary)" size={20} />
                  Workspace Summary
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '10px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
                    <div style={{ color: 'var(--accent-primary)' }}><FolderOpen size={20} /></div>
                    <div style={{ flex: 1 }}>
                      <strong style={{ fontSize: '0.9rem', display: 'block' }}>Topic Directories</strong>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{topics.length} study topics configured</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '10px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
                    <div style={{ color: 'var(--accent-teal)' }}><Database size={20} /></div>
                    <div style={{ flex: 1 }}>
                      <strong style={{ fontSize: '0.9rem', display: 'block' }}>Ingested Sources</strong>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>All segments stored in content_chunks table</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Setup wizard screen */}
        {activeTab === 'setup' && (
          <div className="fade-in glass-card">
            <h2 style={{ marginBottom: '24px', fontFamily: 'var(--font-display)' }}>Setup Wizard & Document Ingestion</h2>
            
            <div style={{ display: 'grid', gridTemplateColumns: '3fr 2fr', gap: '32px' }}>
              <div>
                <div className="form-group">
                  <label>1. Target Topic Domain</label>
                  <select 
                    value={selectedTopic?.id || ''} 
                    onChange={(e) => {
                      const topic = topics.find(t => t.id === e.target.value);
                      if (topic) setSelectedTopic(topic);
                    }}
                    style={{ width: '100%' }}
                  >
                    {topics.map((t) => (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group" style={{ marginBottom: '24px' }}>
                  <label>2. Choose Ingestion Method</label>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginTop: '4px' }}>
                    <div style={{ border: '1px solid var(--accent-primary)', padding: '16px', borderRadius: '8px', cursor: 'pointer', background: 'rgba(99, 102, 241, 0.05)' }}>
                      <strong style={{ display: 'block', marginBottom: '4px' }}>File Upload</strong>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Upload PDF, Markdown or TXT syllabus document.</span>
                    </div>
                    <div style={{ border: '1px solid var(--border-color)', padding: '16px', borderRadius: '8px', cursor: 'not-allowed', opacity: 0.5 }}>
                      <strong style={{ display: 'block', marginBottom: '4px' }}>Syllabus Text Input</strong>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Paste raw syllabus requirements text (Coming soon).</span>
                    </div>
                  </div>
                </div>

                {/* Drag and Drop Zone */}
                <div 
                  onDragOver={handleDragOver}
                  onDrop={handleDrop}
                  onClick={() => !uploading && fileInputRef.current?.click()}
                  style={{ 
                    border: '2px dashed var(--border-color)', 
                    borderRadius: '12px', 
                    padding: '32px', 
                    textAlign: 'center', 
                    marginBottom: '24px',
                    cursor: uploading ? 'not-allowed' : 'pointer',
                    background: 'rgba(255,255,255,0.01)',
                    transition: 'border-color 0.2s ease',
                    position: 'relative'
                  }}
                  onMouseEnter={(e) => {
                    if (!uploading) e.currentTarget.style.borderColor = 'var(--accent-primary)';
                  }}
                  onMouseLeave={(e) => {
                    if (!uploading) e.currentTarget.style.borderColor = 'var(--border-color)';
                  }}
                >
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileSelect}
                    accept=".pdf,.txt,.md"
                    style={{ display: 'none' }}
                    disabled={uploading}
                  />
                  <Upload size={32} color="var(--text-muted)" style={{ marginBottom: '12px' }} />
                  {selectedFile ? (
                    <div>
                      <p style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                        {selectedFile.name}
                      </p>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {formatBytes(selectedFile.size)}
                      </span>
                    </div>
                  ) : (
                    <div>
                      <p style={{ fontSize: '0.95rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                        Drag & drop documents here, or click to select file
                      </p>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        Supports PDF, MD, TXT (Max 15MB)
                      </span>
                    </div>
                  )}
                </div>

                {/* Progress bar during uploads */}
                {uploading && (
                  <div style={{ marginBottom: '24px', padding: '16px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {jobStatus.toUpperCase() === 'PENDING' ? 'Queuing Ingestion Task...' : jobMessage}
                      </span>
                      <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-primary)' }}>
                        {jobProgress}%
                      </span>
                    </div>
                    {/* Background Progress Bar */}
                    <div style={{ height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                      <div style={{ 
                        height: '100%', 
                        width: `${jobProgress}%`, 
                        background: 'linear-gradient(90deg, var(--accent-primary) 0%, var(--accent-secondary) 100%)',
                        borderRadius: '3px',
                        transition: 'width 0.3s ease'
                      }} />
                    </div>
                  </div>
                )}

                <button 
                  disabled={!selectedFile || uploading || !selectedTopic}
                  onClick={handleIngestFile}
                  className="btn btn-primary" 
                  style={{ width: '100%' }}
                >
                  {uploading ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      <span>Vectorizing Document...</span>
                    </>
                  ) : (
                    'Submit and Run Ingestion'
                  )}
                </button>
              </div>

              <div>
                <h3 style={{ fontSize: '1.1rem', marginBottom: '16px' }}>Ingested Documents list</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto', maxHeight: '420px' }}>
                  {isLoadingDocs ? (
                    <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                      <Loader2 size={24} className="animate-spin" style={{ margin: '0 auto 12px' }} />
                      <span>Fetching documents...</span>
                    </div>
                  ) : documents.length === 0 ? (
                    <div style={{
                      padding: '24px',
                      textAlign: 'center',
                      background: 'rgba(255, 255, 255, 0.02)',
                      border: '1px dashed var(--border-color)',
                      borderRadius: '8px',
                      color: 'var(--text-secondary)',
                      fontSize: '0.85rem'
                    }}>
                      No documents ingested yet. Upload a syllabus or study material to begin.
                    </div>
                  ) : (
                    documents.map((doc) => (
                      <div 
                        key={doc.id} 
                        style={{ 
                          display: 'flex', 
                          justifyContent: 'space-between', 
                          alignItems: 'center', 
                          padding: '12px', 
                          background: 'rgba(255,255,255,0.02)', 
                          borderRadius: '8px', 
                          border: '1px solid var(--border-color)' 
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0, flex: 1, paddingRight: '8px' }}>
                          <FileText size={18} color="var(--accent-secondary)" style={{ flexShrink: 0 }} />
                          <div style={{ minWidth: 0 }}>
                            <strong style={{ 
                              fontSize: '0.85rem', 
                              display: 'block', 
                              color: 'var(--text-primary)',
                              whiteSpace: 'nowrap',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis'
                            }}>
                              {doc.original_filename}
                            </strong>
                            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                              Type: {doc.source_type === 'upload_pdf' ? 'PDF Document' : 'Text/Markdown'}
                            </span>
                          </div>
                        </div>
                        
                        {/* Status Chip */}
                        <span style={{ 
                          fontSize: '0.75rem', 
                          padding: '2px 8px', 
                          borderRadius: '10px', 
                          background: doc.status === 'parsed' ? 'rgba(20, 184, 166, 0.1)' 
                            : doc.status === 'failed' ? 'rgba(239, 68, 68, 0.1)'
                            : 'rgba(168, 85, 247, 0.1)', 
                          color: doc.status === 'parsed' ? 'var(--accent-teal)' 
                            : doc.status === 'failed' ? '#ef4444'
                            : 'var(--accent-secondary)',
                          textTransform: 'capitalize',
                          flexShrink: 0
                        }}>
                          {doc.status}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Mock Exam simulator screen */}
        {activeTab === 'exam' && (
          <div className="fade-in glass-card" style={{ textAlign: 'center', padding: '60px 40px' }}>
            <Clock size={48} color="var(--accent-primary)" style={{ marginBottom: '16px' }} />
            <h2 style={{ marginBottom: '12px' }}>Exam Simulator ready</h2>
            <p style={{ color: 'var(--text-secondary)', maxWidth: '500px', margin: '0 auto 24px' }}>
              Once you run document ingestion and compile questions, you will be able to launch timed exam sets or customized practice sessions directly from this screen.
            </p>
            <div style={{ display: 'flex', justifyContent: 'center', gap: '12px' }}>
              <button onClick={() => setActiveTab('setup')} className="btn btn-primary">Go to Document Ingestion</button>
            </div>
          </div>
        )}

        {/* Mock results screen */}
        {activeTab === 'results' && (
          <div className="fade-in glass-card" style={{ textAlign: 'center', padding: '60px 40px' }}>
            <TrendingUp size={48} color="var(--accent-secondary)" style={{ marginBottom: '16px' }} />
            <h2 style={{ marginBottom: '12px' }}>No attempt records found</h2>
            <p style={{ color: 'var(--text-secondary)', maxWidth: '500px', margin: '0 auto 24px' }}>
              Complete your first exam practice or simulation to populate metrics, score breakdowns, and tag correctness reports on this dashboard.
            </p>
            <button onClick={() => setActiveTab('setup')} className="btn btn-secondary">Prepare First Exam</button>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
