# Syntax Guardian 🛡️

> An AI-powered Code Quality Intelligence Agent that analyzes repositories and generates actionable, developer-friendly reports.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Latest-red.svg)](https://streamlit.io/)

## 🚀 What Syntax Guardian Does

Syntax Guardian is an intelligent code analysis agent that goes beyond simple linting to provide comprehensive insights into your codebase. It helps development teams maintain code quality at scale by:

- **🔍 Multi-Language Analysis**: Supports Python and JavaScript/TypeScript repositories
- **📊 Quality Scoring**: Generates overall quality scores (0-100) and per-category breakdowns
- **🎯 Issue Detection**: Identifies security vulnerabilities, performance bottlenecks, code duplication, complexity issues, testing gaps, and documentation problems
- **💬 Interactive Q&A**: Answers natural language questions about your codebase with precise file:line citations
- **📈 Actionable Reports**: Provides detailed explanations of issues and practical fix suggestions

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Ingestion     │───▶│   Embeddings    │───▶│   Detectors     │
│   Layer         │    │   Generation    │    │   Pipeline      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   File System   │    │   Vector Store  │    │   Issue Rules   │
│   Processing    │    │   (Chroma)      │    │   Engine        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                 │                       │
                                 ▼                       ▼
                        ┌─────────────────┐    ┌─────────────────┐
                        │      Q&A        │    │   Severity      │
                        │   Retrieval     │    │   Scoring       │
                        └─────────────────┘    └─────────────────┘
                                 │                       │
                                 ▼                       ▼
                        ┌─────────────────────────────────────────┐
                        │           Report Generation             │
                        │        (Markdown + JSON)               │
                        └─────────────────────────────────────────┘
```

### Core Components

- **Ingestion Layer**: Handles repository cloning, file processing, and content extraction
- **Embeddings Generation**: Creates vector representations using Chroma for semantic search
- **Detectors Pipeline**: Rule-based issue detection across multiple categories
- **Severity Scoring**: Intelligent prioritization using smooth decay algorithms
- **Q&A System**: RAG-powered conversational interface with precise citations
- **Report Generation**: Comprehensive markdown and JSON output formats

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.10 or higher
- Git
- uv (recommended) or pip
- Groq API key for Q&A functionality

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/AmanS2501/Syntax_Guardian.git
   cd Syntax_Guardian
   ```

2. **Install dependencies**:
   ```bash
   # Using uv (recommended)
   uv venv
   uv pip install -e .
   
   # Or using pip
   pip install -e .
   ```

3. **Set up environment variables**:
   ```bash
   # Windows CMD
   set GROQ_API_KEY=your_groq_api_key_here
   
   # Windows PowerShell
   $env:GROQ_API_KEY="your_groq_api_key_here"
   
   # Linux/Mac
   export GROQ_API_KEY="your_groq_api_key_here"
   ```

## 🎮 Usage

### Command Line Interface

#### Basic Analysis
```bash
# Index a repository (creates embeddings)
uv run cqia index .

# Analyze code quality
uv run cqia analyze <path-to-repository>

# Combined index + analyze
uv run cqia analyze <path-to-repository> --with-index
```

#### Interactive Q&A
```bash
# Ask questions about your codebase
uv run cqia chat <path-to-repository> --question "How is authentication implemented?"

# Follow-up questions in interactive mode
uv run cqia chat <path-to-repository> --interactive
```

### Web Interface

#### FastAPI Backend
```bash
# Start the API server
uv run cqia serve-api

# Access at http://127.0.0.1:8000
# Interactive docs at http://127.0.0.1:8000/docs
```

#### Streamlit UI
```bash
# Start the web interface
uv run cqia serve-ui

# Access at http://localhost:8501
```

### Example Workflow

```bash
# 1. Analyze a Python project
uv run cqia analyze ./my-python-project

# 2. Review the generated report
cat ./my-python-project/report.md

# 3. Ask specific questions
uv run cqia chat ./my-python-project --question "What are the main security concerns?"

# 4. Use web interface for GitHub repos
uv run cqia serve-ui
# Then paste GitHub URL in the web interface
```

## 📋 Features & Capabilities

### Code Quality Detection

| Category | Description | Examples |
|----------|-------------|----------|
| 🔒 **Security** | Identifies potential vulnerabilities | SQL injection risks, hardcoded secrets, unsafe deserialization |
| ⚡ **Performance** | Detects performance bottlenecks | Inefficient loops, memory leaks, blocking operations |
| 📝 **Documentation** | Finds documentation gaps | Missing docstrings, outdated comments, unclear variable names |
| 🔄 **Duplication** | Spots code duplication | Repeated logic blocks, similar function patterns |
| 🧩 **Complexity** | Measures code complexity | High cyclomatic complexity, deep nesting levels |
| 🧪 **Testing** | Identifies testing gaps | Low test coverage, missing edge cases, test quality issues |

### Quality Scoring System

- **Overall Score**: 0-100 scale using smooth decay algorithm `100/(1+weighted_load)`
- **Category Scores**: Individual scores for each quality dimension
- **Severity Weighting**: P0 (Critical) → P1 (High) → P2 (Medium) → P3 (Low)
- **Trend Tracking**: JSON reports enable historical quality tracking

### Interactive Q&A Features

- **Contextual Answers**: Responses grounded in your specific codebase
- **Precise Citations**: Every answer includes `[file:start-end]` line references  
- **Report Integration**: Incorporates generated findings for better context
- **Follow-up Support**: Conversational interface for deeper exploration

## 📊 Sample Output

### Quality Report Structure
```markdown
# Code Quality Report

## Summary
- **Overall Quality Score**: 78/100
- **Total Files Analyzed**: 45
- **Issues Found**: 23
- **Critical Issues**: 2

## Category Scores
- Security: 85/100
- Performance: 72/100
- Documentation: 65/100
- Testing: 80/100
- Complexity: 75/100
- Duplication: 88/100

## Top Priority Issues

### 🔒 Critical: Potential SQL Injection
**File**: `src/database/queries.py:45-52`
**Why this matters**: Direct string concatenation in SQL queries can lead to injection attacks
**How to fix**: Use parameterized queries or an ORM like SQLAlchemy
```

### Q&A Example
```
Q: "How is user authentication implemented?"

A: User authentication is implemented using JWT tokens in the auth module [auth/jwt_handler.py:15-45]. 
The system uses a token-based approach where users receive a JWT after successful login validation 
[auth/login.py:23-35]. The tokens are verified on each protected route using the @require_auth 
decorator [auth/decorators.py:12-28].

Key components:
- Token generation: auth/jwt_handler.py:15-25
- Login validation: auth/login.py:23-35  
- Route protection: auth/decorators.py:12-28
```

## 🔧 Configuration

### Analysis Settings
```python
# config.py example
ANALYSIS_CONFIG = {
    'include_patterns': ['**/*.py', '**/*.js', '**/*.ts'],
    'exclude_patterns': ['**/node_modules/**', '**/__pycache__/**'],
    'max_file_size': '1MB',
    'complexity_threshold': 10,
    'duplication_threshold': 0.8
}
```

### Q&A Settings
```python
QA_CONFIG = {
    'model': 'llama-3.3-70b-versatile',  # Groq model
    'chunk_size': 1000,
    'chunk_overlap': 200,
    'max_results': 5
}
```

## 🏆 Advanced Features

### RAG (Retrieval-Augmented Generation)
- Semantic search across codebase using vector embeddings
- Context-aware responses using Chroma vector database
- Efficient chunking and retrieval for large repositories

### Severity Scoring Algorithm
```python
def calculate_quality_score(issues):
    """
    Smooth decay scoring: 100/(1+weighted_load)
    Emphasizes critical issues while dampening noise
    """
    weights = {'P0': 10, 'P1': 5, 'P2': 2, 'P3': 1}
    weighted_load = sum(weights[issue.severity] for issue in issues)
    return 100 / (1 + weighted_load)
```

### Multi-Language Support
- **Python**: AST parsing, import analysis, security pattern detection
- **JavaScript/TypeScript**: ESLint integration, dependency analysis, performance patterns

## 🌐 Web Deployment

### Local Development
```bash
# API + UI together
docker-compose up

# Or separately
uv run cqia serve-api &
uv run cqia serve-ui
```

### GitHub Integration
The web interface supports direct GitHub repository analysis:
1. Paste GitHub repository URL
2. Agent clones and analyzes automatically  
3. View results in interactive dashboard
4. Ask questions about the analyzed code

## 🧪 Testing

```bash
# Run the test suite
pytest tests/

# Run with coverage
pytest --cov=syntax_guardian tests/

# Run specific test categories
pytest tests/test_detectors.py -v
pytest tests/test_qa.py -v
```

## 🚀 Extending Syntax Guardian

### Adding New Detectors
```python
# detectors/custom_detector.py
class CustomDetector(BaseDetector):
    def detect(self, file_content, file_path):
        issues = []
        # Your detection logic here
        return issues
```

### Adding Language Support
```python
# parsers/new_language_parser.py
class NewLanguageParser(BaseParser):
    def parse(self, content):
        # Language-specific parsing logic
        return parsed_content
```

## 🔍 Troubleshooting

### Common Issues

**Q&A fails with authentication error**
- Verify `GROQ_API_KEY` is set correctly
- Check that the API key has sufficient credits
- Ensure model name `llama-3.3-70b-versatile` is supported

**Clone fails with "destination exists"**
- Use `--clean` mode to safely remove existing directories
- On Windows, the agent handles read-only .git files automatically

**No files indexed**
- Check include/exclude glob patterns in configuration
- Verify file extensions match: `**/*.py`, `**/*.js`, `**/*.ts`
- Ensure repository path is accessible

### Performance Tips

- **Large repositories**: Use `--max-files` flag to limit analysis scope
- **Memory usage**: Adjust chunk size in Q&A configuration  
- **Speed**: Enable `--parallel` processing for multi-file analysis

## 📚 Dependencies

### Core Libraries
- **LangChain**: Agent framework and document processing
- **Chroma**: Vector database for embeddings storage  
- **FastAPI**: High-performance API framework
- **Streamlit**: Interactive web interface
- **ChatGroq**: Groq API integration for LLM capabilities

### Development Tools
- **pytest**: Testing framework
- **black**: Code formatting
- **ruff**: Fast Python linter
- **mypy**: Static type checking

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Setup
```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Pre-commit hooks
pre-commit install

# Run tests before committing
make test
```

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built for the Code Quality Intelligence Agent challenge
- Powered by LangChain, Chroma, FastAPI, Streamlit, and Groq
- Thanks to the development community for inspiration and feedback

## 🔗 Links

- **GitHub Repository**: https://github.com/AmanS2501/Syntax_Guardian
- **Documentation**: [docs/](docs/)
- **Issue Tracker**: [GitHub Issues](https://github.com/AmanS2501/Syntax_Guardian/issues)
- **Discussions**: [GitHub Discussions](https://github.com/AmanS2501/Syntax_Guardian/discussions)

---

**Built with ❤️ for developers who care about code quality**
