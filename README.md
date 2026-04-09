# Web-Based Smart Educational Compiler

## Project Overview

This project implements a comprehensive Web-Based Smart Educational Compiler for a simplified C-like programming language. The compiler demonstrates fundamental compiler construction concepts through an interactive web interface, making it an effective teaching tool for understanding compilation phases.

## Features

### Core Compiler Features
- **Lexical Analysis**: Token recognition and classification
- **Syntax Analysis**: Recursive descent parsing with error recovery
- **Semantic Analysis**: Type checking and symbol table management
- **AST Generation**: Abstract Syntax Tree visualization
- **TAC Generation**: Three Address Code intermediate representation

### Educational Features
- **Interactive Web Interface**: Real-time compilation with visual feedback
- **Error Detection**: Comprehensive error reporting with line numbers
- **Auto-Correction**: One-click error correction for common mistakes
- **Visual Results**: Tabbed interface showing Tokens, Errors, Symbols, AST, and TAC

### Supported Language Constructs
- Variable declarations (int, float)
- Assignment statements
- Arithmetic expressions with operator precedence
- Conditional statements (if-else)
- Loop constructs (while)
- Nested blocks with scope management

## Project Structure

```
├── compiler.py          # Main compiler implementation
├── web_api.py           # Flask REST API
├── test_cases.py        # Comprehensive test suite
├── requirements.txt     # Python dependencies
├── frontend/            # React web application
│   ├── src/
│   │   ├── App.jsx      # Main application component
│   │   ├── components/  # UI components
│   │   └── ...
│   ├── package.json     # Node.js dependencies
│   └── ...


## Quick Start

### Option 1: Easy Launcher (Recommended)
From project root, run:
```bash
npm start
```
This starts both backend and frontend together.

Windows alternative:
- Run `run_project.ps1` to open backend + frontend in separate terminals.

### Option 2: Manual Start

#### Backend Setup
```bash
# Install Python dependencies (if not already installed)
pip install -r requirements.txt

# Run the Flask API server
python web_api.py
```
Server will start on: http://localhost:5000

#### Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies (if not already installed)
npm install

# Start the development server
npm run dev
```
App will start on: http://localhost:3001

### Access the Application
Open http://localhost:3002 in your browser to use the compiler.

## Test Cases

Run the comprehensive test suite:
```bash
python test_cases.py
```

The test suite includes 12 test cases covering:
- Valid syntax validation
- Error detection and reporting
- Semantic analysis
- Auto-correction suggestions

## PBL Assessment

This project is submitted for Phase 2 & 3 assessment of PBL (Project Based Learning) covering:
- **Phase 2**: Syntax Analysis - Parser implementation and AST generation
- **Phase 3**: Semantic Analysis - Symbol table management and type checking

## Technologies Used

- **Backend**: Python 3.8+, Flask, Flask-CORS
- **Frontend**: React 18, Vite, Tailwind CSS
- **Architecture**: REST API, Recursive Descent Parsing
- **Testing**: Comprehensive unit test suite

## Author

[Your Name] - PBL Project Submission

## License

This project is developed as part of academic coursework.
