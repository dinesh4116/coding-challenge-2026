import re
import os

with open("stitch_screen_reset.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1. Extract Head content
head_match = re.search(r'<head>(.*?)</head>', html, re.DOTALL)
head_content = head_match.group(1) if head_match else ""

# 2. Extract Body class
body_tag_match = re.search(r'<body([^>]*)>', html)
body_class = ""
if body_tag_match:
    class_match = re.search(r'class="([^"]*)"', body_tag_match.group(1))
    if class_match:
        body_class = class_match.group(1)

# 3. Create index.html
index_html = f"""<!doctype html>
<html lang="en" class="h-full">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    {head_content}
  </head>
  <body class="h-full m-0 p-0 overflow-hidden">
    <div id="root" class="{body_class} w-full h-full"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>"""
with open("index.html", "w", encoding="utf-8") as f:
    f.write(index_html)

# 4. Clear index.css to avoid Tailwind v4 conflict
with open("src/index.css", "w", encoding="utf-8") as f:
    f.write("")

# 5. Extract body content for App.tsx
body_content_match = re.search(r'<body[^>]*>(.*)</body>', html, re.DOTALL)
content = body_content_match.group(1) if body_content_match else html

# Basic JSX replacements
content = content.replace("class=", "className=")
content = content.replace("for=", "htmlFor=")
content = content.replace("<!--", "{/*").replace("-->", "*/}")
content = re.sub(r'style="([^"]*)"', r'style={{}}', content)

# Fix self-closing tags
for tag in ['input', 'img', 'br', 'hr']:
    content = re.sub(r'(<'+tag+r'[^>]*)(?<!/)>', r'\1 />', content)

# Fix problematic HTML attributes
content = content.replace('selected=""', 'defaultValue="1"')
content = content.replace('checked=""', 'defaultChecked')
content = content.replace('checked', 'defaultChecked')

# Write App.tsx
jsx_template = f"""import React, {{ useState, useMemo }} from 'react';
import {{
  DEFAULT_TRIAGE_CONFIG,
  parseCsvFlexible,
  runTriageEngine,
  suggestColumnMapping,
}} from './triageEngine';
import {{ SAMPLE_SYNTHETIC_CSV }} from './sampleSyntheticCsv';

export default function App() {{
  const [config, setConfig] = useState(DEFAULT_TRIAGE_CONFIG);
  
  const triageOutput = useMemo(() => {{
    const parsedCsv = parseCsvFlexible(SAMPLE_SYNTHETIC_CSV);
    const mapping = suggestColumnMapping(parsedCsv.headers);
    return runTriageEngine(
      parsedCsv.headers,
      parsedCsv.rows,
      mapping,
      config
    );
  }}, [config]);

  return (
    <>
      {content}
    </>
  );
}}
"""
with open("src/App.tsx", "w", encoding="utf-8") as f:
    f.write(jsx_template)

print("Conversion complete!")
