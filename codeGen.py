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

def collect_code_files(directories, output_file_path):
    """Recursively collect all code files and their contents from multiple directories, excluding common directories and files."""
    output = []
    
    # Define exclusion lists
    excluded_dirs = {
        'node_modules', '.git', '__pycache__', 'dist', 'build', 
        '.vscode', '.idea', 'venv', '.env', 'target', 'out', '.venv',
        'bower_components', 'coverage', '.cache', '.pytest_cache',
    }
    excluded_files = {
        'package-lock.json', 'yarn.lock', '.DS_Store', 'pnpm-lock.yaml',
        'vite.config.ts', 'vite.config.js'
    }
    
    # Add the script itself and the output file to the exclusion list
    script_path = pathlib.Path(__file__).resolve()
    resolved_output_path = pathlib.Path(output_file_path).resolve()
    
    for directory in directories:
        directory = pathlib.Path(directory)
        if not directory.exists() or not directory.is_dir():
            output.append(f"# Directory Skipped: {directory}\n*Error: Not a valid directory*\n")
            continue
            
        output.append(f"# Directory: {directory}\n")
        
        try:
            for item in directory.rglob('*'):
                # Resolve item path for accurate comparison
                resolved_item = item.resolve()

                # Exclude the script itself and the output file
                if resolved_item == script_path or resolved_item == resolved_output_path:
                    continue

                # Check if any part of the path is an excluded directory
                if any(part in excluded_dirs for part in item.parts):
                    continue

                if item.is_file():
                    # Check if the file itself is excluded by name
                    if item.name in excluded_files:
                        continue
                    
                    if is_code_file(item):
                        try:
                            with open(item, 'r', encoding='utf-8') as file:
                                content = file.read()
                            # Get relative path from the input directory
                            relative_path = item.relative_to(directory)
                            # Create markdown code block
                            output.append(f"### {relative_path}\n```")
                            output.append(content)
                            output.append("```\n")
                        except (UnicodeDecodeError, PermissionError) as e:
                            relative_path = item.relative_to(directory)
                            output.append(f"### {relative_path}\n*Error reading file: {str(e)}*\n")
        except Exception as e:
            output.append(f"*Error accessing directory {directory}: {str(e)}*\n")
    
    return '\n'.join(output)

def save_to_markdown(content, output_file):
    """Save the collected content to a markdown file."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Output saved to {output_file}"
    except Exception as e:
        return f"Error saving file: {str(e)}"

def main(directories, output_file="code_collection.md"):
    """Main function to process multiple directories and generate markdown."""
    if not directories:
        return "Error: No directories provided"
    
    content = collect_code_files(directories, output_file)
    if not content:
        return "No code files found in the provided directories"
    
    return save_to_markdown(content, output_file)

if __name__ == "__main__":
    # Example usage: replace with your directory paths
    # directory_paths = ["./backend", "./frontend"]  # Adjust these paths as needed
    directory_paths = ["./"]
    output_path = "code_collection.md"
    result = main(directory_paths, output_path)
    print(result)