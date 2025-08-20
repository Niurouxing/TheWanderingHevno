import os
import pathlib

def is_code_file(file_path):
    """Check if a file is a code file based on its extension."""
    code_extensions = (
        '.py', '.java', '.cpp', '.c', '.h', '.js', '.ts', '.html', 
        '.css', '.go', '.rb', '.php', '.rs', '.sql', '.sh', '.kt', 
        '.cs', '.swift', '.m', '.mm', '.r', '.pl', '.lua', '.scala', '.jsx', 
        '.tsx', '.json', '.yaml', '.yml', '.xml', '.md', '.txt', '.toml', '.in'
    )
    return file_path.suffix.lower() in code_extensions

def collect_code_files(paths, output_file_path):
    """Recursively collect all code files and their contents from multiple directories or specific files, excluding common directories and files."""
    output = []
    
    # Define exclusion lists
    excluded_dirs = {
        'node_modules', '.git', '__pycache__', 'dist', 'build', 
        '.vscode', '.idea', 'venv', '.env', 'target', 'out', '.venv',
        'bower_components', 'coverage', '.cache', '.pytest_cache'
        , 'tests', "shared-theme"
    }
    excluded_files = {
        'package-lock.json', 'yarn.lock', '.DS_Store', 'pnpm-lock.yaml',
        'conftest.py'
    }
    
    # Define files to always include, regardless of extension
    always_include_files = {
        'README', 'LICENSE', 'Dockerfile', 'Makefile', '.gitignore',
        '.dockerignore', 'requirements.txt', 'package.json', 'tsconfig.json'
    }
    
    # Add the script itself and the output file to the exclusion list
    script_path = pathlib.Path(__file__).resolve()
    resolved_output_path = pathlib.Path(output_file_path).resolve()
    
    for path in paths:
        path = pathlib.Path(path)
        if not path.exists():
            output.append(f"# Path Skipped: {path}\n*Error: Path does not exist*\n")
            continue
            
        if path.is_file():
            # Handle individual file
            resolved_path = path.resolve()
            if resolved_path == script_path or resolved_path == resolved_output_path:
                continue
                
            if path.name in excluded_files and path.name not in always_include_files:
                continue
                
            try:
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                output.append(f"### {path}\n```")
                output.append(content)
                output.append("```\n")
            except (UnicodeDecodeError, PermissionError) as e:
                output.append(f"### {path}\n*Error reading file: {str(e)}*\n")
                
        elif path.is_dir():
            output.append(f"# Directory: {path}\n")
            
            try:
                for item in path.rglob('*'):
                    resolved_item = item.resolve()
                    
                    if resolved_item == script_path or resolved_item == resolved_output_path:
                        continue
                        
                    if any(part in excluded_dirs for part in item.parts):
                        continue
                        
                    if item.is_file():
                        if item.name in excluded_files and item.name not in always_include_files:
                            continue
                            
                        if is_code_file(item) or item.name in always_include_files:
                            try:
                                with open(item, 'r', encoding='utf-8') as file:
                                    content = file.read()
                                relative_path = item.relative_to(path)
                                output.append(f"### {relative_path}\n```")
                                output.append(content)
                                output.append("```\n")
                            except (UnicodeDecodeError, PermissionError) as e:
                                relative_path = item.relative_to(path)
                                output.append(f"### {relative_path}\n*Error reading file: {str(e)}*\n")
            except Exception as e:
                output.append(f"*Error accessing directory {path}: {str(e)}*\n")
    
    return '\n'.join(output)

def save_to_markdown(content, output_file):
    """Save the collected content to a markdown file."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Output saved to {output_file}"
    except Exception as e:
        return f"Error saving file: {str(e)}"

def main(paths, output_file="code_collection.md"):
    """Main function to process multiple paths (directories or files) and generate markdown."""
    if not paths:
        return "Error: No paths provided"
    
    content = collect_code_files(paths, output_file)
    if not content:
        return "No code files or specified files found in the provided paths"
    
    return save_to_markdown(content, output_file)

if __name__ == "__main__":
    # paths = [
    #     "./backend", 
    #     "./plugins/core_engine",
    #     # "./plugins/core_api",
    #     "./plugins/core_codex",
    #     # "./plugins/diagnostics",
    #     "./plugins/core_memoria",
    #     "./plugins/core_remote_hooks",
    #     "./plugins/core_websocket",
    #     "./plugins/core_llm",
    #     # "./plugins/core_logging",
    #     # "./plugins/core_persistence",
    #     # "./plugins/core_diagnostics",
    #     # "./frontend",
    #     # "./plugins/core_layout",
    #     # "./plugins/core_llm_config",
    #     # "./plugins/page_demo",
    #     # "./plugins/sandbox_editor",
    #     # "./plugins/sandbox_explorer",
    #     # "./plugins/core_runner_ui",
    #     # "./hevno.json",
    #     # "./cli.py",
    #     # "./frontend",
    #     # "./tests/conftest.py",
    #     # "./tests/conftest_data.py",
    #     # "./conftest.py",
    #     # "./plugins/core_memoria",
    #     # "./",
    # ]

    paths = [
        "./frontend",
        "./plugins/core_layout",
        # "./plugins/page_demo",
        # "./plugins/core_llm_config",
        # "./plugins/sandbox_editor",
        # "./plugins/sandbox_explorer",
        "./plugins/core_runner_ui",
        "./plugins/panel_conversation_stream",
        "./plugins/panel_debug_moment",   
        # "./plugins/core_remote_hooks",
        # "./plugins/core_websocket",
        # "./package.json",
        # "./vite.config.js",
        # "./index.html",
    ]

    # paths = [
    #     "./backend", 
    #     "./frontend",
    #     "./plugins/core_api",
    #     "./plugins/core_goliath",
    #     "./plugins/core_websocket",
    #     "./plugins/core_remote_hooks",
    #     "./plugins/core_persistence",
    #      "./package.json",
    #      "./vite.config.js",
    # ]

    # paths = [  
    #      "./",
    # ]
    output_path = "code_collection.md"
    result = main(paths, output_path)
    print(result)