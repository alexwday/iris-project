# IRIS Project

## Local Development Setup

### Database Setup

This project uses PostgreSQL for the database. For local development, a Docker container is set up:

1. Install Docker Desktop (if not already installed)

2. Start the PostgreSQL container:
   ```bash
   docker-compose up -d
   ```

3. The database will be initialized with the following credentials:
   - Host: localhost
   - Port: 5432
   - Database: maven-finance
   - Username: iris_dev
   - Password: iris_dev_password

4. To stop the database:
   ```bash
   docker-compose down
   ```

5. To stop and remove all data:
   ```bash
   docker-compose down -v
   ```

### Project Setup

1. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install the project in development mode:
   ```bash
   pip install -e .
   ```

3. Run the notebook:
   ```bash
   jupyter notebook notebooks/test_notebook.ipynb
   ```

## Code Quality

- Lint: `flake8 iris/`
- Type check: `mypy iris/`
- Test: `pytest`