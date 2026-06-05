import os
import re

emoji_pattern = re.compile(r'[\U00010000-\U0010ffff\u2600-\u26FF\u2700-\u27BF]')
results = []

for root, dirs, files in os.walk(r'c:\Users\HomeAdmin\Downloads\bot\core'):
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if emoji_pattern.search(line):
                        results.append(f"{file}:{i+1}: {line.strip()}")

with open('emoji_results.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))
