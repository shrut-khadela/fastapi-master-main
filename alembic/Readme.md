# Database
    Alembic Commands
    alembic revision --autogenerate -m "v0.0 initial commit"
    alembic upgrade head

Please do not delete any Version from alembic\versions or Table from DB.

# Naming convention to follow while making the new commit for DB.
    alembic revision --autogenerate -m "{VERSION FORMAT}"

### VERSION FORMAT
    v{major version}.{minor version} {relevant sort-comment}

### If "relation stock does not exist" or "Can't locate revision identified by '...'"
1. **Create stock table only (quick fix):**  
   Run the standalone SQL:  
   `psql $DATABASE_URL -f alembic/versions/create_stock_table_standalone.sql`  
   (Or run the statements in `alembic/versions/create_stock_table_standalone.sql` in your DB client.)

2. **Fix Alembic revision mismatch:**  
   If your DB's `alembic_version` points to a revision that no longer exists in the repo, set it to the latest known revision, then upgrade:
   ```sql
   UPDATE alembic_version SET version_num = 'a1b2c3d4e5f6';
   ```
   Then run: `alembic upgrade head`
