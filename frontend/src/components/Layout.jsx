import { Outlet, NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Layout.css';

const nav = [
  { to: '/', label: 'Dashboard' },
  { to: '/menu', label: 'Menu' },
  { to: '/tables', label: 'Tables' },
  { to: '/orders', label: 'Orders' },
  { to: '/stock', label: 'Stock' },
  { to: '/invoices', label: 'Invoices' },
  { to: '/payments', label: 'Payments' },
  { to: '/restaurant', label: 'Restaurant' },
];

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="layout">
      <header className="layout-header">
        <div className="container layout-header-inner">
          <NavLink to="/" className="logo">
            Spice & Stories
          </NavLink>
          <nav className="nav">
            {nav.map(({ to, label }) => (
              <NavLink key={to} to={to} className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="header-actions">
            <span className="user-name">{user?.firstname} {user?.lastname}</span>
            <button type="button" className="btn btn-ghost" onClick={logout}>
              Logout
            </button>
          </div>
        </div>
      </header>
      <main className="layout-main">
        <div className="container">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
