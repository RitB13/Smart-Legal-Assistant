import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Scale, Menu, X, LogOut, User, ChevronDown, History, Sun, Moon } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';

const NAV_LINKS = [
  { path: '/chat',      label: 'Legal Assistant' },
  { path: '/predict',   label: 'Case Predictor' },
  { path: '/mediation', label: 'Mediation' },
  { path: '/rights',    label: 'Know Your Rights' },
];

function ThemeToggleButton({ className = '' }: { className?: string }) {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <button
      onClick={toggleTheme}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      className={`relative flex items-center gap-1.5 ${className}`}
    >
      {/* Track */}
      <div
        className={`relative w-11 h-6 rounded-full transition-all duration-300 ${
          isDark
            ? 'bg-blue-600 shadow-[0_0_8px_rgba(79,172,254,0.5)]'
            : 'bg-slate-200'
        }`}
      >
        {/* Sliding dot */}
        <span
          className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow-md transition-transform duration-300 ease-in-out flex items-center justify-center ${
            isDark ? 'translate-x-5' : 'translate-x-0'
          }`}
        >
          {isDark
            ? <Moon className="h-3 w-3 text-blue-500" />
            : <Sun className="h-3 w-3 text-amber-400" />
          }
        </span>
      </div>

    </button>
  );
}

export default function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    }
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setUserMenuOpen(false);
        setMobileOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleKey);
    };
  }, []);

  function handleLogout() {
    logout();
    navigate('/');
    setUserMenuOpen(false);
  }

  const isActive = (path: string) =>
    path === '/' ? location.pathname === '/' : location.pathname.startsWith(path);

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-200 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/80 dark:bg-slate-900/95 dark:border-slate-700/50">
      <div className="max-w-6xl mx-auto px-4">
        <div className="flex h-14 items-center justify-between gap-6">

          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 flex-shrink-0">
            <Scale className="h-5 w-5 text-primary" />
            <span className="text-sm font-bold text-slate-900 dark:text-white">
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
                      ? 'bg-primary/8 text-primary font-medium dark:bg-blue-500/15 dark:text-blue-300'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-300 dark:hover:text-white dark:hover:bg-slate-700/50'
                  }`}
                >
                  {link.label}
                </Link>
              ))}
            </nav>
          )}

          {/* Right side */}
          <div className="flex items-center gap-2 flex-shrink-0">

            {/* Theme toggle — desktop, always visible */}
            <ThemeToggleButton className="hidden md:flex" />

            {isAuthenticated ? (
              <>
                {/* User menu */}
                <div className="relative" ref={userMenuRef}>
                  <button
                    onClick={() => setUserMenuOpen(o => !o)}
                    className="hidden md:flex items-center gap-1.5 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100 rounded-lg transition-colors dark:text-slate-300 dark:hover:bg-slate-700/50"
                  >
                    <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center dark:bg-blue-500/20">
                      <User className="h-3.5 w-3.5 text-primary dark:text-blue-300" />
                    </div>
                    <span className="max-w-[120px] truncate font-medium">{user?.name?.split(' ')[0]}</span>
                    <ChevronDown className={`h-3.5 w-3.5 text-slate-400 dark:text-slate-500 transition-transform ${userMenuOpen ? 'rotate-180' : ''}`} />
                  </button>

                  {userMenuOpen && (
                    <div className="absolute right-0 top-full mt-1.5 w-52 bg-white border border-slate-200 rounded-xl shadow-lg py-1 z-50 dark:bg-slate-800 dark:border-slate-700">
                      <div className="px-3 py-2 border-b border-slate-100 dark:border-slate-700">
                        <p className="text-xs font-semibold text-slate-800 truncate dark:text-slate-200">{user?.name}</p>
                        <p className="text-xs text-slate-400 truncate dark:text-slate-500">{user?.email}</p>
                      </div>
                      <Link
                        to="/predictions"
                        onClick={() => setUserMenuOpen(false)}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors dark:text-slate-300 dark:hover:bg-slate-700/50 dark:hover:text-white"
                      >
                        <History className="h-4 w-4" /> My Predictions
                      </Link>
                      <button
                        onClick={handleLogout}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 hover:text-red-600 transition-colors dark:text-slate-300 dark:hover:bg-red-900/20 dark:hover:text-red-400"
                      >
                        <LogOut className="h-4 w-4" /> Sign out
                      </button>
                    </div>
                  )}
                </div>

                {/* Mobile hamburger */}
                <button
                  onClick={() => setMobileOpen(o => !o)}
                  className="md:hidden p-2 text-slate-600 hover:text-slate-900 rounded-lg hover:bg-slate-100 transition-colors dark:text-slate-400 dark:hover:text-white dark:hover:bg-slate-700/50"
                >
                  {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
                </button>
              </>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  to="/login"
                  className="text-sm font-medium text-slate-600 hover:text-slate-900 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition-colors dark:text-slate-300 dark:hover:text-white dark:hover:bg-slate-700/50"
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

        {/* Mobile nav menu (authenticated) */}
        {isAuthenticated && (
          <nav
            className={`md:hidden border-t border-slate-100 dark:border-slate-700/50 overflow-hidden transition-all duration-200 ease-in-out ${
              mobileOpen ? 'max-h-96 py-3 opacity-100' : 'max-h-0 py-0 opacity-0'
            } space-y-0.5`}
          >
            {NAV_LINKS.map(link => (
              <Link
                key={link.path}
                to={link.path}
                onClick={() => setMobileOpen(false)}
                className={`block px-3 py-2.5 text-sm rounded-lg transition-colors ${
                  isActive(link.path)
                    ? 'bg-primary/8 text-primary font-medium dark:bg-blue-500/15 dark:text-blue-300'
                    : 'text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-700/30'
                }`}
              >
                {link.label}
              </Link>
            ))}
            <div className="border-t border-slate-100 dark:border-slate-700/50 pt-2 mt-2">
              <div className="px-3 py-1 text-xs text-slate-400 font-medium dark:text-slate-500">{user?.email}</div>
              {/* Theme toggle row in mobile menu */}
              <div className="px-3 py-1.5">
                <ThemeToggleButton className="justify-center" />
              </div>
              <Link
                to="/predictions"
                onClick={() => setMobileOpen(false)}
                className={`block px-3 py-2.5 text-sm rounded-lg transition-colors ${
                  isActive('/predictions')
                    ? 'bg-primary/8 text-primary font-medium dark:bg-blue-500/15 dark:text-blue-300'
                    : 'text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-700/30'
                }`}
              >
                My Predictions
              </Link>
              <button
                onClick={handleLogout}
                className="w-full text-left px-3 py-2.5 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors flex items-center gap-2 dark:text-red-400 dark:hover:bg-red-900/20"
              >
                <LogOut className="h-4 w-4" /> Sign out
              </button>
            </div>
          </nav>
        )}

        {/* Mobile theme toggle row — unauthenticated only (no hamburger menu available) */}
        {!isAuthenticated && (
          <div className="md:hidden flex justify-end pb-2">
            <ThemeToggleButton />
          </div>
        )}
      </div>
    </header>
  );
}
