import { useState } from 'react';
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
  LogOut
} from 'lucide-react';
import { AuthPage } from './pages/AuthPage';

function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'));
  const [user, setUser] = useState<any | null>(() => {
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });
  const [activeTab, setActiveTab] = useState<'dashboard' | 'setup' | 'exam' | 'results'>('dashboard');
  const [dbConnected, setDbConnected] = useState<boolean>(false);
  const [selectedTopic, setSelectedTopic] = useState<string>('DSA & System Design');
  const [filesUploaded] = useState<Array<{name: string, size: string, status: string}>>([]);

  const handleAuthSuccess = (newToken: string, newUser: any) => {
    setToken(newToken);
    setUser(newUser);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
  };

  if (!token) {
    return <AuthPage onAuthSuccess={handleAuthSuccess} />;
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-primary)' }}>
      {/* Sidebar Navigation */}
      <aside style={{ 
        width: '280px', 
        borderRight: '1px solid var(--border-color)', 
        background: 'var(--bg-secondary)', 
        display: 'flex', 
        flexDirection: 'column', 
        justifyContent: 'space-between',
        padding: '24px'
      }}>
        <div>
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
          <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
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
          <div style={{ marginTop: '32px' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Your Topics</span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '8px' }}>
              <div 
                onClick={() => setSelectedTopic('DSA & System Design')}
                style={{ 
                  padding: '8px 12px', 
                  borderRadius: '6px', 
                  fontSize: '0.9rem', 
                  cursor: 'pointer',
                  background: selectedTopic === 'DSA & System Design' ? 'rgba(255,255,255,0.03)' : 'transparent',
                  borderLeft: selectedTopic === 'DSA & System Design' ? '2px solid var(--accent-primary)' : '2px solid transparent',
                  color: selectedTopic === 'DSA & System Design' ? 'var(--text-primary)' : 'var(--text-secondary)'
                }}
              >
                DSA & System Design
              </div>
              <div 
                onClick={() => setSelectedTopic('Salesforce Dev')}
                style={{ 
                  padding: '8px 12px', 
                  borderRadius: '6px', 
                  fontSize: '0.9rem', 
                  cursor: 'pointer',
                  background: selectedTopic === 'Salesforce Dev' ? 'rgba(255,255,255,0.03)' : 'transparent',
                  borderLeft: selectedTopic === 'Salesforce Dev' ? '2px solid var(--accent-primary)' : '2px solid transparent',
                  color: selectedTopic === 'Salesforce Dev' ? 'var(--text-secondary)' : 'var(--text-secondary)'
                }}
              >
                Salesforce Certification
              </div>
            </div>
          </div>
        </div>

        {/* Database Status Widget */}
        <div className="glass-card" style={{ padding: '16px', background: 'rgba(255,255,255,0.02)', borderRadius: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <Database size={16} color={dbConnected ? 'var(--accent-teal)' : '#f59e0b'} />
            <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Local Infrastructure</span>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            {dbConnected ? 'Postgres + pgvector is online and ready.' : 'Database config created. Ready to launch.'}
          </p>
          <button 
            onClick={() => setDbConnected(!dbConnected)}
            className="btn btn-secondary" 
            style={{ width: '100%', padding: '6px 12px', fontSize: '0.8rem', borderRadius: '6px' }}
          >
            {dbConnected ? 'Disconnect DB' : 'Simulate Connect'}
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
            marginTop: '16px',
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
      </aside>

      {/* Main Panel */}
      <main style={{ flex: 1, padding: '40px', overflowY: 'auto' }}>
        {/* Header */}
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '40px' }}>
          <div>
            <span style={{ fontSize: '0.85rem', color: 'var(--accent-primary)', fontWeight: 600, textTransform: 'uppercase' }}>Workspace: local_host_dev</span>
            <h2 style={{ fontSize: '1.8rem', fontFamily: 'var(--font-display)', margin: 0 }}>Active Subject: {selectedTopic}</h2>
          </div>
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
            {/* Database status widget */}
            <div className="glass-card" style={{ padding: '8px 16px', borderRadius: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: dbConnected ? 'var(--accent-teal)' : '#f59e0b' }}></div>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Status: {dbConnected ? 'Online' : 'Configured'}</span>
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
                <h1 style={{ marginBottom: '12px' }}>Initial Scaffolding Completed!</h1>
                <p style={{ color: 'var(--text-secondary)', maxWidth: '600px', fontSize: '1.05rem', marginBottom: '20px' }}>
                  The folder structures for the frontend, backend, configuration profiles, and database mappings have been created successfully. All items are tracked according to the system documentation guidelines.
                </p>
                <div style={{ display: 'flex', gap: '12px' }}>
                  <button onClick={() => setActiveTab('setup')} className="btn btn-primary">
                    Start Setup Wizard <ChevronRight size={16} />
                  </button>
                  <a href="file:///c:/Users/abhas/My%20Workspace/projects/ai-exam-portal/README.md" target="_blank" rel="noreferrer" className="btn btn-secondary">
                    View README
                  </a>
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
                  Scaffolded Configuration Files
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '12px', borderBottom: '1px solid var(--border-color)' }}>
                    <div>
                      <strong style={{ display: 'block', fontSize: '0.95rem' }}>.gitignore</strong>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Excludes .venv, node_modules, and uploads directory</span>
                    </div>
                    <span style={{ color: 'var(--accent-teal)', fontSize: '0.85rem', fontWeight: 600 }}>Active</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '12px', borderBottom: '1px solid var(--border-color)' }}>
                    <div>
                      <strong style={{ display: 'block', fontSize: '0.95rem' }}>README.md</strong>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Explains system stack and quick start guidelines</span>
                    </div>
                    <span style={{ color: 'var(--accent-teal)', fontSize: '0.85rem', fontWeight: 600 }}>Active</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '12px', borderBottom: '1px solid var(--border-color)' }}>
                    <div>
                      <strong style={{ display: 'block', fontSize: '0.95rem' }}>changelog.md</strong>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Tracks versions, updates, and code iterations</span>
                    </div>
                    <span style={{ color: 'var(--accent-teal)', fontSize: '0.85rem', fontWeight: 600 }}>Active</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <div>
                      <strong style={{ display: 'block', fontSize: '0.95rem' }}>docker-compose.yml</strong>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>PostgreSQL with pgvector vector database setup</span>
                    </div>
                    <span style={{ color: 'var(--accent-teal)', fontSize: '0.85rem', fontWeight: 600 }}>Active</span>
                  </div>
                </div>
              </div>

              <div className="glass-card">
                <h3 style={{ fontSize: '1.25rem', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <FolderOpen color="var(--accent-primary)" size={20} />
                  Workspace Directories
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '10px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
                    <div style={{ color: 'var(--accent-primary)' }}><FolderOpen size={20} /></div>
                    <div style={{ flex: 1 }}>
                      <strong style={{ fontSize: '0.9rem', display: 'block' }}>backend/app/</strong>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>FastAPI models, schemas, routers, and services</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '10px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
                    <div style={{ color: 'var(--accent-secondary)' }}><FolderOpen size={20} /></div>
                    <div style={{ flex: 1 }}>
                      <strong style={{ fontSize: '0.9rem', display: 'block' }}>frontend/src/</strong>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>React + TS, modular components, custom styling</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '10px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
                    <div style={{ color: 'var(--accent-teal)' }}><FolderOpen size={20} /></div>
                    <div style={{ flex: 1 }}>
                      <strong style={{ fontSize: '0.9rem', display: 'block' }}>data/uploads/</strong>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Local file upload path (Git ignored for security)</span>
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
                  <label>1. Select Topic Domain</label>
                  <select value={selectedTopic} onChange={(e) => setSelectedTopic(e.target.value)}>
                    <option value="DSA & System Design">DSA & System Design</option>
                    <option value="Salesforce Dev">Salesforce Certification</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>2. Choose Ingestion Method</label>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginTop: '4px' }}>
                    <div style={{ border: '1px solid var(--accent-primary)', padding: '16px', borderRadius: '8px', cursor: 'pointer', background: 'rgba(99, 102, 241, 0.05)' }}>
                      <strong style={{ display: 'block', marginBottom: '4px' }}>File Upload</strong>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Upload PDF, Markdown or Text syllabus document.</span>
                    </div>
                    <div style={{ border: '1px solid var(--border-color)', padding: '16px', borderRadius: '8px', cursor: 'not-allowed', opacity: 0.5 }}>
                      <strong style={{ display: 'block', marginBottom: '4px' }}>Syllabus Text Input</strong>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Paste raw syllabus requirements text.</span>
                    </div>
                  </div>
                </div>

                <div style={{ border: '2px dashed var(--border-color)', borderRadius: '12px', padding: '32px', textAlign: 'center', marginBottom: '24px' }}>
                  <Upload size={32} color="var(--text-muted)" style={{ marginBottom: '12px' }} />
                  <p style={{ fontSize: '0.95rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>Drag & drop documents here, or click to select files</p>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Supports PDF, MD, TXT (Max 15MB)</span>
                </div>

                <button className="btn btn-primary" style={{ width: '100%' }}>
                  Submit and Run Ingestion
                </button>
              </div>

              <div>
                <h3 style={{ fontSize: '1.1rem', marginBottom: '16px' }}>Ingested Documents list</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {filesUploaded.length === 0 ? (
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
                    filesUploaded.map((file, idx) => (
                      <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <FileText size={18} color="var(--accent-secondary)" />
                          <div>
                            <strong style={{ fontSize: '0.85rem', display: 'block' }}>{file.name}</strong>
                            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{file.size}</span>
                          </div>
                        </div>
                        <span style={{ fontSize: '0.75rem', padding: '2px 8px', borderRadius: '10px', background: 'rgba(20, 184, 166, 0.1)', color: 'var(--accent-teal)' }}>
                          {file.status}
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
