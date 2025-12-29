
import re

file_path = 'main_backend/static/dashboard/app.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

def print_func_body(name):
    print(f"\n--- {name} ---")
    # Finding "window.name =" or "function name" or "const name ="
    # This is a heuristic.
    match = re.search(r'(function|const|window\.)\s*' + name + r'\s*=?\s*(\([^)]*\)|async\s*\([^)]*\))\s*=>?\s*\{', content)
    if match:
        start = match.start()
        # simplified bracket counting to find end
        count = 0
        found_start = False
        for i, char in enumerate(content[start:]):
            if char == '{':
                count += 1
                found_start = True
            elif char == '}':
                count -= 1
            
            if found_start and count == 0:
                print(content[start:start+i+1])
                return
    else:
        print("Not found")

print_func_body('previewStreamInSettings')
print_func_body('connectLiveFeed')
print_func_body('setupStreamWS')
print_func_body('refreshAttendanceSubjects')
