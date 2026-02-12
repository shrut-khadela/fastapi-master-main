const API_BASE = import.meta.env.VITE_API_URL || '/api';

function getToken() {
  return localStorage.getItem('token');
}

export async function request(path, options = {}) {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(url, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = typeof data.detail === 'string' ? data.detail : data.detail?.message || data.message || res.statusText || 'Request failed';
    const err = new Error(msg);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

export const api = {
  // Auth
  login: (body) => request('/login', { method: 'POST', body: JSON.stringify(body) }),
  signup: (body) => request('/signup', { method: 'POST', body: JSON.stringify(body) }),
  me: () => request('/me'),

  // Restaurant
  createRestaurant: (body) => request('/create_restaurant', { method: 'POST', body: JSON.stringify(body) }),
  getRestaurants: (page = 1, per_page = 50) => request(`/get_restaurants?page=${page}&per_page=${per_page}`),
  uploadRestaurantLogo: async (file) => {
    const url = (import.meta.env.VITE_API_URL || '/api') + '/upload_restaurant_logo';
    const token = localStorage.getItem('token');
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(url, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = typeof data.detail === 'string' ? data.detail : data.detail?.message || data.message || res.statusText || 'Upload failed';
      throw new Error(msg);
    }
    return data;
  },

  // Tables
  getTables: (page = 1, per_page = 50) => request(`/get_tables?page=${page}&per_page=${per_page}`),
  createTable: (body) => request('/create_table', { method: 'POST', body: JSON.stringify(body) }),
  getTable: (id) => request(`/tables_by_id/${id}`),
  updateTable: (id, body) => request(`/update_table/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  deleteTable: (id) => request(`/delete_table_by_id/${id}`, { method: 'DELETE' }),

  // Categories
  createCategory: (body) => request('/create_category', { method: 'POST', body: JSON.stringify(body) }),

  // Menu
  getMenus: (page = 1, per_page = 50) => request(`/get_menus?page=${page}&per_page=${per_page}`),
  getMenu: (id) => request(`/get_menu_by_id/${id}`),
  createMenu: (body) => request('/create_menu', { method: 'POST', body: JSON.stringify(body) }),
  updateMenu: (id, body) => request(`/update_menu/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  deleteMenu: (id) => request(`/delete_menu_by_id/${id}`, { method: 'DELETE' }),

  // Orders
  getOrders: (page = 1, per_page = 50) => request(`/get_orders?page=${page}&per_page=${per_page}`),
  getOrder: (id) => request(`/get_order_by_id/${id}`),
  createOrder: (body) => request('/create_order', { method: 'POST', body: JSON.stringify(body) }),
  updateOrder: (id, body) => request(`/update_order/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  deleteOrder: (id) => request(`/delete_order_by_id/${id}`, { method: 'DELETE' }),
  updateOrderStatus: (id, body) => request(`/update_order_status/${id}`, { method: 'PUT', body: JSON.stringify(body) }),

  // Stock
  getStocks: (page = 1, per_page = 50) => request(`/get_stocks?page=${page}&per_page=${per_page}`),
  getStock: (id) => request(`/get_stock_by_id/${id}`),
  createStock: (body) => request('/create_stock', { method: 'POST', body: JSON.stringify(body) }),
  updateStock: (id, body) => request(`/update_stock/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  deleteStock: (id) => request(`/delete_stock_by_id/${id}`, { method: 'DELETE' }),

  // Invoices
  getInvoices: (page = 1, per_page = 50) => request(`/get_invoices?page=${page}&per_page=${per_page}`),
  getInvoice: (id) => request(`/get_invoice_by_id/${id}`),
  getTablesWithUninvoicedOrders: () => request('/tables_with_uninvoiced_orders'),
  createInvoice: (body) => request('/create_invoice', { method: 'POST', body: JSON.stringify(body) }),
  createInvoiceForTable: (body) => request('/create_invoice_for_table', { method: 'POST', body: JSON.stringify(body) }),
  updateInvoice: (id, body) => request(`/update_invoice/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  deleteInvoice: (id) => request(`/delete_invoice_by_id/${id}`, { method: 'DELETE' }),

  // Payments
  createPayment: (body) => request('/create_payment', { method: 'POST', body: JSON.stringify(body) }),
  getPayment: (id) => request(`/${id}`),
  markPaymentPaid: (id, body = {}) => request(`/${id}/mark_paid`, { method: 'POST', body: JSON.stringify(body) }),
};
