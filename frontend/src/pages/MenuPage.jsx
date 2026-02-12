import { useState, useEffect } from 'react';
import { api } from '../api/client';
import './ManagePage.css';

export default function MenuPage() {
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modal, setModal] = useState(null); // 'create' | { menu_id } for edit
  const [form, setForm] = useState({
    item_list: [],
    price: 0,
    quantity: '',
    category_name: [],
  });

  const load = () => {
    setLoading(true);
    api.getMenus(1, 100)
      .then((data) => setList(Array.isArray(data) ? data : []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => load(), []);

  const openCreate = () => {
    setForm({
      item_list: [{ item_name: '', price: 0, category_id: '', category_name: '' }],
      price: 0,
      quantity: '',
      category_name: [{ category_id: '', category_name: '' }],
    });
    setModal('create');
    setError('');
  };

  const openEdit = (m) => {
    const itemList = Array.isArray(m.item_list) ? m.item_list : [];
    const catName = Array.isArray(m.category_name) ? m.category_name : [];
    setForm({
      menu_id: m.menu_id,
      item_list: itemList.length ? itemList : [{ item_name: '', price: 0, category_id: '', category_name: '' }],
      price: Number(m.price) || 0,
      quantity: m.quantity || '',
      category_name: catName.length ? catName : [{ category_id: '', category_name: '' }],
    });
    setModal(m.menu_id);
    setError('');
  };

  const addItem = () => {
    setForm((f) => ({
      ...f,
      item_list: [...f.item_list, { item_name: '', price: 0, category_id: '', category_name: '' }],
    }));
  };

  const updateItem = (index, field, value) => {
    setForm((f) => {
      const next = [...f.item_list];
      next[index] = { ...next[index], [field]: value };
      return { ...f, item_list: next };
    });
  };

  const removeItem = (index) => {
    setForm((f) => ({
      ...f,
      item_list: f.item_list.filter((_, i) => i !== index),
    }));
  };

  const save = async (e) => {
    e.preventDefault();
    setError('');
    const payload = {
      item_list: form.item_list.filter((i) => i.item_name),
      price: Number(form.price) || 0,
      quantity: String(form.quantity || ''),
      category_name: form.category_name.filter((c) => c.category_name),
    };
    try {
      if (modal === 'create') {
        await api.createMenu(payload);
      } else {
        await api.updateMenu(form.menu_id, payload);
      }
      setModal(null);
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  const doDelete = async (menuId) => {
    if (!confirm('Delete this menu?')) return;
    try {
      await api.deleteMenu(menuId);
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
          <h1>Menu</h1>
          <p>Manage menu items and categories.</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={openCreate}>
          Add menu
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <p className="empty-state">Loading…</p>
      ) : list.length === 0 ? (
        <div className="empty-state card">
          <p>No menus yet.</p>
          <button type="button" className="btn btn-primary" onClick={openCreate}>
            Add menu
          </button>
        </div>
      ) : (
        <div className="table-wrap card">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Items</th>
                <th>Price</th>
                <th>Quantity</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {list.map((m, idx) => (
                <tr key={m.menu_id}>
                  <td>{idx + 1}</td>
                  <td>
                    {Array.isArray(m.item_list) && m.item_list.length
                      ? m.item_list.map((i) => i.item_name || i.name).filter(Boolean).join(', ') || '—'
                      : '—'}
                  </td>
                  <td>₹{Number(m.price)}</td>
                  <td>{m.quantity || '—'}</td>
                  <td>
                    <button type="button" className="btn btn-ghost" onClick={() => openEdit(m)}>Edit</button>
                    <button type="button" className="btn btn-danger" onClick={() => doDelete(m.menu_id)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modal && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal card" onClick={(e) => e.stopPropagation()}>
            <h2>{modal === 'create' ? 'New menu' : 'Edit menu'}</h2>
            <form onSubmit={save}>
              {error && <div className="alert alert-error">{error}</div>}
              <div className="form-group">
                <label>Items</label>
                {form.item_list.map((item, i) => (
                  <div key={i} className="form-row align-center" style={{ marginBottom: '0.5rem' }}>
                    <input
                      placeholder="Item name"
                      value={item.item_name || ''}
                      onChange={(e) => updateItem(i, 'item_name', e.target.value)}
                    />
                    <input
                      type="number"
                      placeholder="Price"
                      value={item.price ?? ''}
                      onChange={(e) => updateItem(i, 'price', Number(e.target.value))}
                      style={{ maxWidth: '100px' }}
                    />
                    <button type="button" className="btn btn-danger" onClick={() => removeItem(i)}>Remove</button>
                  </div>
                ))}
                <button type="button" className="btn btn-ghost" onClick={addItem}>+ Add item</button>
              </div>
              <div className="form-group">
                <label>Price (default)</label>
                <input
                  type="number"
                  value={form.price}
                  onChange={(e) => setForm((f) => ({ ...f, price: Number(e.target.value) }))}
                />
              </div>
              <div className="form-group">
                <label>Quantity (e.g. 300ml)</label>
                <input
                  value={form.quantity}
                  onChange={(e) => setForm((f) => ({ ...f, quantity: e.target.value }))}
                  placeholder="300 or 300ml"
                />
              </div>
              <div className="form-actions">
                <button type="submit" className="btn btn-primary">Save</button>
                {modal !== 'create' && (
                  <button type="button" className="btn btn-danger" onClick={() => doDelete(form.menu_id)}>
                    Delete
                  </button>
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
