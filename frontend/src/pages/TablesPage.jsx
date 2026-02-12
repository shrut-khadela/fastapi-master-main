import { useState, useEffect } from 'react';
import { api } from '../api/client';
import './ManagePage.css';

export default function TablesPage() {
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modal, setModal] = useState(null); // 'create' | table_id for edit
  const [tableNo, setTableNo] = useState('');

  const load = () => {
    setLoading(true);
    api.getTables(1, 100)
      .then((data) => setList(Array.isArray(data) ? data : []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => load(), []);

  const openCreate = () => {
    setTableNo('');
    setModal('create');
    setError('');
  };

  const openEdit = (t) => {
    setTableNo(String(t.table_no));
    setModal(t.table_id);
    setError('');
  };

  const save = async (e) => {
    e.preventDefault();
    const no = parseInt(tableNo, 10);
    if (isNaN(no)) {
      setError('Table number must be a number');
      return;
    }
    setError('');
    try {
      if (modal === 'create') {
        await api.createTable({ table_no: no });
      } else {
        await api.updateTable(modal, { table_no: no });
      }
      setModal(null);
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  const doDelete = async (id) => {
    if (!confirm('Delete this table?')) return;
    try {
      await api.deleteTable(id);
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
          <h1>Tables</h1>
          <p>Manage table numbers for orders.</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={openCreate}>
          Add table
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <p className="empty-state">Loading…</p>
      ) : list.length === 0 ? (
        <div className="empty-state card">
          <p>No tables yet.</p>
          <button type="button" className="btn btn-primary" onClick={openCreate}>
            Add table
          </button>
        </div>
      ) : (
        <div className="table-wrap card">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Table no.</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {list.map((t, idx) => (
                <tr key={t.table_id}>
                  <td>{idx + 1}</td>
                  <td>{t.table_no}</td>
                  <td>
                    <button type="button" className="btn btn-ghost" onClick={() => openEdit(t)}>Edit</button>
                    <button type="button" className="btn btn-danger" onClick={() => doDelete(t.table_id)}>Delete</button>
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
            <h2>{modal === 'create' ? 'New table' : 'Edit table'}</h2>
            <form onSubmit={save}>
              {error && <div className="alert alert-error">{error}</div>}
              <div className="form-group">
                <label>Table number</label>
                <input
                  type="number"
                  value={tableNo}
                  onChange={(e) => setTableNo(e.target.value)}
                  required
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
