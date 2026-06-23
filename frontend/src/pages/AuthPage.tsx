import React, { useState } from 'react';
import { GraduationCap, Bolt } from 'lucide-react';
import { LoginForm } from './LoginForm';
import { SignupForm } from './SignupForm';

// Since some lucide-react icons might be named differently, let's map simple svg-like elements or use generic icons
import { FileText, Activity } from 'lucide-react';

interface AuthPageProps {
  onAuthSuccess: (token: string, user: any) => void;
}

export const AuthPage: React.FC<AuthPageProps> = ({ onAuthSuccess }) => {
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');

  return (
    <div
      style={{
        minHeight: '100vh',
        width: '100vw',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        background: 'var(--bg-primary)',
        backgroundImage: `
        radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.15) 0px, transparent 50%),
        radial-gradient(at 100% 100%, rgba(168, 85, 247, 0.1) 0px, transparent 50%)
      `,
        backgroundAttachment: 'fixed',
        fontFamily: 'var(--font-sans)',
      }}
    >
      <main
        className="glass-card"
        style={{
          width: '100%',
          maxWidth: '1000px',
          borderRadius: '16px',
          overflow: 'hidden',
          boxShadow: '0 20px 50px rgba(0, 0, 0, 0.4)',
          display: 'flex',
          flexWrap: 'wrap',
          minHeight: '640px',
          padding: '0',
          border: '1px solid rgba(255, 255, 255, 0.08)',
        }}
      >
        {/* Left Column: Branding & Benefits */}
        <section
          style={{
            flex: '1 1 50%',
            background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
            padding: '48px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            position: 'relative',
            overflow: 'hidden',
            minWidth: '320px',
          }}
        >
          {/* Shimmer Effect */}
          <div
            className="shimmer"
            style={{
              position: 'absolute',
              inset: 0,
              opacity: 0.15,
              pointerEvents: 'none',
            }}
          ></div>

          <div style={{ position: 'relative', zIndex: 10 }}>
            {/* Logo */}
            <div
              style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '48px' }}
            >
              <div
                style={{
                  width: '48px',
                  height: '48px',
                  background: 'rgba(255, 255, 255, 0.2)',
                  backdropFilter: 'blur(8px)',
                  borderRadius: '10px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: '1px solid rgba(255, 255, 255, 0.3)',
                }}
              >
                <GraduationCap size={28} color="#fff" />
              </div>
              <h1
                style={{
                  fontSize: '1.75rem',
                  color: '#fff',
                  fontWeight: 700,
                  margin: 0,
                  background: 'none',
                  WebkitTextFillColor: 'initial',
                  fontFamily: 'var(--font-display)',
                  letterSpacing: '-0.02em',
                }}
              >
                AI Prep
              </h1>
            </div>

            <h2
              style={{
                fontSize: '2.25rem',
                lineHeight: '2.75rem',
                color: '#fff',
                fontWeight: 800,
                marginBottom: '32px',
                fontFamily: 'var(--font-display)',
                letterSpacing: '-0.03em',
              }}
            >
              The Future of Exam Readiness.
            </h2>

            {/* Benefits List */}
            <ul
              style={{ display: 'flex', flexDirection: 'column', gap: '16px', listStyle: 'none' }}
            >
              <li
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                  color: 'rgba(255, 255, 255, 0.9)',
                }}
              >
                <span
                  style={{
                    background: 'rgba(255, 255, 255, 0.1)',
                    padding: '8px',
                    borderRadius: '50%',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    display: 'flex',
                  }}
                >
                  <FileText size={18} />
                </span>
                <span style={{ fontSize: '1.1rem' }}>Upload Syllabi</span>
              </li>
              <li
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                  color: 'rgba(255, 255, 255, 0.9)',
                }}
              >
                <span
                  style={{
                    background: 'rgba(255, 255, 255, 0.1)',
                    padding: '8px',
                    borderRadius: '50%',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    display: 'flex',
                  }}
                >
                  <Bolt size={18} />
                </span>
                <span style={{ fontSize: '1.1rem' }}>Instant MCQ Generation</span>
              </li>
              <li
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                  color: 'rgba(255, 255, 255, 0.9)',
                }}
              >
                <span
                  style={{
                    background: 'rgba(255, 255, 255, 0.1)',
                    padding: '8px',
                    borderRadius: '50%',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    display: 'flex',
                  }}
                >
                  <Activity size={18} />
                </span>
                <span style={{ fontSize: '1.1rem' }}>Detailed Analytics</span>
              </li>
            </ul>
          </div>

          {/* Testimonial card */}
          <div
            style={{
              position: 'relative',
              zIndex: 10,
              marginTop: '48px',
              padding: '24px',
              background: 'rgba(255, 255, 255, 0.05)',
              backdropFilter: 'blur(4px)',
              borderRadius: '12px',
              border: '1px solid rgba(255, 255, 255, 0.1)',
            }}
          >
            <p
              style={{
                fontSize: '0.95rem',
                color: 'rgba(255, 255, 255, 0.8)',
                fontStyle: 'italic',
                lineHeight: '1.5',
                marginBottom: '16px',
              }}
            >
              "AI Prep transformed my study sessions. I went from feeling overwhelmed to completely
              prepared in just two weeks."
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div
                style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: '50%',
                  border: '2px solid rgba(255, 255, 255, 0.2)',
                  overflow: 'hidden',
                  background: '#131b2e',
                }}
              >
                <img
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuBb6oMTFoSqHENnynH1Hq9ACeZm9-ZFB1ldzhS2zckkqh3-s3OoDe3s4z9uiBCm39sTjBkfgzkRelTLuazTBZDO_vdbe5sPsg3aPwMsBG9omo4ndHDJXySRfdK8623-Bh1hktxARF0XFZar-6v3fGFx-tZArKA5uMbJPcnDMP9v140MG2N39-xn25WkuVnmQNg4jZ3J-3_6aP0EHotqv-iUjEFLO2BkQHffFG1SBTJXwQy_kqlvD2jBTuvJv7s1WQRGNiaUhPvjvr1L"
                  alt="Sarah Jenkins"
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
              </div>
              <div>
                <p style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fff', margin: 0 }}>
                  Sarah Jenkins
                </p>
                <p style={{ fontSize: '0.75rem', color: 'rgba(255, 255, 255, 0.6)', margin: 0 }}>
                  Medical Resident
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Right Column: Form Area */}
        <section
          style={{
            flex: '1 1 50%',
            background: 'var(--bg-secondary)',
            padding: '48px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            minWidth: '320px',
          }}
        >
          <div style={{ width: '100%', maxWidth: '380px', margin: '0 auto' }}>
            {/* Toggle Switch */}
            <div
              style={{
                display: 'flex',
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid var(--border-color)',
                padding: '4px',
                borderRadius: '9999px',
                marginBottom: '32px',
                position: 'relative',
              }}
            >
              {/* Sliding Background */}
              <div
                style={{
                  position: 'absolute',
                  top: '4px',
                  left: '4px',
                  width: 'calc(50% - 4px)',
                  height: 'calc(100% - 8px)',
                  background: 'var(--accent-primary)',
                  borderRadius: '9999px',
                  transition: 'transform var(--transition-normal)',
                  transform: mode === 'signin' ? 'translateX(0)' : 'translateX(100%)',
                  zIndex: 1,
                }}
              ></div>

              <button
                onClick={() => setMode('signin')}
                style={{
                  position: 'relative',
                  zIndex: 2,
                  flex: 1,
                  background: 'none',
                  border: 'none',
                  padding: '8px 0',
                  color: mode === 'signin' ? '#fff' : 'var(--text-secondary)',
                  fontWeight: 600,
                  fontSize: '0.875rem',
                  cursor: 'pointer',
                  borderRadius: '9999px',
                  transition: 'color var(--transition-fast)',
                }}
              >
                Sign In
              </button>
              <button
                onClick={() => setMode('signup')}
                style={{
                  position: 'relative',
                  zIndex: 2,
                  flex: 1,
                  background: 'none',
                  border: 'none',
                  padding: '8px 0',
                  color: mode === 'signup' ? '#fff' : 'var(--text-secondary)',
                  fontWeight: 600,
                  fontSize: '0.875rem',
                  cursor: 'pointer',
                  borderRadius: '9999px',
                  transition: 'color var(--transition-fast)',
                }}
              >
                Sign Up
              </button>
            </div>

            {/* Dynamic Form Render */}
            {mode === 'signin' ? (
              <LoginForm onSuccess={onAuthSuccess} onToggleMode={() => setMode('signup')} />
            ) : (
              <SignupForm onSuccess={onAuthSuccess} onToggleMode={() => setMode('signin')} />
            )}

            {/* Divider */}
            <div
              style={{
                position: 'relative',
                margin: '32px 0 24px',
                textAlign: 'center',
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  top: '50%',
                  left: 0,
                  right: 0,
                  borderTop: '1px solid var(--border-color)',
                  zIndex: 1,
                }}
              ></div>
              <span
                style={{
                  position: 'relative',
                  zIndex: 2,
                  background: 'var(--bg-secondary)',
                  padding: '0 16px',
                  fontSize: '0.75rem',
                  color: 'var(--text-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.1em',
                }}
              >
                Or continue with
              </span>
            </div>

            {/* Social Buttons */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <button
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '12px',
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  padding: '12px 0',
                  cursor: 'pointer',
                  transition: 'var(--transition-fast)',
                }}
                onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
              >
                <svg style={{ width: '20px', height: '20px' }} viewBox="0 0 24 24">
                  <path
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    fill="#4285F4"
                  ></path>
                  <path
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    fill="#34A853"
                  ></path>
                  <path
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"
                    fill="#FBBC05"
                  ></path>
                  <path
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                    fill="#EA4335"
                  ></path>
                </svg>
                <span
                  style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}
                >
                  Google
                </span>
              </button>
              <button
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '12px',
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  padding: '12px 0',
                  cursor: 'pointer',
                  transition: 'var(--transition-fast)',
                }}
                onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
              >
                <svg
                  style={{ width: '20px', height: '20px' }}
                  fill="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"></path>
                </svg>
                <span
                  style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}
                >
                  GitHub
                </span>
              </button>
            </div>

            <p
              style={{
                marginTop: '32px',
                textAlign: 'center',
                fontSize: '0.75rem',
                color: 'var(--text-muted)',
                lineHeight: '1.4',
              }}
            >
              By continuing, you agree to our{' '}
              <a
                href="#"
                style={{ color: 'var(--accent-primary)', textDecoration: 'none' }}
                onClick={e => e.preventDefault()}
              >
                Terms of Service
              </a>{' '}
              and{' '}
              <a
                href="#"
                style={{ color: 'var(--accent-primary)', textDecoration: 'none' }}
                onClick={e => e.preventDefault()}
              >
                Privacy Policy
              </a>
              .
            </p>
          </div>
        </section>
      </main>

      {/* Footer Decorative text */}
      <div
        style={{
          position: 'absolute',
          bottom: '24px',
          left: '24px',
          opacity: 0.1,
          pointerEvents: 'none',
          display: 'none', // hidden on mobile
        }}
        className="desktop-only"
      >
        <p
          style={{
            fontSize: '1rem',
            textTransform: 'uppercase',
            letterSpacing: '0.15em',
            fontWeight: 800,
          }}
        >
          Cognitive Edge Design
        </p>
      </div>

      <style>{`
        .shimmer::after {
          content: '';
          position: absolute;
          top: -50%;
          left: -50%;
          width: 200%;
          height: 200%;
          background: linear-gradient(
            to bottom right,
            rgba(255, 255, 255, 0) 0%,
            rgba(255, 255, 255, 0.08) 50%,
            rgba(255, 255, 255, 0) 100%
          );
          transform: rotate(45deg);
          animation: shimmerEffect 8s infinite linear;
        }

        @keyframes shimmerEffect {
          0% { transform: translate(-30%, -30%) rotate(45deg); }
          100% { transform: translate(30%, 30%) rotate(45deg); }
        }

        @media (min-width: 768px) {
          .desktop-only {
            display: block !important;
          }
        }
      `}</style>
    </div>
  );
};
