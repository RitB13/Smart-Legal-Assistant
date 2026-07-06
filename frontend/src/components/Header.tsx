import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Scale, Menu, X, LogOut, User, ChevronDown, History } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';

const NAV_LINKS = [
  { path: '/chat',      label: 'Legal Assistant' },
  { path: '/predict',   label: 'Case Predictor' },
  { path: '/mediation', label: 'Mediation' },
  { path: '/upload',    label: 'Documents' },
  { path: '/rights',    label: 'Know Your Rights' },
];

export default function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // Close user menu on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  function handleLogout() {
    logout();
    navigate('/');
    setUserMenuOpen(false);
  }

  const isActive = (path: string) =>
    path === '/' ? location.pathname === '/' : location.pathname.startsWith(path);

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-200 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/80">
      <div className="max-w-6xl mx-auto px-4">
        <div className="flex h-14 items-center justify-between gap-6">

          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 flex-shrink-0">
            <Scale className="h-5 w-5 text-primary" />
            <span className="text-sm font-bold text-slate-900">
              Smart Legal<span className="text-primary"> Assistant</span>
            </span>
          </Link>

          {/* Desktop nav — only shown when authenticated */}
          {isAuthenticated && (
            <nav className="hidden md:flex items-center gap-1 flex-1">
              {NAV_LINKS.map(link => (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                    isActive(link.path)
                      ? 'bg-primary/8 text-primary font-medium'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }`}
                >
                  {link.label}
                </Link>
              ))}
            </nav>
          )}

          {/* Right side */}
          <div className="flex items-center gap-2 flex-shrink-0">
            {isAuthenticated ? (
              <>
                {/* User menu */}
                <div className="relative" ref={userMenuRef}>
                  <button
                    onClick={() => setUserMenuOpen(o => !o)}
                    className="hidden md:flex items-center gap-1.5 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
                  >
                    <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center">
                      <User className="h-3.5 w-3.5 text-primary" />
                    </div>
                    <span className="max-w-[120px] truncate font-medium">{user?.name?.split(' ')[0]}</span>
                    <ChevronDown className={`h-3.5 w-3.5 text-slate-400 transition-transform ${userMenuOpen ? 'rotate-180' : ''}`} />
                  </button>

                  {userMenuOpen && (
                    <div className="absolute right-0 top-full mt-1.5 w-52 bg-white border border-slate-200 rounded-xl shadow-lg py-1 z-50">
                      <div className="px-3 py-2 border-b border-slate-100">
                        <p className="text-xs font-semibold text-slate-800 truncate">{user?.name}</p>
                        <p className="text-xs text-slate-400 truncate">{user?.email}</p>
                      </div>
                      <Link
                        to="/predictions"
                        onClick={() => setUserMenuOpen(false)}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors"
                      >
                        <History className="h-4 w-4" /> My Predictions
                      </Link>
                      <button
                        onClick={handleLogout}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 hover:text-red-600 transition-colors"
                      >
                        <LogOut className="h-4 w-4" /> Sign out
                      </button>
                    </div>
                  )}
                </div>

                {/* Mobile hamburger */}
                <button
                  onClick={() => setMobileOpen(o => !o)}
                  className="md:hidden p-2 text-slate-600 hover:text-slate-900 rounded-lg hover:bg-slate-100 transition-colors"
                >
                  {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
                </button>
              </>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  to="/login"
                  className="text-sm font-medium text-slate-600 hover:text-slate-900 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition-colors"
                >
                  Sign in
                </Link>
                <Link
                  to="/register"
                  className="text-sm font-medium text-white bg-primary px-3 py-1.5 rounded-lg hover:opacity-90 transition-opacity"
                >
                  Get started
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Mobile nav menu */}
        {isAuthenticated && mobileOpen && (
          <nav className="md:hidden border-t border-slate-100 py-3 space-y-0.5">
            {NAV_LINKS.map(link => (
              <Link
                key={link.path}
                to={link.path}
                onClick={() => setMobileOpen(false)}
                className={`block px-3 py-2.5 text-sm rounded-lg transition-colors ${
                  isActive(link.path)
                    ? 'bg-primary/8 text-primary font-medium'
                    : 'text-slate-600 hover:bg-slate-50'
                }`}
              >
                {link.label}
              </Link>
            ))}
            <div className="border-t border-slate-100 pt-2 mt-2">
              <div className="px-3 py-1 text-xs text-slate-400 font-medium">{user?.email}</div>
              <Link
                to="/predictions"
                onClick={() => setMobileOpen(false)}
                className={`block px-3 py-2.5 text-sm rounded-lg transition-colors ${
                  isActive('/predictions')
                    ? 'bg-primary/8 text-primary font-medium'
                    : 'text-slate-600 hover:bg-slate-50'
                }`}
              >
                My Predictions
              </Link>
              <button
                onClick={handleLogout}
                className="w-full text-left px-3 py-2.5 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors flex items-center gap-2"
              >
                <LogOut className="h-4 w-4" /> Sign out
              </button>
            </div>
          </nav>
        )}
      </div>
    </header>
  );
}
