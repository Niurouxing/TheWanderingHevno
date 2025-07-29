import os
import pathlib
import argparse

def is_code_file(file_path):
    """Check if a file is a code file based on its extension."""
    code_extensions = (
        '.py', '.java', '.cpp', '.c', '.h', '.js', '.ts', '.html', 
        '.css', '.go', '.rb', '.php', '.rs', '.sql', '.sh', '.kt', 
        '.cs', '.swift', '.m', '.mm', '.r', '.pl', '.lua', '.scala', '.yaml',
        '.yml', '.json', '.xml', '.txt', '.md', '.bash'
    )
    return file_path.suffix.lower() in code_extensions

def should_exclude_path(path, base_directory, output_file_name):
    """Check if a path should be excluded."""
    # Get the script name
    script_name = pathlib.Path(__file__).name
    
    # Check if it's the script itself, the output file, or pnpm-lock.yaml
    if path.name == script_name or path.name == output_file_name or path.name == "pnpm-lock.yaml":
        return True
    
    # Check if path contains excluded directories
    excluded_dirs = {'node_modules', 'old_hevno', '.git', '__pycache__'}
    try:
        relative_path = path.relative_to(base_directory)
        path_parts = relative_path.parts
        return bool(excluded_dirs.intersection(path_parts))
    except ValueError:
        return False

def collect_code_files(directory, output_file_name, code_only=False):
    """Recursively collect all code files and their contents."""
    output = []
    base_directory = pathlib.Path(directory).resolve()
    
    try:
        for item in base_directory.rglob('*'):
            if item.is_file() and is_code_file(item) and not should_exclude_path(item, base_directory, output_file_name):
                try:
                    with open(item, 'r', encoding='utf-8') as file:
                        content = file.read()
                    
                    relative_path = item.relative_to(base_directory)
                    
                    if code_only:
                        output.append(content)
                    else:
                        # Create markdown code block
                        output.append(f"### {relative_path}\n```")
                        output.append(content)
                        output.append("```\n")
                except (UnicodeDecodeError, PermissionError) as e:
                    error_message = f"### {relative_path}\n*Error reading file: {str(e)}*\n"
                    if not code_only:
                        output.append(error_message)
                    else:
                        print(f"Warning: Could not read {relative_path}: {e}")

    except Exception as e:
        error_message = f"*Error accessing directory {directory}: {str(e)}*\n"
        if not code_only:
            output.append(error_message)
        else:
            print(error_message)
    
    return '\n'.join(output)

def save_to_file(content, output_file):
    """Save the collected content to a file."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Output saved to {output_file}"
    except Exception as e:
        return f"Error saving file: {str(e)}"

def main(directories, output_file="code_collection.md", code_only=False):
    """Main function to process directories and generate output file."""
    all_content = []
    for directory in directories:
        if not os.path.isdir(directory):
            print(f"Warning: '{directory}' is not a valid directory, skipping.")
            continue
        
        print(f"Processing directory: {directory}...")
        content = collect_code_files(directory, output_file, code_only)
        all_content.append(content)
    
    if not all_content:
        return "No code files found in the specified directories."
    
    final_output = '\n'.join(all_content)
    return save_to_file(final_output, output_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Collect code from multiple directories into a single file."
    )
    parser.add_argument(
        'directories', 
        nargs='+', 
        help='One or more directories to scan for code files.'
    )
    parser.add_argument(
        '-o', '--output', 
        default='code_collection.md', 
        help='The name of the output file.'
    )
    parser.add_argument(
        '--code-only', 
        action='store_true', 
        help='Enable pure code mode, which exports only the raw code without Markdown formatting.'
    )
    
    args = parser.parse_args()
    
    result = main(args.directories, args.output, args.code_only)
    print(result)

    # Example of how to run from the command line:
    # 
    # 1. Standard mode with one directory:
    # python codeGen.py ./packages/schemas
    #
    # 2. Standard mode with multiple directories and a custom output file:
    # python codeGen.py ./dir1 ./dir2 -o my_code.md
    #
    # 3. Pure code mode:
    # python codeGen.py ./dir1 ./dir2 --code-only -o all_code.txt