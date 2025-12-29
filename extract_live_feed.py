
import re

file_path = 'main_backend/static/dashboard/app.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

def print_func_body(name):
    # Improved regex to find function logic
    # Looking for "function connectLiveFeed() {" or similar
    pattern = re.compile(r'function\s+' + name + r'\s*\([^)]*\)\s*\{')
    match = pattern.search(content)
    
    if match:
        start_idx = match.start()
        # Find matching brace
        brace_count = 0
        found_start = False
        end_idx = -1
        
        for i in range(start_idx, len(content)):
            char = content[i]
            if char == '{':
                brace_count += 1
                found_start = True
            elif char == '}':
                brace_count -= 1
                
            if found_start and brace_count == 0:
                end_idx = i + 1
                break
        
        if end_idx != -1:
            print(f"--- {name} ---")
            print(content[start_idx:end_idx])
        else:
            print(f"--- {name} --- (Incomplete body)")
    else:
        print(f"--- {name} --- (Function not found)")

print_func_body("connectLiveFeed")
