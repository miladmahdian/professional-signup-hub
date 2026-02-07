import { Link, useLocation } from 'react-router-dom';

export default function Navbar() {
  const location = useLocation();

  const linkClass = (path) =>
    `px-4 py-2 rounded-md text-sm font-medium transition-colors ${
      location.pathname === path
        ? 'bg-indigo-600 text-white'
        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
    }`;

  return (
    <nav className="bg-white border-b border-gray-200 px-6 py-3">
      <div className="max-w-5xl mx-auto flex items-center justify-between">
        <h1 className="text-lg font-semibold text-gray-900">
          Professional Sign-Up Hub
        </h1>
        <div className="flex gap-2">
          <Link to="/professionals" className={linkClass('/professionals')}>
            Professionals
          </Link>
          <Link to="/professionals/new" className={linkClass('/professionals/new')}>
            Add Professional
          </Link>
        </div>
      </div>
    </nav>
  );
}
