import os
import base64
from bs4 import BeautifulSoup
from pathlib import Path
from notes_export_utils import get_tracker

def extract_and_replace_base64_images():
    """Extract base64 images from raw HTML files and create processed HTML files"""
    tracker = get_tracker()
    
    # Check for images-only mode
    images_only = os.environ.get('NOTES_EXPORT_IMAGES_ONLY', 'false').lower() == 'true'
    
    if images_only:
        print("Running in IMAGES-ONLY mode - extracting images to flat directory")
    
    # Get notes that need image extraction
    notes_to_process = tracker.get_notes_to_process('images')
    
    if not notes_to_process:
        print("No notes need image extraction - all up to date!")
        return
    
    print(f"Processing {len(notes_to_process)} notes for image extraction...")
    
    # Set up directories
    raw_folder_path = os.path.join(tracker.root_directory, 'raw')
    html_folder_path = os.path.join(tracker.root_directory, 'html')
    
    # For images-only mode, output directly to root directory
    if images_only:
        images_output_dir = Path(tracker.root_directory)
        images_output_dir.mkdir(parents=True, exist_ok=True)
    
    total_images_extracted = 0
    
    for note in notes_to_process:
        try:
            print(f"Extracting images from: {note['filename']} from {note['notebook']}")
            
            # Build paths for raw and processed HTML files
            if tracker._uses_subdirs():
                raw_file = Path(raw_folder_path) / note['notebook'] / f"{note['filename']}.html"
                html_file = Path(html_folder_path) / note['notebook'] / f"{note['filename']}.html"
                attachments_dir = html_file.parent / 'attachments'
            else:
                raw_file = Path(raw_folder_path) / f"{note['filename']}.html"
                html_file = Path(html_folder_path) / f"{note['filename']}.html"
                attachments_dir = Path(html_folder_path) / 'attachments'
            
            # In images-only mode, use root directory for output
            if images_only:
                attachments_dir = images_output_dir
            
            # Ensure output directory exists (only for non-images-only mode)
            if not images_only:
                html_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if raw file exists
            if not raw_file.exists():
                print(f"Warning: Raw file not found: {raw_file}")
                continue
            
            # Read the raw HTML file, try different encodings
            html_content = None
            for encoding in ['utf-8', 'MacRoman', 'latin-1']:
                try:
                    with open(raw_file, "r", encoding=encoding) as file:
                        html_content = file.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if html_content is None:
                print(f"Error: Could not read {raw_file} with any encoding")
                continue
            
            soup = BeautifulSoup(html_content, "html.parser")
            img_ctr = 0
            images_extracted = False
            
            for img_tag in soup.find_all("img"):
                img_src = img_tag.get("src")
                if img_src and img_src.startswith("data:image"):
                    img_ctr += 1
                    
                    # Ensure attachments directory exists
                    if not attachments_dir.exists():
                        os.makedirs(attachments_dir)
                    
                    # Extract image format and data
                    try:
                        header, image_data = img_src.split(",", 1)
                        img_format = header.split(";")[0].split("/")[1]
                        
                        # Decode and save the image
                        image = base64.b64decode(image_data)
                        img_filename = f"{note['filename']}-attachment-{str(img_ctr).zfill(3)}.{img_format}"
                        img_filepath = attachments_dir / img_filename
                        
                        with open(img_filepath, "wb") as img_file:
                            img_file.write(image)
                        
                        # Log the image writing
                        if images_only:
                            print(f"Image written: {img_filename}")
                        else:
                            relative_path = img_filepath.relative_to(Path(tracker.root_directory))
                            print(f"Image written: {relative_path}")
                        
                        # Update src attribute in HTML to point to extracted image (only for non-images-only)
                        if not images_only:
                            img_relative_path = f"./attachments/{img_filename}"
                            img_tag['src'] = img_relative_path
                        
                        images_extracted = True
                        total_images_extracted += 1
                        
                    except Exception as e:
                        print(f"Error extracting image {img_ctr} from {raw_file}: {e}")
                        continue
            
            # Save processed HTML file only in normal mode (not images-only)
            if not images_only:
                with open(html_file, "w", encoding="utf-8") as file:
                    file.write(str(soup))
                
                if images_extracted:
                    print(f"Processed HTML with extracted images saved: {html_file}")
                else:
                    print(f"Processed HTML saved (no images found): {html_file}")
            
            # Mark as exported in JSON
            tracker.mark_note_exported(note['json_file'], note['note_id'], 'images')
            
        except Exception as e:
            print(f"Error processing {note['filename']}: {e}")
    
    if images_only:
        print(f"\n=== IMAGES-ONLY MODE COMPLETE ===")
        print(f"Total images extracted: {total_images_extracted}")
        print(f"Output directory: {images_output_dir}")

if __name__ == "__main__":
    extract_and_replace_base64_images()
