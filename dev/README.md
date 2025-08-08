# Development Files

This directory contains development, testing, and utility files that are not part of the core production system.

## Structure

### `/tests/`
All test files (`test_*.py`) for various components and integrations:
- Platform integration tests (Google, Microsoft, Zoom, Okta)
- Performance and caching tests
- Comprehensive workflow tests

### `/utilities/`
Analysis and utility scripts for development and troubleshooting:
- User verification and analysis scripts
- Performance testing utilities
- Data integrity checks
- Duplicate detection tools

### `/experiments/`
One-off execution scripts and experimental code:
- Individual termination execution scripts
- Alternative processors and approaches
- Development prototypes

## Note
These files are excluded from Git tracking via `.gitignore` as they are development-specific and not needed for production deployment.
