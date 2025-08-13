# PostgreSQL Setup Guide for Lucky Gas

## 🚀 Quick Start

### One-Command Setup
```bash
cd backend
./setup_local_postgres.sh
```

This will:
1. Install PostgreSQL (if not installed)
2. Create database and user
3. Load environment configuration
4. Initialize database with tables
5. Create admin user and sample data
6. Optionally start the backend

## 📋 What Gets Created

### Database Configuration
- **Database**: `luckygas`
- **User**: `luckygas`
- **Password**: `luckygas123`
- **Host**: `localhost`
- **Port**: `5432`
- **URL**: `postgresql://luckygas:luckygas123@localhost:5432/luckygas`

### Initial Data
- **Admin User**: `admin@luckygas.com` / `admin-password-2025`
- **Sample Products**: 5 products (gas cylinders and services)
- **Sample Drivers**: 2 drivers with vehicles
- **Sample Customers**: 3 customers (restaurants and residential)

## 🔧 Manual Setup Steps

If you prefer to set up manually:

### 1. Install PostgreSQL
```bash
# macOS
brew install postgresql@15
brew services start postgresql@15

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### 2. Create Database and User
```bash
# Run the setup script
./setup_postgres.sh

# Or manually:
createdb luckygas
psql -d postgres -c "CREATE USER luckygas WITH PASSWORD 'luckygas123';"
psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE luckygas TO luckygas;"
```

### 3. Configure Environment
Create `backend/.env.local`:
```env
DATABASE_URL=postgresql://luckygas:luckygas123@localhost:5432/luckygas
SECRET_KEY=local-development-secret-key-32-chars-minimum
FIRST_SUPERUSER=admin@luckygas.com
FIRST_SUPERUSER_PASSWORD=admin-password-2025
ENVIRONMENT=development
DEBUG=true
```

### 4. Initialize Database
```bash
cd backend
uv run python init_db.py
```

### 5. Start Backend
```bash
uv run python run_backend.py
```

## 🎯 Why PostgreSQL?

For your scale (1,267 customers, 350,000+ delivery records), PostgreSQL is the better choice:

### Advantages over SQLite:
- **Concurrent Access**: Handles multiple users better (15 concurrent users)
- **Performance**: Better query optimization for large datasets
- **Features**: Advanced indexes, full-text search, JSON support
- **Production Ready**: Same database in dev and production
- **Scalability**: Can grow with your business

### Performance Benefits:
- Proper indexes for customer/date queries
- Efficient aggregations for reports
- Better handling of 350k+ records
- Connection pooling for concurrent users

## 🧪 Testing the Setup

### 1. Test Database Connection
```bash
# Using psql
PGPASSWORD=luckygas123 psql -U luckygas -d luckygas -h localhost -c "SELECT 1"

# Using Python
uv run python -c "from app.core.database_sync import test_connection; print(test_connection())"
```

### 2. Check Tables Created
```bash
PGPASSWORD=luckygas123 psql -U luckygas -d luckygas -h localhost -c "\dt"
```

### 3. Verify Admin User
```bash
PGPASSWORD=luckygas123 psql -U luckygas -d luckygas -h localhost \
  -c "SELECT email, full_name FROM users WHERE email='admin@luckygas.com'"
```

## 🔍 Troubleshooting

### PostgreSQL Not Starting
```bash
# macOS
brew services restart postgresql@15

# Linux
sudo systemctl restart postgresql
```

### Connection Refused
Check if PostgreSQL is running:
```bash
pg_isready
```

### Permission Denied
Make sure the user has correct privileges:
```bash
psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE luckygas TO luckygas;"
```

### Database Already Exists
Drop and recreate:
```bash
dropdb luckygas
createdb luckygas
```

## 📊 Database Management

### Connect with psql
```bash
PGPASSWORD=luckygas123 psql -U luckygas -d luckygas -h localhost
```

### Useful psql Commands
```sql
-- List tables
\dt

-- Describe table structure
\d customers

-- Count records
SELECT COUNT(*) FROM customers;
SELECT COUNT(*) FROM deliveries;

-- Check indexes
\di

-- Database size
SELECT pg_database_size('luckygas');
```

### Backup Database
```bash
pg_dump -U luckygas -h localhost luckygas > luckygas_backup.sql
```

### Restore Database
```bash
psql -U luckygas -h localhost luckygas < luckygas_backup.sql
```

## 🚦 Starting the Full Stack

### With PostgreSQL:
```bash
# From project root
./start_local.sh
```

This will automatically use PostgreSQL if `.env.local` exists.

### Access Points:
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Frontend**: http://localhost:5173

## 📈 Performance Tips

### For 350,000+ Records:
1. **Indexes are created automatically** on:
   - `deliveries(customer_id, delivery_date)`
   - `deliveries(driver_id, delivery_date)`
   - `orders(customer_id, order_date)`
   - `orders(status, order_date)`

2. **Archive old data** (optional):
   ```python
   # Archive deliveries older than 6 months
   python scripts/archive_old_deliveries.py
   ```

3. **Monitor performance**:
   ```sql
   -- Check slow queries
   SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;
   ```

## ✅ Verification Checklist

- [ ] PostgreSQL installed and running
- [ ] Database `luckygas` created
- [ ] User `luckygas` can connect
- [ ] Tables created (users, customers, products, etc.)
- [ ] Admin user can login
- [ ] Backend starts without errors
- [ ] API docs accessible at http://localhost:8000/docs

## 🎉 Success!

Once everything is set up, you'll have:
- A robust PostgreSQL database perfect for your scale
- Proper indexes for fast queries on 350k+ records
- Sample data to test with
- Admin access to the system
- A production-ready database setup

The system is optimized for:
- **1,267 customers**
- **350,000+ delivery records**
- **15 concurrent users**
- **Fast response times (<100ms)**