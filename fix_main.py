#!/usr/bin/env python3
import re

with open('/workspace/main.py', 'r') as f:
    content = f.read()

# Find and replace update_stats calls with inline stats updates
replacements = [
    ('update_stats("invalid")', 'stats["invalid"] += 1\n            stats["checked"] += 1'),
    ('update_stats("valid")', 'stats["valid"] += 1\n            stats["checked"] += 1'),
    ('update_stats("errors")', 'stats["errors"] += 1\n            stats["checked"] += 1'),
    ('update_stats("captcha")', 'stats["valid"] += 1\n            stats["captcha_solved"] += 1\n            stats["checked"] += 1'),
]

for old, new in replacements:
    content = content.replace(old, new)

# Remove the update_stats function definition since we're not using it anymore
# Actually keep it but make sure checked is incremented only once per call
# The issue is that update_stats already increments checked, so we need to ensure
# each path only calls it once

with open('/workspace/main.py', 'w') as f:
    f.write(content)

print("Fixed!")
