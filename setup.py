from setuptools import setup, find_packages

setup(
    name="pg_lineagelens",
    version="1.0.0",
    description="PostgreSQL Performance Analyzer",
    author="Somasundaram Sekar",
    author_email="somasundaram@outlook.com",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "flask>=2.0.0",
        "psycopg2-binary>=2.9.0",
        "pandas>=1.3.0",
        "networkx>=2.6.0",
        "matplotlib>=3.4.0",
        "sqlparse>=0.4.0",
        "waitress>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "pg_lineagelens=app_launcher:start_server",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Database Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
)