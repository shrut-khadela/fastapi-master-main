import { useState, useEffect, useMemo } from 'react';
import { api } from '../api/client';
import './ManagePage.css';

const statusClass = (s) => {
  const v = (s || '').toLowerCase();
  if (v === 'pending') return 'badge-pending';
  if (v === 'ready') return 'badge-ready';
  if (v === 'cancelled') return 'badge-cancelled';
  if (v === 'preparing') return 'badge-preparing';
  return 'badge-pending';
};

/** Get display name from a menu item dict (API may use item_name, name, itemName, description, etc.) */
function getItemDisplayName(i) {
  const raw = (i.item_name ?? i.name ?? i.itemName ?? i.description ?? i.title ?? '').trim();
  return raw || 'Unnamed item';
}

/** Flatten all menu entries into a single list of { name, price, category } for ordering. Use per-item price, fallback to menu-level price. */
function flattenMenuItems(menus) {
  if (!Array.isArray(menus)) return [];
  const seen = new Set();
  const out = [];
  for (const m of menus) {
    const menuPrice = Number(m.price) || 0;
    let items = Array.isArray(m.item_list) ? m.item_list : [];
    items = items.map((i) => (typeof i === 'string' ? (() => { try { return JSON.parse(i); } catch { return {}; } })() : i));
    for (const i of items) {
      const name = getItemDisplayName(i);
      if (name === 'Unnamed item') continue;
      const price = Number(i.price) || menuPrice || 0;
      const category = (i.category_name || i.category || '').trim();
      const key = `${name}|${price}|${category}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push({ name, price, category });
    }
  }
  return out.sort((a, b) => (a.category || '').localeCompare(b.category || '') || a.name.localeCompare(b.name));
}

/** Parse order item_list string into cart array [{ name, price, qty }] */
function parseOrderItems(itemListStr) {
  try {
    const raw = typeof itemListStr === 'string' ? JSON.parse(itemListStr || '[]') : itemListStr;
    if (!Array.isArray(raw)) return [];
    return raw.map((el) => ({
      name: el.name || el.item_name || el.description || 'Item',
      price: Number(el.price) || 0,
      qty: Math.max(1, parseInt(el.qty ?? el.quantity ?? 1, 10)),
    }));
  } catch {
    return [];
  }
}

/** Build item_list JSON string from cart */
function cartToItemList(cart) {
  return JSON.stringify(
    cart.map(({ name, price, qty }) => ({ name, qty, price }))
  );
}

export default function OrdersPage() {
  const [list, setList] = useState([]);
  const [tables, setTables] = useState([]);
  const [menus, setMenus] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modal, setModal] = useState(null); // 'create' | order_id for edit
  const [form, setForm] = useState({ item_list: '[]', quantity: 0, table_no: '' });
  const [cart, setCart] = useState([]); // [{ name, price, qty }] for modal
  const [menuSearch, setMenuSearch] = useState('');
  const [statusForm, setStatusForm] = useState({ status: 'pending' });

  const menuItems = useMemo(() => flattenMenuItems(menus), [menus]);

  const load = () => {
    setLoading(true);
    Promise.all([
      api.getOrders(1, 100),
      api.getTables(1, 100),
      api.getMenus(1, 200),
    ])
      .then(([ordersData, tablesData, menusData]) => {
        setList(Array.isArray(ordersData) ? ordersData : []);
        setTables(Array.isArray(tablesData) ? tablesData : []);
        setMenus(Array.isArray(menusData) ? menusData : []);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => load(), []);

  const openCreate = () => {
    const firstTableNo = tables.length > 0 ? String(tables[0].table_no) : '';
    setForm({ item_list: '[]', quantity: 0, table_no: firstTableNo });
    setCart([]);
    setMenuSearch('');
    setModal('create');
    setError('');
  };

  const openEdit = (o) => {
    const itemListStr = typeof o.item_list === 'string' ? o.item_list : JSON.stringify(o.item_list || []);
    setForm({
      item_list: itemListStr,
      quantity: o.quantity ?? 0,
      table_no: String(o.table_id ?? o.table_no ?? (tables[0]?.table_no ?? '')),
    });
    setCart(parseOrderItems(itemListStr));
    setMenuSearch('');
    setModal(o.order_id);
    setError('');
  };

  const addToCart = (item, qty = 1) => {
    const n = Math.max(1, parseInt(qty, 10));
    setCart((prev) => {
      const i = prev.findIndex((c) => c.name === item.name && c.price === item.price);
      if (i >= 0) {
        const next = [...prev];
        next[i] = { ...next[i], qty: next[i].qty + n };
        return next;
      }
      return [...prev, { name: item.name, price: item.price, qty: n }];
    });
  };

  const updateCartQty = (index, delta) => {
    setCart((prev) => {
      const next = [...prev];
      const v = next[index].qty + delta;
      if (v <= 0) return next.filter((_, i) => i !== index);
      next[index] = { ...next[index], qty: v };
      return next;
    });
  };

  const removeFromCart = (index) => {
    setCart((prev) => prev.filter((_, i) => i !== index));
  };

  const filteredMenuItems = useMemo(() => {
    const q = (menuSearch || '').trim().toLowerCase();
    if (!q) return menuItems;
    return menuItems.filter(
      (i) =>
        i.name.toLowerCase().includes(q) ||
        (i.category || '').toLowerCase().includes(q)
    );
  }, [menuItems, menuSearch]);

  const saveOrder = async (e) => {
    e.preventDefault();
    setError('');
    const itemListStr = cart.length > 0 ? cartToItemList(cart) : form.item_list;
    const totalQty = cart.reduce((s, i) => s + i.qty, 0);
    try {
      const payload = {
        item_list: itemListStr,
        quantity: totalQty || Number(form.quantity) || 0,
        table_no: String(form.table_no),
      };
      if (modal === 'create') {
        await api.createOrder(payload);
      } else {
        await api.updateOrder(modal, payload);
      }
      setModal(null);
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  const updateStatus = async (orderId) => {
    setError('');
    try {
      await api.updateOrderStatus(orderId, { status: statusForm.status });
      setModal(null);
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  const doDelete = async (id) => {
    if (!confirm('Delete this order?')) return;
    try {
      await api.deleteOrder(id);
      setModal(null);
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="manage-page">
      <div className="page-header flex">
        <div>
          <h1>Orders</h1>
          <p>View and manage orders.</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={openCreate}>
          New order
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <p className="empty-state">Loading…</p>
      ) : list.length === 0 ? (
        <div className="empty-state card">
          <p>No orders yet.</p>
          <button type="button" className="btn btn-primary" onClick={openCreate}>
            New order
          </button>
        </div>
      ) : (
        <div className="table-wrap card">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Table</th>
                <th>Status</th>
                <th>Items (preview)</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {list.map((o, idx) => (
                <tr key={o.order_id}>
                  <td>{idx + 1}</td>
                  <td>Table {o.table_id}</td>
                  <td><span className={`badge ${statusClass(o.order_status)}`}>{o.order_status}</span></td>
                  <td>
                    {typeof o.item_list === 'string'
                      ? (o.item_list.length > 60 ? o.item_list.slice(0, 60) + '…' : o.item_list)
                      : '—'}
                  </td>
                  <td>
                    <button type="button" className="btn btn-ghost" onClick={() => { openEdit(o); setStatusForm({ status: o.order_status || 'pending' }); }}>Edit</button>
                    <button type="button" className="btn btn-danger" onClick={() => doDelete(o.order_id)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modal && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal card modal-order" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '640px' }}>
            <h2>{modal === 'create' ? 'New order' : 'Edit order'}</h2>
            <form onSubmit={saveOrder}>
              {error && <div className="alert alert-error">{error}</div>}

              <div className="form-group">
                <label>Search menu items</label>
                <input
                  type="text"
                  placeholder="Search by item name or category…"
                  value={menuSearch}
                  onChange={(e) => setMenuSearch(e.target.value)}
                  className="search-input"
                />
              </div>

              <div className="form-group">
                <label>Available menu items</label>
                <div className="menu-items-list">
                  {menuItems.length === 0 ? (
                    <p className="form-hint">No menu items yet. Add items in the Menu page first.</p>
                  ) : filteredMenuItems.length === 0 ? (
                    <p className="form-hint">No items match your search.</p>
                  ) : (
                    filteredMenuItems.map((item, idx) => (
                      <button
                        key={`${item.name}-${item.price}-${idx}`}
                        type="button"
                        className="menu-item-chip"
                        onClick={() => addToCart(item)}
                        title={`${item.name} — ₹${item.price}`}
                      >
                        <span className="menu-item-chip-main">
                          <span className="menu-item-name">{item.name || 'Unnamed item'}</span>
                          {item.category && <span className="menu-item-cat">{item.category}</span>}
                        </span>
                        <span className="menu-item-price">₹{item.price}</span>
                      </button>
                    ))
                  )}
                </div>
              </div>

              <div className="form-group">
                <label>Your order ({cart.reduce((s, i) => s + i.qty, 0)} items)</label>
                {cart.length === 0 ? (
                  <p className="form-hint">Click items above to add to order.</p>
                ) : (
                  <ul className="cart-list">
                    {cart.map((line, idx) => (
                      <li key={`${line.name}-${line.price}-${idx}`} className="cart-line">
                        <span className="cart-line-name">
                          <span className="cart-line-name-text">{line.name || 'Unnamed item'}</span>
                          <span className="cart-line-unit">₹{line.price} each</span>
                        </span>
                        <span className="cart-line-meta">₹{line.price} × {line.qty} = ₹{line.price * line.qty}</span>
                        <span className="cart-line-actions">
                          <button type="button" className="btn btn-ghost btn-sm" onClick={() => updateCartQty(idx, -1)}>−</button>
                          <span className="cart-qty">{line.qty}</span>
                          <button type="button" className="btn btn-ghost btn-sm" onClick={() => updateCartQty(idx, 1)}>+</button>
                          <button type="button" className="btn btn-ghost btn-sm" onClick={() => removeFromCart(idx)}>Remove</button>
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="form-group">
                <label>Table</label>
                <select
                  value={form.table_no}
                  onChange={(e) => setForm((f) => ({ ...f, table_no: e.target.value }))}
                  required
                >
                  <option value="">Select table</option>
                  {tables.map((t) => (
                    <option key={t.table_id} value={String(t.table_no)}>
                      Table {t.table_no}
                    </option>
                  ))}
                </select>
                {tables.length === 0 && (
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: '0.25rem 0 0' }}>
                    No tables yet. Create tables in the Tables page first.
                  </p>
                )}
              </div>
              {modal !== 'create' && (
                <div className="form-group">
                  <label>Order status</label>
                  <select
                    value={statusForm.status}
                    onChange={(e) => setStatusForm({ status: e.target.value })}
                  >
                    <option value="pending">Pending</option>
                    <option value="preparing">Preparing</option>
                    <option value="ready">Ready</option>
                    <option value="cancelled">Cancelled</option>
                  </select>
                  <button type="button" className="btn btn-primary" style={{ marginTop: '0.5rem' }} onClick={() => updateStatus(modal)}>
                    Update status
                  </button>
                </div>
              )}
              <div className="form-actions">
                <button type="submit" className="btn btn-primary">Save</button>
                {modal !== 'create' && (
                  <button type="button" className="btn btn-danger" onClick={() => doDelete(modal)}>Delete</button>
                )}
                <button type="button" className="btn btn-ghost" onClick={() => setModal(null)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
