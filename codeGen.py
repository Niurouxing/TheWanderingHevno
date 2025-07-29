import os
import pathlib

def is_code_file(file_path):
    """Check if a file is a code file based on its extension."""
    code_extensions = (
        '.py', '.java', '.cpp', '.c', '.h', '.js', '.ts', '.html', 
        '.css', '.go', '.rb', '.php', '.rs', '.sql', '.sh', '.kt', 
        '.cs', '.swift', '.m', '.mm', '.r', '.pl', '.lua', '.scala', '.yaml',
        '.yml', '.json', '.xml', '.txt', '.md', '.bash'
    )
    return file_path.suffix.lower() in code_extensions

def should_exclude_path(path, base_directory):
    """Check if a path should be excluded."""
    # Get the script name
    script_name = pathlib.Path(__file__).name
    
    # Check if it's the script itself, the output file, or pnpm-lock.yaml
    if path.name == script_name or path.name == "code_collection.md" or path.name == "pnpm-lock.yaml":
        return True
    
    # Check if path contains excluded directories
    excluded_dirs = {'node_modules', 'old_hevno'}
    try:
        relative_path = path.relative_to(base_directory)
        path_parts = relative_path.parts
        return bool(excluded_dirs.intersection(path_parts))
    except ValueError:
        return False

def collect_code_files(directory):
    """Recursively collect all code files and their contents."""
    output = []
    directory = pathlib.Path(directory)
    
    try:
        for item in directory.rglob('*'):
            if item.is_file() and is_code_file(item) and not should_exclude_path(item, directory):
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
                    output.append(f"### {relative_path}\n*Error reading file: {str(e)}*\n")
    except Exception as e:
        output.append(f"*Error accessing directory: {str(e)}*\n")
    
    return '\n'.join(output)

def save_to_markdown(content, output_file):
    """Save the collected content to a markdown file."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Output saved to {output_file}"
    except Exception as e:
        return f"Error saving file: {str(e)}"

def main(directory=".", output_file="code_collection.md"):
    """Main function to process directory and generate markdown."""
    if not os.path.isdir(directory):
        return f"Error: {directory} is not a valid directory"
    
    content = collect_code_files(directory)
    if not content:
        return "No code files found in the directory"
    
    return save_to_markdown(content, output_file)

if __name__ == "__main__":
    # Process current directory
    result = main()
    print(result)