# Lucky Gas System Login Credentials

## Production System Access

### Frontend URL
https://storage.googleapis.com/luckygas-frontend-staging-2025/index.html

### Backend API
https://luckygas-backend-production-154687573210.asia-east1.run.app

### Admin Credentials
- **Username**: `admin@luckygas.com`
- **Password**: `admin-password-2025`

## Login Status

✅ **Login is WORKING** with the correct credentials above.

### Issue Resolution Summary

The login issue was caused by using incorrect credentials:
- ❌ Wrong: admin@luckygas.tw / admin123
- ✅ Correct: admin@luckygas.com / admin-password-2025

### Technical Details

1. **Frontend Configuration**: ✅ Correctly pointing to production backend
2. **Backend Status**: ✅ Running and accessible
3. **CORS Configuration**: ✅ Properly configured for Google Cloud Storage
4. **API Endpoints**:
   - `/api/v1/auth/login`: ✅ Working
   - `/api/v1/auth/login-optimized`: ⚠️ Returns 500 error (use regular login)

### Testing the Login

You can test the login directly using curl:

```bash
curl -X POST "https://luckygas-backend-production-154687573210.asia-east1.run.app/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@luckygas.com&password=admin-password-2025"
```

Or simply visit the frontend and use the credentials above:
https://storage.googleapis.com/luckygas-frontend-staging-2025/index.html#/login

## Additional Notes

- The system uses JWT authentication
- Tokens expire after 2 hours
- The backend includes proper CORS headers for the frontend domain
- All API requests should include the Origin header when testing