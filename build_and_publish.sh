#!/bin/bash
set -e

# Clean old builds
rm -rf build/ dist/ *.egg-info/

# Install build tools
pip install --upgrade pip
pip install --upgrade build twine

# Build source distribution and wheel
python -m build

# Check package
twine check dist/*

echo "Build complete! To publish to PyPI, run:"
echo "twine upload dist/*"
echo ""
echo "To publish to Test PyPI, run:"
echo "twine upload --repository-url https://test.pypi.org/legacy/ dist/*"