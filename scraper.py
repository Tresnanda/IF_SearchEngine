import pandas as pd
import gdown
import os
import re
import time
import shutil
import subprocess

CSV_PATH = 'data_source/Pengumpulan Laporan TA FINAL (Respons) - Form Responses 1.csv'
OUTPUT_DIR = 'new_dataset'

def extract_gdrive_id(url):
    if pd.isna(url):
        return None
    match = re.search(r'id=([a-zA-Z0-9_-]+)', str(url))
    if match:
        return match.group(1)
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', str(url))
    if match:
        return match.group(1)
    return None

def download_files():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    print(f"Reading CSV from {CSV_PATH}...")
    try:
        df = pd.read_csv(CSV_PATH)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return
        
    url_column = '1. File TA (yang sudah direvisi) '
    if url_column not in df.columns:
        print(f"Column '{url_column}' not found.")
        return
        
    print(f"Found {len(df)} rows. Starting download...")
    
    for index, row in df.iterrows():
        url = row[url_column]
        title = row['Judul TA']
        file_id = extract_gdrive_id(url)
        
        if not file_id:
            continue
            
        print(f"[{index+1}] Downloading: {title[:50]}... (ID: {file_id})")
        
        clean_title = re.sub(r'[^\w\s-]', '', str(title))[:50]
        
        # Check if already exists as .docx or .pdf
        if os.path.exists(os.path.join(OUTPUT_DIR, f"{clean_title}.docx")) or os.path.exists(os.path.join(OUTPUT_DIR, f"{clean_title}.pdf")):
            print(f"  -> File already exists, skipping")
            continue
        
        final_path = os.path.join(OUTPUT_DIR, f"{clean_title}.docx")
        
        try:
            # Fallback to direct curl, which handles basic files better when gdown is rate limited
            curl_cmd = [
                'curl', '-s', '-L', 
                f'https://drive.google.com/uc?export=download&id={file_id}',
                '-o', final_path
            ]
            
            subprocess.run(curl_cmd, check=True)
            
            # Basic validation
            if os.path.getsize(final_path) < 100000:  # If less than 100kb it might be a redirect HTML
                # Let's see if it's HTML
                with open(final_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(1000)
                    if "<html" in content.lower() or "<!doctype" in content.lower():
                        print(f"  -> Downloaded HTML error page. Trying gdown...")
                        os.remove(final_path)
                        downloaded_path = gdown.download(id=file_id, output=f"{OUTPUT_DIR}/", quiet=True, fuzzy=True)
                        if downloaded_path:
                            # Move/rename logic
                            _, ext = os.path.splitext(downloaded_path)
                            if not ext: ext = '.pdf'
                            actual_path = os.path.join(OUTPUT_DIR, f"{clean_title}{ext}")
                            if os.path.abspath(downloaded_path) != os.path.abspath(actual_path):
                                shutil.move(downloaded_path, actual_path)
                            print(f"  -> Saved via gdown as {actual_path}")
                        else:
                            print(f"  -> Both curl and gdown failed.")
                        continue
            
            # If it's a PDF, change extension
            try:
                out = subprocess.check_output(['file', final_path]).decode('utf-8')
                if 'PDF document' in out:
                    pdf_path = os.path.join(OUTPUT_DIR, f"{clean_title}.pdf")
                    shutil.move(final_path, pdf_path)
                    final_path = pdf_path
            except Exception:
                pass
                
            print(f"  -> Saved as {final_path}")
                
        except Exception as e:
            print(f"  -> Failed with exception: {e}")
            if os.path.exists(final_path): os.remove(final_path)
            
        time.sleep(1) # sleep to prevent rate limiting

if __name__ == "__main__":
    download_files()
