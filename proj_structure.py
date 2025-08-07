def create_project_structure():
    """Create the complete project structure"""
    
    directories = [
        "web_page_analyzer",
        "tests",
        "examples", 
        "screenshots",
        "analysis_results",
        "docs"
    ]
    
    files = {
        "requirements.txt": REQUIREMENTS.strip(),
        "setup.py": SETUP_PY.strip(),
        "web_page_analyzer/__init__.py": "",
        "web_page_analyzer/config.py": open(__file__).read(),
        "tests/__init__.py": "",
        "tests/test_analyzer.py": create_test_file(),
        "examples/__init__.py": "",
        ".gitignore": create_gitignore(),
        "README.md": create_readme(),
        "docker-compose.yml": create_docker_compose()
    }
    
    # Create directories
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")
    
    # Create files
    for filepath, content in files.items():
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Created file: {filepath}")
    
    print("\nProject structure created successfully!")
    print("Next steps:")
    print("1. cd into the project directory")
    print("2. pip install -r requirements.txt")
    print("3. python -m pytest tests/")
    print("4. python examples/basic_usage.py")