import os
import zipfile

def create_clean_zip(source_dir, output_zip_path):
    exclude_dirs = {'venv', 'node_modules', '__pycache__', '.git', '.vite'}
    exclude_extensions = {'.pyc', '.pyd'}

    print(f"Creating zip file: {output_zip_path}")
    count = 0
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Modify dirs in-place to prevent os.walk from descending into excluded folders
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
            
            for file in files:
                if any(file.endswith(ext) for ext in exclude_extensions):
                    continue
                if file.endswith('.zip'):
                    continue
                
                full_path = os.path.join(root, file)
                # Compute relative path inside the zip (prefixed with searchpilot-ai/)
                rel_path = os.path.relpath(full_path, os.path.dirname(source_dir))
                zipf.write(full_path, rel_path)
                count += 1
                
    file_size_mb = os.path.getsize(output_zip_path) / (1024 * 1024)
    print(f"Successfully packaged {count} files into {output_zip_path} ({file_size_mb:.2f} MB)")

if __name__ == "__main__":
    src = os.path.dirname(os.path.abspath(__file__))
    out_zip = os.path.join(os.path.dirname(src), "searchpilot-ai-full-project.zip")
    create_clean_zip(src, out_zip)
    
    # Also keep a copy inside project directory for easy download
    out_zip_internal = os.path.join(src, "searchpilot-ai-full-project.zip")
    import shutil
    shutil.copyfile(out_zip, out_zip_internal)
    print(f"Copied zip to internal path: {out_zip_internal}")
