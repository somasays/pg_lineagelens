# PostgreSQL Data Lineage Analyzer

A tool for analyzing query performance and building data lineage graphs from PostgreSQL databases.

## Features

- Identify the most expensive queries in your PostgreSQL database
- Build data lineage graphs showing how data flows between tables
- Analyze table usage statistics
- Get performance insights and optimization recommendations
- Export results in various formats (CSV, PNG, GraphML)

## Requirements

- Python 3.8+
- PostgreSQL database with `pg_stat_statements` extension enabled
- Required Python packages (installed automatically):
  - Flask
  - psycopg2
  - pandas
  - networkx
  - matplotlib
  - sqlparse
  - waitress

## Installation

### Option 1: Using pre-built binary (recommended for end users)

1. Download the latest release for your platform:
   - [Windows Installer](https://github.com/somasays/pg_lineagelens/releases/latest/download/pg_lineage_setup.exe)
   - [macOS DMG](https://github.com/somasays/pg_lineagelens/releases/latest/download/PostgreSQL_Data_Lineage.dmg)
   - [Linux Package](https://github.com/somasays/pg_lineagelens/releases/latest/download/PostgreSQL_Data_Lineage_linux.tar.gz)

2. Run the installer or extract the files

3. Launch the application

### Option 2: Install from PyPI

```bash
pip install pg-lineage
```

Then run the application:

```bash
pg_lineage
```

### Option 3: Install from source

1. Clone the repository:

```bash
git clone https://github.com/somasays/pg_lineagelens.git
cd pg_lineagelens
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the application:

```bash
python app_launcher.py
```

## Setting up pg_stat_statements in PostgreSQL

To use this tool, you need to enable the `pg_stat_statements` extension in your PostgreSQL database:

1. Edit your `postgresql.conf` file and add:
   ```
   shared_preload_libraries = 'pg_stat_statements'
   pg_stat_statements.track = all
   ```

2. Restart PostgreSQL

3. Connect to your database and run:
   ```sql
   CREATE EXTENSION pg_stat_statements;
   ```

## Usage

1. Launch the application
2. Enter your PostgreSQL connection details
3. Configure the analysis settings
4. Run the analysis
5. Explore the results:
   - View expensive queries
   - Examine table statistics
   - Visualize data lineage
   - Download reports

## Building from Source

### Requirements

- Python 3.8+
- PyInstaller 5.0+
- pipenv (recommended)

### Using Pipenv (Recommended)

```bash
# Install dependencies
pipenv install
pipenv install --dev

# Build for current platform
pipenv run pyinstaller pyinstaller.spec
```

### Windows

```bash
# Manual build
pip install -r requirements.txt
pyinstaller pyinstaller.spec

# Using the installer script
packaging/windows/build_installer.ps1
```

The executable will be created in the `dist/pg_lineage` directory.

### macOS

```bash
# Manual build
pip install -r requirements.txt
pyinstaller pyinstaller.spec

# Create DMG
bash packaging/macos/create_app.sh
```

The application bundle will be created in the `dist` directory.

### Linux

```bash
# Manual build
pip install -r requirements.txt
pyinstaller pyinstaller.spec

# Create tarball package
bash packaging/linux/create_package.sh
```

## Continuous Integration/Continuous Deployment

This project uses GitHub Actions for automated builds and releases.

### Automated Builds

Every push to the main branch and pull request triggers the build workflow which:
- Builds the application for Windows, macOS, and Linux
- Runs on native runners for each platform to ensure compatibility
- Creates installable packages for each platform

### Creating Releases

1. Tag a commit with a version number:
   ```bash
   git tag -a v1.0.0 -m "Version 1.0.0"
   git push origin v1.0.0
   ```

2. This will trigger the build workflow and automatically:
   - Build all platform packages
   - Create a GitHub release with all build artifacts
   - Generate release notes based on commit history

### Manual Builds

You can also manually trigger the build workflow from the GitHub Actions tab.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [PostgreSQL](https://www.postgresql.org/) - The world's most advanced open source database
- [Flask](https://flask.palletsprojects.com/) - Web framework for Python
- [NetworkX](https://networkx.org/) - Network analysis in Python
- [SQLParse](https://github.com/andialbrecht/sqlparse) - SQL parser for Python