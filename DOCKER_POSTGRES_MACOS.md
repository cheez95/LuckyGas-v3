# PostgreSQL Docker on macOS - Solving Permission Issues

## The Problem

When running PostgreSQL in Docker on macOS, you may encounter this error:
```
mkdir: can't create directory '/var/lib/postgresql/data/pgdata': Permission denied
```

This happens because:
1. macOS has different filesystem permissions than Linux
2. Docker Desktop for Mac uses a virtualization layer
3. Bind mounts (local directories) have permission mismatches between the host and container

## The Solution: Use Named Volumes

Instead of bind mounting a local directory, use Docker named volumes. Docker manages these volumes internally with the correct permissions.

### ❌ DON'T DO THIS (Causes Permission Errors)
```yaml
volumes:
  - ./data:/var/lib/postgresql/data  # Bind mount - causes permission issues
```

### ✅ DO THIS (Works Correctly)
```yaml
volumes:
  - postgres_data:/var/lib/postgresql/data  # Named volume - Docker manages permissions

# Declare the volume at the root level
volumes:
  postgres_data:
```

## Complete Working Configuration

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:latest
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: myuser
      POSTGRES_PASSWORD: mypassword
      # IMPORTANT: Set PGDATA to a subdirectory
      PGDATA: /var/lib/postgresql/data/pgdata
    
    ports:
      - "5432:5432"
    
    volumes:
      # Named volume prevents permission issues
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:  # Declare the named volume
```

## Key Points

1. **Always use named volumes** for PostgreSQL data on macOS
2. **Set PGDATA** environment variable to a subdirectory (e.g., `/var/lib/postgresql/data/pgdata`)
3. **Declare volumes** in the root-level `volumes:` section
4. **Docker manages permissions** automatically for named volumes

## Common Commands

```bash
# Start PostgreSQL
docker-compose up -d postgres

# View logs
docker-compose logs -f postgres

# Stop PostgreSQL (data persists)
docker-compose down

# Stop and remove all data
docker-compose down -v

# Connect with psql
docker exec -it luckygas-postgres psql -U luckygas -d luckygas

# Backup database
docker exec luckygas-postgres pg_dump -U luckygas luckygas > backup.sql

# Restore database
docker exec -i luckygas-postgres psql -U luckygas luckygas < backup.sql
```

## Volume Management

```bash
# List all volumes
docker volume ls

# Inspect volume details
docker volume inspect luckygas_postgres_data

# Remove unused volumes
docker volume prune

# Backup volume data
docker run --rm -v luckygas_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-backup.tar.gz -C /data .

# Restore volume data
docker run --rm -v luckygas_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres-backup.tar.gz -C /data
```

## Using .env File

Create a `.env` file for sensitive data:
```env
POSTGRES_USER=myuser
POSTGRES_PASSWORD=mysecurepassword
POSTGRES_DB=mydb
```

Then reference in docker-compose.yml:
```yaml
environment:
  POSTGRES_USER: ${POSTGRES_USER}
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
  POSTGRES_DB: ${POSTGRES_DB}
```

## Troubleshooting

### PostgreSQL Alpine vs Standard Image UID Mismatch

A common cause of permission errors is switching between PostgreSQL image variants:

- **postgres:15-alpine**: Uses UID 70 for postgres user
- **postgres:15** (standard): Uses UID 999 for postgres user

If you switch images and have existing volume data, you'll get permission errors.

**Solution**: Fix volume ownership to match the image:
```bash
# For standard postgres image (UID 999)
docker run --rm -v your_volume:/data alpine chown -R 999:999 /data

# For alpine postgres image (UID 70)
docker run --rm -v your_volume:/data alpine chown -R 70:70 /data
```

**Recommendation**: Use `postgres:15` (standard) for better compatibility.

### If you still get permission errors:

1. **Remove existing volumes**:
   ```bash
   docker-compose down -v
   docker volume prune
   ```

2. **Check Docker Desktop settings**:
   - Ensure Docker Desktop has file sharing permissions
   - Restart Docker Desktop

3. **Verify no bind mounts**:
   - Check your docker-compose.yml doesn't use `./` paths for PostgreSQL

4. **Use the postgres-only example**:
   ```bash
   docker-compose -f docker-compose.postgres-only.yml up -d
   ```

## Performance Tips

1. Named volumes perform better than bind mounts on macOS
2. Use `postgres:15` (standard) for compatibility, or `postgres:15-alpine` for smaller size
3. Configure PostgreSQL for your workload in `postgresql.conf`
4. Monitor with `docker stats` for resource usage
5. Be consistent with image choice across environments to avoid UID issues

## Security Best Practices

1. Never commit `.env` files with real passwords
2. Use strong passwords in production
3. Restrict PostgreSQL port access with firewall rules
4. Enable SSL for remote connections
5. Regularly update the PostgreSQL image

## Additional Resources

- [Docker Named Volumes Documentation](https://docs.docker.com/storage/volumes/)
- [PostgreSQL Docker Image Documentation](https://hub.docker.com/_/postgres)
- [Docker Desktop for Mac Known Issues](https://docs.docker.com/desktop/mac/troubleshoot/)