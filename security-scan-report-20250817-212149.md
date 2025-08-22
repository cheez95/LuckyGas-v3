# 🔒 Security Scan Report

**Date**: 2025-08-17 21:21:49  
**Scanner Version**: 1.0.0  
**Project**: Lucky Gas Delivery System

---

## Scan Summary


### ⚠️ PostgreSQL URLs with passwords
**Severity**: HIGH
```
./terraform/database.tf:140:    connection_string = "postgresql://${google_sql_user.app_user.name}:${google_sql_user.app_user.password}@${google_sql_database_instance.postgres.private_ip_address}:5432/${google_sql_database.database.name}"
./start_local.sh:36:DATABASE_URL=postgresql://luckygas:luckygas123@localhost:5432/luckygas
./deploy/migrate-database.sh:30:export DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
./k8s/overlays/staging/secrets-staging.env:6:# DATABASE_URL=postgresql://user:pass@cloud-sql-proxy:5432/luckygas_staging
./tests/rollback/rollback_verification_test.py:70:        db_url = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{test_db}"
./tests/rollback/rollback_verification_test.py:95:        db_url = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{test_db}"
./tests/rollback/rollback_verification_test.py:116:        db_url = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{test_db}"
./tests/rollback/rollback_verification_test.py:170:        db_url = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{test_db}"
./tests/e2e/start-services.sh:105:export DATABASE_URL=${TEST_DATABASE_URL:-"postgresql://test:test@localhost:5432/luckygas_test"}
./tests/e2e/start-services-and-test.sh:49:    TESTING=1 DATABASE_URL="${TEST_DATABASE_URL:-postgresql://test:test@localhost:5432/luckygas_test}" \
```
