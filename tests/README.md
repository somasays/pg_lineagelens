# PostgreSQL Data Lineage Tests

This directory contains the automated tests for the PostgreSQL Data Lineage tool.

## Test Structure

The tests are organized into three categories:

- **Unit Tests** (`tests/unit/`): Fast, isolated tests for individual components
- **Functional Tests** (`tests/functional/`): Tests for Flask routes and web interfaces
- **Integration Tests** (`tests/integration/`): Tests that interact with real databases

## Running Tests

### Prerequisites

- Python 3.8+
- All project dependencies installed (`pipenv install --dev`)
- PostgreSQL server (for integration tests only)

### Basic Usage

Run all tests:

```bash
pipenv run pytest
```

Run a specific test category:

```bash
pipenv run pytest tests/unit/
pipenv run pytest tests/functional/
pipenv run pytest tests/integration/
```

Run a specific test file:

```bash
pipenv run pytest tests/unit/test_analyzer.py
```

Run a specific test function:

```bash
pipenv run pytest tests/unit/test_analyzer.py::TestPostgresQueryLineage::test_init
```

### Integration Tests Configuration

Integration tests require a running PostgreSQL server. By default, they attempt to connect to:

- Host: localhost
- Port: 5432
- Database: postgres
- Username: postgres
- Password: postgres

You can override these settings using environment variables:

```bash
PG_TEST_HOST=my-db-server \
PG_TEST_PORT=5433 \
PG_TEST_DB=test_db \
PG_TEST_USER=test_user \
PG_TEST_PASSWORD=test_password \
pipenv run pytest tests/integration/
```

If the PostgreSQL server is not available, integration tests will be skipped automatically.

### Test Coverage

To generate a test coverage report:

```bash
pipenv run pytest --cov=app tests/
```

For a detailed HTML coverage report:

```bash
pipenv run pytest --cov=app --cov-report=html tests/
```

The HTML report will be available in the `htmlcov` directory.

## Adding New Tests

When adding new tests:

1. Follow the existing structure (unit/functional/integration)
2. Use proper pytest fixtures from `conftest.py`
3. Mock external dependencies when appropriate
4. Add appropriate markers if needed