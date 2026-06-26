path = r'c:\Users\shiva\Downloads\stitch\stitch\krishimitra_app\lib\screens\login_screen.dart'

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

out = []
i = 0
while i < len(lines):
    line = lines[i]
    # Fix 1: pass role to verifyFirebaseOtp
    if 'await _api.verifyFirebaseOtp(phone);' in line and 'role:' not in line:
        line = line.replace('verifyFirebaseOtp(phone);', 'verifyFirebaseOtp(phone, role: _selectedRole);')
    # Fix 2: smarter role resolution after is_registered check
    if "final String role = (verifyRes['role'] ?? _selectedRole).toString();" in line:
        indent = '    '
        out.append(indent + '// Use DB role if already registered; otherwise use what user selected.\n')
        out.append(indent + 'final String role = isRegistered\n')
        out.append(indent + '    ? (verifyRes[\'role\'] ?? _selectedRole).toString()\n')
        out.append(indent + '    : _selectedRole;\n')
        i += 1
        continue
    out.append(line)
    i += 1

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(out)

print('Done - patched login_screen.dart')
