import { useState, useEffect } from 'react';
import { api } from '../api/client';
import './ManagePage.css';

const apiOrigin = import.meta.env.VITE_API_URL ? new URL(import.meta.env.VITE_API_URL).origin : (typeof window !== 'undefined' ? window.location.origin : '');

export default function RestaurantPage() {
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loadingLogo, setLoadingLogo] = useState(false);
  const [form, setForm] = useState({
    upi_merchant_name: '',
    upi_id: '',
    restaurant_address: '',
    restaurant_phone: '',
    restaurant_email: '',
    logo_url: '',
  });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await api.getRestaurants(1, 1);
        if (!cancelled && list?.length) {
          const r = list[0];
          setForm((f) => ({
            ...f,
            upi_merchant_name: r.upi_merchant_name || '',
            upi_id: r.upi_id || '',
            restaurant_address: r.restaurant_address || '',
            restaurant_phone: r.restaurant_phone || '',
            restaurant_email: r.restaurant_email || '',
            logo_url: r.logo_url || '',
          }));
        }
      } catch {
        // ignore
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const handleLogoFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setError('Please select an image (PNG, JPEG, WebP or GIF).');
      return;
    }
    setError('');
    setLoadingLogo(true);
    try {
      const { logo_url } = await api.uploadRestaurantLogo(file);
      setForm((f) => ({ ...f, logo_url }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingLogo(false);
      e.target.value = '';
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      await api.createRestaurant({
        upi_merchant_name: form.upi_merchant_name,
        upi_id: form.upi_id,
        restaurant_address: form.restaurant_address || null,
        restaurant_phone: form.restaurant_phone || null,
        restaurant_email: form.restaurant_email || null,
        logo_url: form.logo_url || null,
      });
      setSuccess('Restaurant details saved. Use the same UPI merchant name when creating payments.');
    } catch (err) {
      setError(err.message);
    }
  };

  const logoPreviewUrl = form.logo_url
    ? (form.logo_url.startsWith('http') ? form.logo_url : `${apiOrigin}${form.logo_url.startsWith('/') ? '' : '/'}${form.logo_url}`)
    : null;

  return (
    <div className="manage-page">
      <div className="page-header">
        <h1>Restaurant</h1>
        <p>Set your UPI and contact details for payments.</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="card" style={{ maxWidth: 520 }}>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>UPI merchant name</label>
            <input
              value={form.upi_merchant_name}
              onChange={(e) => setForm((f) => ({ ...f, upi_merchant_name: e.target.value }))}
              placeholder="Your restaurant name (for UPI)"
              required
            />
          </div>
          <div className="form-group">
            <label>UPI ID</label>
            <input
              value={form.upi_id}
              onChange={(e) => setForm((f) => ({ ...f, upi_id: e.target.value }))}
              placeholder="9876543210@ybl or name@paytm"
              required
            />
          </div>
          <div className="form-group">
            <label>Restaurant logo (optional)</label>
            <p className="form-hint">Upload a logo to show on invoices. PNG, JPEG, WebP or GIF.</p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <label className="btn btn-secondary" style={{ marginBottom: 0, cursor: 'pointer' }}>
                <input type="file" accept="image/*" onChange={handleLogoFile} disabled={loadingLogo} style={{ display: 'none' }} />
                {loadingLogo ? 'Uploading…' : 'Upload logo'}
              </label>
              {logoPreviewUrl && (
                <>
                  <img src={logoPreviewUrl} alt="Logo preview" style={{ height: 48, width: 'auto', maxWidth: 120, objectFit: 'contain' }} />
                  <button type="button" className="btn btn-secondary" onClick={() => setForm((f) => ({ ...f, logo_url: '' }))}>Remove</button>
                </>
              )}
            </div>
            <input
              value={form.logo_url}
              onChange={(e) => setForm((f) => ({ ...f, logo_url: e.target.value }))}
              placeholder="Or paste logo URL"
              style={{ marginTop: 8 }}
            />
          </div>
          <div className="form-group">
            <label>Address</label>
            <input
              value={form.restaurant_address}
              onChange={(e) => setForm((f) => ({ ...f, restaurant_address: e.target.value }))}
              placeholder="Restaurant address"
            />
          </div>
          <div className="form-group">
            <label>Phone</label>
            <input
              value={form.restaurant_phone}
              onChange={(e) => setForm((f) => ({ ...f, restaurant_phone: e.target.value }))}
              placeholder="Contact number"
            />
          </div>
          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              value={form.restaurant_email}
              onChange={(e) => setForm((f) => ({ ...f, restaurant_email: e.target.value }))}
              placeholder="restaurant@example.com"
            />
          </div>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary">Save restaurant</button>
          </div>
        </form>
      </div>
    </div>
  );
}
