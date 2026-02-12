import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import './Dashboard.css';

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState({ tables: 0, menus: 0, orders: 0, stock: 0 });

  useEffect(() => {
    Promise.all([
      api.getTables(1, 1).then((d) => ({ tables: Array.isArray(d) ? d.length : 0 })),
      api.getMenus(1, 1).then((d) => ({ menus: Array.isArray(d) ? d.length : 0 })),
      api.getOrders(1, 1).then((d) => ({ orders: Array.isArray(d) ? d.length : 0 })),
      api.getStocks(1, 1).then((d) => ({ stock: Array.isArray(d) ? d.length : 0 })),
    ]).catch(() => ({})).then((arr) => {
      setStats((s) => ({
        ...s,
        ...Object.assign({}, ...arr),
      }));
    });

    const load = async () => {
      try {
        const [t, m, o, st] = await Promise.all([
          api.getTables(1, 100),
          api.getMenus(1, 100),
          api.getOrders(1, 100),
          api.getStocks(1, 100),
        ]);
        setStats({
          tables: Array.isArray(t) ? t.length : 0,
          menus: Array.isArray(m) ? m.length : 0,
          orders: Array.isArray(o) ? o.length : 0,
          stock: Array.isArray(st) ? st.length : 0,
        });
      } catch {
        // keep defaults
      }
    };
    load();
  }, []);

  const cards = [
    { label: 'Tables', value: stats.tables, to: '/tables', icon: '◫' },
    { label: 'Menu items', value: stats.menus, to: '/menu', icon: '☰' },
    { label: 'Orders', value: stats.orders, to: '/orders', icon: '📋' },
    { label: 'Stock items', value: stats.stock, to: '/stock', icon: '📦' },
  ];

  return (
    <div className="dashboard">
      <div className="page-header">
        <h1>Welcome back, {user?.firstname}</h1>
        <p>Manage your restaurant from one place.</p>
      </div>
      <div className="dashboard-grid">
        {cards.map(({ label, value, to, icon }) => (
          <Link key={to} to={to} className="dashboard-card">
            <span className="dashboard-card-icon">{icon}</span>
            <span className="dashboard-card-value">{value}</span>
            <span className="dashboard-card-label">{label}</span>
          </Link>
        ))}
      </div>
      <div className="card quick-links">
        <h2 className="quick-links-title">Quick links</h2>
        <div className="quick-links-grid">
          <Link to="/orders" className="btn btn-primary">View orders</Link>
          <Link to="/menu" className="btn btn-ghost">Edit menu</Link>
          <Link to="/payments" className="btn btn-ghost">Payments</Link>
          <Link to="/invoices" className="btn btn-ghost">Invoices</Link>
        </div>
      </div>
    </div>
  );
}
