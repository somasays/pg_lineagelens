from setuptools import setup, find_packages
import os
import codecs
import re

# Get version from _version.py without importing
with open(os.path.join('app', '_version.py'), 'r') as f:
    version_file = f.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        version = version_match.group(1)
    else:
        raise RuntimeError("Unable to find version string.")

# Get the long description from the README file
with codecs.open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="pg_lineagelens",
    version=version,
    description="PostgreSQL Query Lineage and Performance Analyzer",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Somasundaram Sekar",
    author_email="somasundaram@outlook.com",
    url="https://github.com/somasundaram/pg_lineage",
    packages=find_packages() + [
        'app.static', 'app.static.css', 'app.static.js', 'app.static.img', 'app.templates'
    ],
    include_package_data=True,
    package_data={
        "app": ["static/**/*", "templates/**/*"],
        "app.static.css": ["*.css"],
        "app.static.js": ["*.js"],
        "app.static.img": ["*.png", "*.jpg", "*.gif", "*.svg"],
        "app.templates": ["*.html"],
    },
    install_requires=[
        "flask>=2.0.0",
        "psycopg2-binary>=2.9.0",
        "pandas>=1.3.0",
        "networkx>=2.6.0",
        "matplotlib>=3.4.0",
        "sqlparse>=0.4.0",
        "waitress>=2.0.0",
    ],
    py_modules=["app_launcher"],
    entry_points={
        "console_scripts": [
            "pg_lineagelens=app_launcher:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Topic :: Database",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="postgresql, sql, query analysis, performance, lineage",
    python_requires=">=3.8",
)