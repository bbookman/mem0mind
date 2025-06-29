FROM postgres:15

# Set environment variables for database creation (optional, can be set in docker-compose)
ENV POSTGRES_USER lifeboard_user
ENV POSTGRES_PASSWORD strongpassword
ENV POSTGRES_DB lifeboard_db

# Copy initialization scripts
COPY init.sql /docker-entrypoint-initdb.d/

# Expose PostgreSQL port
EXPOSE 5432
