# Spice & Stories — Frontend

React frontend for the restaurant management API.

## Setup

1. From the **project root** (the folder that contains `frontend` and `src`), install dependencies:

   ```bash
   cd frontend && npm install
   ```

   If your project path has spaces, use quotes:

   ```bash
   cd "/Users/shrutkhadela/Kryoverse/resturant management/frontend"
   npm install
   ```

2. **Start the backend first** (in a separate terminal, from project root). If the backend isn’t running, you’ll see `ECONNREFUSED` proxy errors when logging in:

   ```bash
   cd "/Users/shrutkhadela/Kryoverse/resturant management"
   source venv/bin/activate   # or: python -m venv venv && source venv/bin/activate
   uvicorn src.main:create_app --host 0.0.0.0 --port 8000 --reload --factory
   ```

   Ensure PostgreSQL is running and `.env` is set (see project root `Readme.md`).

3. Start the frontend dev server (uses Vite proxy to the backend):

   ```bash
   npm run dev
   ```

   Open [http://localhost:3000](http://localhost:3000). The app proxies `/api` to your backend.

## Environment

- `VITE_API_URL`: API base URL. Defaults to `/api` (proxied to the backend in dev). For production, set to your backend URL (e.g. `https://api.example.com`).

## Build

```bash
npm run build
```

Output is in `dist/`. Serve it with any static host. Set `VITE_API_URL` when building if the API is on a different origin.

## Features

- **Auth**: Login, Signup, JWT stored in `localStorage`
- **Dashboard**: Quick stats and links
- **Menu**: List, create, edit, delete menus (item list, price, quantity, categories)
- **Tables**: CRUD for table numbers
- **Orders**: Create/edit orders, update order status (pending → preparing → ready / cancelled)
- **Stock**: CRUD for inventory (name, quantity, unit, cost per unit)
- **Invoices**: Create/edit invoices linked to orders
- **Payments**: Create payment for an order (UPI); backend provides QR at `/pay/{payment_id}`
- **Restaurant**: Set UPI merchant name and UPI ID for payments
