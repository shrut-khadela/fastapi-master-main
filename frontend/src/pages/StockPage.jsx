import { useState, useEffect } from 'react';
import { api } from '../api/client';
import './ManagePage.css';

export default function StockPage() {
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modal, setModal] = useState(null); // 'create' | stock id for edit
  const [form, setForm] = useState({
    name: '',
    quantity: 0,
    unit_of_measure: 'unit',
    cost_per_unit: 0,
  });

  const load = () => {
    setLoading(true);
    api.getStocks(1, 100)
      .then((data) => setList(Array.isArray(data) ? data : []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => load(), []);

  const openCreate = () => {
    setForm({ name: '', quantity: 0, unit_of_measure: 'unit', cost_per_unit: 0 });
    setModal('create');
    setError('');
  };

  const openEdit = (s) => {
    setForm({
      name: s.name || '',
      quantity: Number(s.quantity) || 0,
      unit_of_measure: s.unit_of_measure || 'unit',
      cost_per_unit: Number(s.cost_per_unit) || 0,
    });
    setModal(s.id);
    setError('');
  };

  const save = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const payload = {
        name: form.name,
        quantity: Number(form.quantity) || 0,
        unit_of_measure: form.unit_of_measure || 'unit',
        cost_per_unit: Number(form.cost_per_unit) || 0,
      };
      if (modal === 'create') {
        await api.createStock(payload);
      } else {
        await api.updateStock(modal, payload);
      }
      setModal(null);
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  const doDelete = async (id) => {
    if (!confirm('Delete this stock item?')) return;
    try {
      await api.deleteStock(id);
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
          <h1>Stock</h1>
          <p>Manage inventory and cost per unit.</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={openCreate}>
          Add stock
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <p className="empty-state">Loading…</p>
      ) : list.length === 0 ? (
        <div className="empty-state card">
          <p>No stock items yet.</p>
          <button type="button" className="btn btn-primary" onClick={openCreate}>
            Add stock
          </button>
        </div>
      ) : (
        <div className="table-wrap card">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Name</th>
                <th>Quantity</th>
                <th>Unit</th>
                <th>Cost/unit</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {list.map((s, idx) => (
                <tr key={s.id}>
                  <td>{idx + 1}</td>
                  <td>{s.name}</td>
                  <td>{s.quantity}</td>
                  <td>{s.unit_of_measure}</td>
                  <td>₹{Number(s.cost_per_unit)}</td>
                  <td>
                    <button type="button" className="btn btn-ghost" onClick={() => openEdit(s)}>Edit</button>
                    <button type="button" className="btn btn-danger" onClick={() => doDelete(s.id)}>Delete</button>
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
            <h2>{modal === 'create' ? 'New stock item' : 'Edit stock'}</h2>
            <form onSubmit={save}>
              {error && <div className="alert alert-error">{error}</div>}
              <div className="form-group">
                <label>Name</label>
                <input
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  required
                />
              </div>
              <div className="form-group">
                <label>Quantity</label>
                <input
                  type="number"
                  step="any"
                  value={form.quantity}
                  onChange={(e) => setForm((f) => ({ ...f, quantity: e.target.value }))}
                />
              </div>
              <div className="form-group">
                <label>Unit of measure</label>
                <input
                  value={form.unit_of_measure}
                  onChange={(e) => setForm((f) => ({ ...f, unit_of_measure: e.target.value }))}
                  placeholder="unit, kg, L, etc."
                />
              </div>
              <div className="form-group">
                <label>Cost per unit (₹)</label>
                <input
                  type="number"
                  step="any"
                  value={form.cost_per_unit}
                  onChange={(e) => setForm((f) => ({ ...f, cost_per_unit: e.target.value }))}
                />
              </div>
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
