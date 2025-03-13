## CONTRIBUTING.md:

**`CONTRIBUTING.md`**:
```markdown
# Contributing to Conference Presentation System

Thank you for your interest in contributing to the Conference Presentation System! This document provides guidelines and instructions for contributing to this project.

## Code of Conduct

By participating in this project, you agree to abide by its terms.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported by searching the [Issues](https://github.com/ambarish-dey/conference-system/issues)
2. If you're unable to find an open issue addressing the problem, open a new one, including:
   - A clear title and description
   - As much relevant information as possible
   - A code sample or an executable test case demonstrating the expected behavior that is not occurring

### Suggesting Enhancements

1. Open a new issue, clearly describing the enhancement
2. Provide specific examples and use cases
3. If possible, provide a step-by-step description of how the enhancement would work

### Pull Requests

1. Fork the repository
2. Create a new branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests to ensure they pass
5. Commit your changes (`git commit -m 'Add some amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Development Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Run the tests: `python -m tests.run_tests`

## Project Structure

- `app.py`: Main application entry point
- `backup.py`: Backup system implementation
- `config.py`: Configuration management
- `modules/`: Core functionality modules
- `static/`: Static assets (CSS, JS, themes)
- `templates/`: HTML templates
- `tests/`: Test suite
- `scripts/`: Deployment scripts

## Coding Style

- Follow PEP 8 style guidelines for Python code
- Use 4 spaces for indentation
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions small and focused

## Testing

- Write tests for new features or bug fixes
- Ensure all tests pass before submitting a pull request
- Run the test suite with `python -m tests.run_tests`

## Documentation

- Update the documentation when changing core functionality
- Follow Markdown formatting for documentation files
- Include examples for new features

## License

By contributing to this project, you agree that your contributions will be licensed under the same license as the project.