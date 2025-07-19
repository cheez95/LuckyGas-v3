# Database Web Viewer

This directory contains the setup for Adminer, a web-based database management tool.

## Quick Start

1. Make sure Docker is installed on your system
2. Run the following command in this directory:
   ```bash
   docker-compose up -d
   ```
3. Open your browser and go to: http://localhost:8080
4. Login with these credentials:
   - System: PostgreSQL
   - Server: host.docker.internal (or localhost if not using Docker Desktop)
   - Username: luckygas
   - Password: luckygas123
   - Database: luckygas

## Features

- Browse all tables and data
- Run SQL queries
- Export/Import data
- Edit records directly
- No command line needed!

## Stop the viewer

```bash
docker-compose down
```