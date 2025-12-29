
import re

file_path = 'main_backend/static/dashboard/app.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

def print_func(name):
    print(f"\n--- {name} ---")
    # Simple regex to find function definition and basic body (imperfect but helps)
    # matching function name() { ... }
    match = re.search(r'function ' + name + r'\s*\(([^)]*)\)\s*\{', content)
    if not match:
        # Try async function
        match = re.search(r'async function ' + name + r'\s*\(([^)]*)\)\s*\{', content)
    
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


print_func('refreshSubjects')
print_func('refreshAttendanceSessionStatus')
print_func('setupStreamWS')
print("\n--- Event Listeners Search ---")
# Check for "change" listeners on dept or sem
print("Dept change listener:", "att-dept" in content and "addEventListener" in content)
print("Sem change listener:", "att-sem" in content and "addEventListener" in content)
print("Btn stop att:", "btn-stop-att" in content)

