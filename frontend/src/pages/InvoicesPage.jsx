import { useState, useEffect } from 'react';
import { api } from '../api/client';
import './ManagePage.css';

export default function InvoicesPage() {
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState({
    order_id: '',
    invoice_number: '',
    invoice_date: new Date().toISOString().slice(0, 10),
    total_amount: 0,
    gst_percent: 0,
    discount_percent: 0,
    payment_status: 'pending',
    notes: '',
    customer_name: '',
  });
  const [orders, setOrders] = useState([]);
  const [tableModal, setTableModal] = useState(false);
  const [tablesWithOrders, setTablesWithOrders] = useState([]);
  const [loadingTables, setLoadingTables] = useState(false);
  const [tableForm, setTableForm] = useState({
    table_no: '',
    invoice_number: '',
    invoice_date: new Date().toISOString().slice(0, 10),
    gst_percent: 0,
    discount_percent: 0,
    payment_status: 'pending',
    notes: '',
    customer_name: '',
  });

  const load = () => {
    setLoading(true);
    Promise.all([
      api.getInvoices(1, 100),
      api.getOrders(1, 100),
    ])
      .then(([invs, ords]) => {
        setList(Array.isArray(invs) ? invs : []);
        setOrders(Array.isArray(ords) ? ords : []);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => load(), []);

  const openCreate = () => {
    setForm({
      order_id: orders[0]?.order_id || '',
      invoice_number: `INV-${Date.now()}`,
      invoice_date: new Date().toISOString().slice(0, 10),
      total_amount: 0,
      gst_percent: 0,
      discount_percent: 0,
      payment_status: 'pending',
      notes: '',
      customer_name: '',
    });
    setModal('create');
    setTableModal(false);
    setError('');
  };

  const openCreateByTable = () => {
    setTableModal(true);
    setModal(null);
    setError('');
    setLoadingTables(true);
    api
      .getTablesWithUninvoicedOrders()
      .then((tableNos) => {
        const list = Array.isArray(tableNos) ? tableNos.map((t) => String(t)) : [];
        setTablesWithOrders(list);
        setTableForm((f) => ({
          ...f,
          table_no: list[0] || '',
          invoice_number: '',
          invoice_date: new Date().toISOString().slice(0, 10),
          gst_percent: 0,
          discount_percent: 0,
          payment_status: 'pending',
          notes: '',
          customer_name: '',
        }));
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoadingTables(false));
  };

  const saveByTable = async (e) => {
    e.preventDefault();
    setError('');
    const tableNo = Number(tableForm.table_no);
    if (!Number.isInteger(tableNo) || tableNo < 0) {
      setError('Please enter a valid table number.');
      return;
    }
    try {
      await api.createInvoiceForTable({
        table_no: tableNo,
        invoice_number: tableForm.invoice_number || undefined,
        invoice_date: tableForm.invoice_date || undefined,
        gst_percent: Number(tableForm.gst_percent) || 0,
        discount_percent: Number(tableForm.discount_percent) || 0,
        payment_status: tableForm.payment_status,
        notes: tableForm.notes || null,
        customer_name: (tableForm.customer_name || '').trim() || null,
      });
      setTableModal(false);
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  const save = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const payload = {
        order_id: form.order_id,
        invoice_number: form.invoice_number,
        invoice_date: form.invoice_date,
        gst_percent: Number(form.gst_percent) || 0,
        discount_percent: Number(form.discount_percent) || 0,
        payment_status: form.payment_status,
        notes: form.notes || null,
        customer_name: (form.customer_name || '').trim() || null,
      };
      if (modal === 'create') {
        await api.createInvoice(payload);
      } else {
        payload.total_amount = Number(form.total_amount) || 0;
        await api.updateInvoice(modal, payload);
      }
      setModal(null);
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  const doDelete = async (id) => {
    if (!confirm('Delete this invoice?')) return;
    try {
      await api.deleteInvoice(id);
      setModal(null);
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  const paymentBadge = (s) => {
    const v = (s || '').toLowerCase();
    if (v === 'paid') return 'badge-paid';
    if (v === 'cancelled') return 'badge-cancelled';
    return 'badge-pending';
  };

  return (
    <div className="manage-page">
      <div className="page-header flex">
        <div>
          <h1>Invoices</h1>
          <p>Create and manage invoices for orders.</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button type="button" className="btn btn-primary" onClick={openCreateByTable}>
            Create Invoice
          </button>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <p className="empty-state">Loading…</p>
      ) : list.length === 0 ? (
        <div className="empty-state card">
          <p>No invoices yet.</p>
          <button type="button" className="btn btn-primary" onClick={openCreateByTable}>
            Create Invoice
          </button>
        </div>
      ) : (
        <div className="table-wrap card">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Invoice #</th>
                <th>Date</th>
                <th>Amount</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {list.map((i, idx) => (
                <tr key={i.invoice_id}>
                  <td>{idx + 1}</td>
                  <td>{i.invoice_number}</td>
                  <td>{typeof i.invoice_date === 'string' ? i.invoice_date.slice(0, 10) : i.invoice_date}</td>
                  <td>₹{Number(i.total_amount)}</td>
                  <td><span className={`badge ${paymentBadge(i.payment_status)}`}>{i.payment_status}</span></td>
                  <td>
                    <a href={`${(import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '')}/invoice/${i.invoice_id || i.id}/view`} target="_blank" rel="noopener noreferrer" className="btn btn-ghost" style={{ textDecoration: 'none' }}>View / Print</a>
                    <button type="button" className="btn btn-ghost" onClick={() => { setForm({ order_id: i.order_id, invoice_number: i.invoice_number, invoice_date: (i.invoice_date && typeof i.invoice_date === 'string' ? i.invoice_date.slice(0, 10) : i.invoice_date ? new Date(i.invoice_date).toISOString().slice(0, 10) : form.invoice_date), total_amount: Number(i.total_amount), gst_percent: Number(i.gst_percent) || 0, discount_percent: Number(i.discount_percent) || 0, payment_status: i.payment_status || 'pending', notes: i.notes || '', customer_name: i.customer_name || '' }); setModal(i.invoice_id); }}>Edit</button>
                    <button type="button" className="btn btn-danger" onClick={() => doDelete(i.invoice_id)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tableModal && (
        <div className="modal-overlay" onClick={() => setTableModal(false)}>
          <div className="modal card" onClick={(e) => e.stopPropagation()}>
            <h2>Create Invoice(merge all orders)</h2>
            <p className="form-hint">All uninvoiced orders for the selected table will be merged into one invoice. Total is auto-calculated from order items + GST − discount. You can enter a customer name to show in &quot;INVOICE TO&quot; (otherwise the table number is shown).</p>
            <form onSubmit={saveByTable}>
              {error && <div className="alert alert-error">{error}</div>}
              <div className="form-group">
                <label>Table number</label>
                <select
                  value={tableForm.table_no}
                  onChange={(e) => setTableForm((f) => ({ ...f, table_no: e.target.value }))}
                  required
                  disabled={loadingTables}
                >
                  <option value="">
                    {loadingTables ? 'Loading tables…' : tablesWithOrders.length === 0 ? 'No tables with uninvoiced orders' : 'Select table'}
                  </option>
                  {tablesWithOrders.map((t) => (
                    <option key={t} value={t}>Table {t}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Customer name (optional – shown in &quot;INVOICE TO&quot; on the invoice)</label>
                <input
                  type="text"
                  value={tableForm.customer_name || ''}
                  onChange={(e) => setTableForm((f) => ({ ...f, customer_name: e.target.value }))}
                  placeholder="e.g. John Smith – leave empty to show table number"
                />
              </div>
              <div className="form-group">
                <label>Invoice number (optional, auto-generated if empty)</label>
                <input
                  value={tableForm.invoice_number}
                  onChange={(e) => setTableForm((f) => ({ ...f, invoice_number: e.target.value }))}
                  placeholder="e.g. INV-123"
                />
              </div>
              <div className="form-group">
                <label>Date</label>
                <input
                  type="date"
                  value={tableForm.invoice_date}
                  onChange={(e) => setTableForm((f) => ({ ...f, invoice_date: e.target.value }))}
                />
              </div>
              <div className="form-group">
                <label>GST (%)</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                  value={tableForm.gst_percent}
                  onChange={(e) => setTableForm((f) => ({ ...f, gst_percent: e.target.value }))}
                />
              </div>
              <div className="form-group">
                <label>Discount (%)</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                  value={tableForm.discount_percent}
                  onChange={(e) => setTableForm((f) => ({ ...f, discount_percent: e.target.value }))}
                />
              </div>
              <div className="form-group">
                <label>Payment status</label>
                <select
                  value={tableForm.payment_status}
                  onChange={(e) => setTableForm((f) => ({ ...f, payment_status: e.target.value }))}
                >
                  <option value="pending">Pending</option>
                  <option value="paid">Paid</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>
              <div className="form-group">
                <label>Notes</label>
                <textarea
                  value={tableForm.notes || ''}
                  onChange={(e) => setTableForm((f) => ({ ...f, notes: e.target.value }))}
                  rows={2}
                />
              </div>
              <div className="form-actions">
                <button type="submit" className="btn btn-primary">Create merged invoice</button>
                <button type="button" className="btn btn-ghost" onClick={() => setTableModal(false)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {modal && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal card" onClick={(e) => e.stopPropagation()}>
            <h2>{modal === 'create' ? 'New invoice' : 'Edit invoice'}</h2>
            <form onSubmit={save}>
              {error && <div className="alert alert-error">{error}</div>}
              <div className="form-group">
                <label>Customer name (optional – shown in &quot;INVOICE TO&quot;)</label>
                <input
                  type="text"
                  value={form.customer_name || ''}
                  onChange={(e) => setForm((f) => ({ ...f, customer_name: e.target.value }))}
                  placeholder="e.g. John Smith – leave empty to show table number"
                />
              </div>
              <div className="form-group">
                <label>Order</label>
                <select
                  value={form.order_id}
                  onChange={(e) => setForm((f) => ({ ...f, order_id: e.target.value }))}
                  required
                >
                  <option value="">Select order</option>
                  {orders.map((o, idx) => (
                    <option key={o.order_id} value={o.order_id}>Order #{idx + 1} · Table {o.table_id}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Invoice number</label>
                <input
                  value={form.invoice_number}
                  onChange={(e) => setForm((f) => ({ ...f, invoice_number: e.target.value }))}
                  required
                />
              </div>
              <div className="form-group">
                <label>Date</label>
                <input
                  type="date"
                  value={form.invoice_date}
                  onChange={(e) => setForm((f) => ({ ...f, invoice_date: e.target.value }))}
                />
              </div>
              {modal === 'create' && (
                <p className="form-hint" style={{ marginTop: 0 }}>Total is auto-calculated from order items + GST − discount.</p>
              )}
              <div className="form-group">
                <label>GST (%)</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                  value={form.gst_percent}
                  onChange={(e) => setForm((f) => ({ ...f, gst_percent: e.target.value }))}
                />
              </div>
              <div className="form-group">
                <label>Discount (%)</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                  value={form.discount_percent}
                  onChange={(e) => setForm((f) => ({ ...f, discount_percent: e.target.value }))}
                />
              </div>
              {modal !== 'create' && (
                <div className="form-group">
                  <label>Total amount (₹)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={form.total_amount}
                    onChange={(e) => setForm((f) => ({ ...f, total_amount: e.target.value }))}
                  />
                </div>
              )}
              <div className="form-group">
                <label>Payment status</label>
                <select
                  value={form.payment_status}
                  onChange={(e) => setForm((f) => ({ ...f, payment_status: e.target.value }))}
                >
                  <option value="pending">Pending</option>
                  <option value="paid">Paid</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>
              <div className="form-group">
                <label>Notes</label>
                <textarea
                  value={form.notes || ''}
                  onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                  rows={2}
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
