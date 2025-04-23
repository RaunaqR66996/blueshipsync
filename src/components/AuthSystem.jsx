import { useState } from 'react';
import { Mail, Lock, User, ArrowRight } from 'lucide-react';
import './AuthSystem.css'; // We'll create this CSS file

export default function AuthSystem() {
  const [currentView, setCurrentView] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState({ text: '', isError: false });

  const handleSubmit = (e) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage({ text: '', isError: false });

    // Simulate API call
    setTimeout(() => {
      setIsLoading(false);
      if (currentView === 'register') {
        if (password !== confirmPassword) {
          setMessage({ text: 'Passwords do not match', isError: true });
          return;
        }
        setMessage({ text: 'Registration successful!', isError: false });
        setCurrentView('login');
      } else {
        setMessage({ 
          text: currentView === 'login' ? 'Login successful!' : 'Reset link sent to your email',
          isError: false 
        });
      }
    }, 1000);
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2 className="auth-title">
          {currentView === 'login' && <><Lock className="auth-icon" /> Login</>}
          {currentView === 'register' && <><User className="auth-icon" /> Register</>}
          {currentView === 'reset' && <><Mail className="auth-icon" /> Reset Password</>}
        </h2>

        <p className="auth-subtitle">
          {currentView === 'login' && 'Enter your credentials to access your account'}
          {currentView === 'register' && 'Create a new account to get started'}
          {currentView === 'reset' && 'Enter your email to reset your password'}
        </p>

        {message.text && (
          <div className={`auth-message ${message.isError ? 'error' : 'success'}`}>
            {message.text}
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          {currentView === 'register' && (
            <div className="form-group">
              <input
                type="text"
                placeholder="Username"
                className="form-input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
          )}

          <div className="form-group">
            <input
              type="email"
              placeholder="Email address"
              className="form-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          {(currentView !== 'reset') && (
            <div className="form-group">
              <input
                type="password"
                placeholder="Password"
                className="form-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          )}

          {currentView === 'register' && (
            <div className="form-group">
              <input
                type="password"
                placeholder="Confirm Password"
                className="form-input"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </div>
          )}

          <button
            type="submit"
            className="auth-button"
            disabled={isLoading}
          >
            {isLoading ? 'Processing...' : (
              <>
                {currentView === 'login' && 'Login'}
                {currentView === 'register' && 'Register'}
                {currentView === 'reset' && 'Send Reset Link'}
                <ArrowRight className="button-icon" />
              </>
            )}
          </button>
        </form>

        <div className="auth-links">
          {currentView === 'login' && (
            <>
              <button className="auth-link" onClick={() => setCurrentView('register')}>Register</button>
              <button className="auth-link" onClick={() => setCurrentView('reset')}>Forgot Password?</button>
            </>
          )}
          {currentView !== 'login' && (
            <button className="auth-link" onClick={() => setCurrentView('login')}>Back to Login</button>
          )}
        </div>
      </div>
    </div>
  );
}