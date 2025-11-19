import os
import ast
import re
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
TESTS_DIR = PROJECT_ROOT / "tests"

def get_python_files(directory):
    return list(directory.rglob("*.py"))

def get_definitions(files):
    """
    Returns a list of definitions: {'name': str, 'file': Path, 'type': 'function'|'method', 'class': str|None, 'lineno': int}
    """
    definitions = []
    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            # Skip magic methods
                            if item.name.startswith("__") and item.name.endswith("__"):
                                continue
                                
                            definitions.append({
                                'name': item.name,
                                'file': file_path,
                                'type': 'method',
                                'class': class_name,
                                'lineno': item.lineno
                            })
                elif isinstance(node, ast.FunctionDef):
                    # Check if it's a standalone function (not inside a class)
                    # ast.walk doesn't track parent, so we might get methods here if we are not careful.
                    # But since we handle ClassDef above, we can just check if this node is top-level or strictly nested in another function.
                    # A simpler way is to just traverse top-level nodes.
                    pass

            # Re-traverse for top-level functions to avoid double counting methods
            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    if node.name.startswith("__") and node.name.endswith("__"):
                        continue
                    definitions.append({
                        'name': node.name,
                        'file': file_path,
                        'type': 'function',
                        'class': None,
                        'lineno': node.lineno
                    })
                    
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            
    return definitions

def check_usage(definitions, src_files, test_files):
    results = []
    
    # Cache file contents to avoid re-reading
    src_contents = {}
    for f in src_files:
        try:
            with open(f, "r", encoding="utf-8") as file:
                src_contents[f] = file.read()
        except:
            pass
            
    test_contents = {}
    for f in test_files:
        try:
            with open(f, "r", encoding="utf-8") as file:
                test_contents[f] = file.read()
        except:
            pass

    for definition in definitions:
        name = definition['name']
        def_file = definition['file']
        
        # Check usage in SRC
        used_in_src = False
        for f, content in src_contents.items():
            # Simple regex to find word usage
            # We want to find 'name' but not as a definition
            # If f is the definition file, we expect at least 1 occurrence (the definition)
            # So we count occurrences.
            
            matches = len(re.findall(r'\b' + re.escape(name) + r'\b', content))
            
            if f == def_file:
                # In the defining file, we expect 1 definition.
                # If matches > 1, it's used internally.
                if matches > 1:
                    used_in_src = True
                    break
            else:
                if matches > 0:
                    used_in_src = True
                    break
        
        if used_in_src:
            continue
            
        # Check usage in TESTS
        used_in_tests = False
        for f, content in test_contents.items():
            matches = len(re.findall(r'\b' + re.escape(name) + r'\b', content))
            if matches > 0:
                used_in_tests = True
                break
        
        if used_in_tests:
            results.append(definition)
            
    return results

def main():
    print("Scanning for methods used ONLY in tests...")
    src_files = get_python_files(SRC_DIR)
    test_files = get_python_files(TESTS_DIR)
    
    print(f"Found {len(src_files)} source files and {len(test_files)} test files.")
    
    definitions = get_definitions(src_files)
    print(f"Found {len(definitions)} definitions (functions/methods).")
    
    candidates = check_usage(definitions, src_files, test_files)
    
    print(f"\nFound {len(candidates)} methods used ONLY in tests:\n")
    
    # Group by file
    by_file = defaultdict(list)
    for c in candidates:
        by_file[c['file']].append(c)
        
    for file_path, items in by_file.items():
        rel_path = file_path.relative_to(PROJECT_ROOT)
        print(f"File: {rel_path}")
        for item in items:
            context = f"Class: {item['class']}" if item['class'] else "Function"
            print(f"  - {item['name']} ({context}, line {item['lineno']})")
        print("")

if __name__ == "__main__":
    main()
