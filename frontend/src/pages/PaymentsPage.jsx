import { useState, useEffect } from 'react';
import { api } from '../api/client';
import './ManagePage.css';

export default function PaymentsPage() {
  const [orders, setOrders] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [createModal, setCreateModal] = useState(false);
  const [form, setForm] = useState({
    restaurant_name: '',
    invoice_id: '',
    order_id: '',
    amount: 0,
  });
  const [payments, setPayments] = useState([]);
  const [existingPayment, setExistingPayment] = useState(null);
  const [createdPayment, setCreatedPayment] = useState(null);

  const load = () => {
    setLoading(true);
    Promise.all([
      api.getOrders(1, 100),
      api.getInvoices(1, 100),
    ])
      .then(([ordersData, invoicesData]) => {
        setOrders(Array.isArray(ordersData) ? ordersData : []);
        setInvoices(Array.isArray(invoicesData) ? invoicesData : []);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => load(), []);

  const openCreate = () => {
    const firstInv = invoices[0];
    setForm({
      restaurant_name: '',
      invoice_id: firstInv?.invoice_id || '',
      order_id: orders[0]?.order_id || '',
      amount: firstInv ? Number(firstInv.total_amount) || 0 : 0,
    });
    setCreateModal(true);
    setError('');
    setSuccess('');
    setExistingPayment(null);
    setCreatedPayment(null);
  };

  const selectedInvoice = form.invoice_id ? invoices.find((inv) => inv.invoice_id === form.invoice_id) : null;

  const createPayment = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      const payload = {
        restaurant_name: form.restaurant_name,
      };
      if (form.invoice_id) {
        payload.invoice_id = form.invoice_id;
      } else {
        payload.order_id = form.order_id;
        payload.amount = Number(form.amount) || 0;
      }
      const res = await api.createPayment(payload);
      setCreatedPayment(res);
      setSuccess('Payment created.');
      setPayments((p) => [...p, res]);
      setCreateModal(false);
    } catch (err) {
      if (err.status === 409 && err.data?.detail) {
        const detail = err.data.detail;
        setCreateModal(false);
        setError('A payment already exists for this order. Showing it below.');
        if (detail.payment) {
          setExistingPayment(detail.payment);
        } else if (detail.payment_id) {
          api.getPayment(detail.payment_id)
            .then((payment) => setExistingPayment(payment))
            .catch((e) => setError(e.message));
        }
      } else {
        setError(err.message);
      }
    }
  };

  return (
    <div className="manage-page">
      <div className="page-header flex">
        <div>
          <h1>Payments</h1>
          <p>Create UPI payment links and QR codes for orders.</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={openCreate}>
          Create payment
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {createdPayment && (
        <div className="card" style={{ marginBottom: '1rem' }}>
          <h3 style={{ marginTop: 0 }}>Payment created – scan to pay</h3>
          <p style={{ color: 'var(--text-muted)', margin: '0 0 1rem' }}>
            Amount: &#8377;{Number(createdPayment.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })} &middot; Status: <span className={`badge badge-${(createdPayment.payment_status || '').toLowerCase()}`}>{createdPayment.payment_status || 'pending'}</span>
          </p>
          {createdPayment.qr_image_url ? (
            <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
              <img src={createdPayment.qr_image_url} alt="UPI QR code" width={256} height={256} style={{ display: 'block', margin: '0 auto', maxWidth: '100%', borderRadius: 8 }} />
              <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', margin: '0.5rem 0 0' }}>Scan with any UPI app to pay</p>
            </div>
          ) : (
            <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>QR not available. <a href={`${(import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '')}/pay/${createdPayment.payment_id}`} target="_blank" rel="noopener noreferrer">Open payment page</a></p>
          )}
          <p style={{ margin: 0, fontSize: '0.9rem' }}>
            <a href={`${(import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '')}/pay/${createdPayment.payment_id}`} target="_blank" rel="noopener noreferrer">Open full payment page</a>
          </p>
          <button type="button" className="btn btn-ghost" style={{ marginTop: '0.75rem' }} onClick={() => { setCreatedPayment(null); setSuccess(''); }}>Dismiss</button>
        </div>
      )}

      {existingPayment && (
        <div className="card" style={{ marginBottom: '1rem' }}>
          <h3 style={{ marginTop: 0 }}>Existing payment for this order</h3>
          <p style={{ color: 'var(--text-muted)', margin: '0 0 1rem' }}>
            Amount: &#8377;{Number(existingPayment.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })} &middot; Status: <span className={`badge badge-${(existingPayment.payment_status || '').toLowerCase()}`}>{existingPayment.payment_status || 'pending'}</span>
          </p>
          {existingPayment.qr_image_url && (
            <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
              <img src={existingPayment.qr_image_url} alt="UPI QR code" width={256} height={256} style={{ display: 'block', margin: '0 auto', maxWidth: '100%', borderRadius: 8 }} />
              <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', margin: '0.5rem 0 0' }}>Scan with any UPI app to pay</p>
            </div>
          )}
          <p style={{ margin: 0, fontSize: '0.9rem' }}>
            <a href={`${(import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '')}/pay/${existingPayment.payment_id}`} target="_blank" rel="noopener noreferrer">Open full payment page</a>
          </p>
          <button type="button" className="btn btn-ghost" style={{ marginTop: '0.75rem' }} onClick={() => { setExistingPayment(null); setError(''); }}>Dismiss</button>
        </div>
      )}

      <div className="card">
        <p style={{ color: 'var(--text-muted)', margin: 0 }}>
          Create a payment for an order to get a UPI QR code. Use the &quot;Open full payment page&quot; link below to show the QR to customers.
          You need to set <strong>Restaurant</strong> (UPI merchant name) in the Restaurant page first, and pass the same name here.
        </p>
      </div>

      {createModal && (
        <div className="modal-overlay" onClick={() => setCreateModal(false)}>
          <div className="modal card" onClick={(e) => e.stopPropagation()}>
            <h2>Create payment</h2>
            <form onSubmit={createPayment}>
              {error && <div className="alert alert-error">{error}</div>}
              <div className="form-group">
                <label>Restaurant name (UPI merchant name)</label>
                <input
                  value={form.restaurant_name}
                  onChange={(e) => setForm((f) => ({ ...f, restaurant_name: e.target.value }))}
                  placeholder="Same as in Restaurant settings"
                  required
                />
              </div>
              <div className="form-group">
                <label>Invoice (create payment for existing invoice)</label>
                <select
                  value={form.invoice_id}
                  onChange={(e) => {
                    const inv = invoices.find((i) => i.invoice_id === e.target.value);
                    setForm((f) => ({
                      ...f,
                      invoice_id: e.target.value,
                      amount: inv ? Number(inv.total_amount) || 0 : f.amount,
                    }));
                  }}
                >
                  <option value="">Select invoice (amount will be from invoice)</option>
                  {invoices.map((inv) => (
                    <option key={inv.invoice_id} value={inv.invoice_id}>
                      {inv.invoice_number} — ₹{Number(inv.total_amount).toFixed(2)} · {inv.payment_status || 'pending'}
                    </option>
                  ))}
                </select>
                {invoices.length === 0 && (
                  <p className="form-hint">No invoices yet. Create an invoice from the Invoices page first.</p>
                )}
              </div>
              {!form.invoice_id && (
                <>
                  <div className="form-group">
                    <label>Order (if not using an invoice)</label>
                    <select
                      value={form.order_id}
                      onChange={(e) => setForm((f) => ({ ...f, order_id: e.target.value }))}
                    >
                      <option value="">Select order</option>
                      {orders.map((o, idx) => (
                        <option key={o.order_id} value={o.order_id}>Order #{idx + 1} · Table {o.table_id}</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Amount (₹)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={form.amount}
                      onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                    />
                  </div>
                </>
              )}
              {form.invoice_id && selectedInvoice && (
                <p className="form-hint" style={{ marginTop: 0 }}>
                  Amount for this payment: ₹{Number(selectedInvoice.total_amount).toFixed(2)} (from invoice total).
                </p>
              )}
              <div className="form-actions">
                <button type="submit" className="btn btn-primary">Create & get QR</button>
                <button type="button" className="btn btn-ghost" onClick={() => setCreateModal(false)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
