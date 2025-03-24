import os
import re
import shutil
import argparse
from datetime import datetime
import pydub
from pydub import AudioSegment
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def is_instrumental(filename):
    """Check if file is instrumental based on filename."""
    patterns = [
        r'instrumental',
        r'no\s*vox'
    ]
    return any(re.search(pattern, filename.lower()) for pattern in patterns)

def is_song(filename):
    """Check if file is a song based on filename."""
    patterns = [
        r'with.*vox',
        r'\+.*vox'
    ]
    return any(re.search(pattern, filename.lower()) for pattern in patterns)

def clean_filename(filename, is_instrumental=False, artist=None):
    """Clean filename to required format."""
    # Extract base name without extension
    base_name = os.path.splitext(os.path.basename(filename))[0]
    
    # Remove numbers, special characters and clean up
    clean_name = re.sub(r'[0-9]+', '', base_name)  # Remove numbers
    clean_name = re.sub(r'with.*vox|\+.*vox|no.*vox|instrumental', '', clean_name, flags=re.IGNORECASE)  # Remove vox/instrumental indicators
    clean_name = re.sub(r'[^\w\s]', '', clean_name)  # Remove special characters
    clean_name = clean_name.strip()  # Remove leading/trailing whitespace
    clean_name = re.sub(r'\s+', '_', clean_name)  # Replace spaces with underscores
    clean_name = re.sub(r'_+', '_', clean_name)  # Replace multiple underscores with single underscore
    clean_name = clean_name.rstrip('_')  # Remove trailing underscores
    clean_name = clean_name.lower()  # Convert to lowercase
    
    # Add artist prefix if provided
    if artist:
        clean_name = f"{artist.lower()}_{clean_name}"
    
    # Add instrumental suffix if needed
    if is_instrumental:
        clean_name += "instrumental"
    
    return clean_name + ".wav"

def get_audio_length(file_path, debug=False):
    """
    Get the length of an audio file in seconds.
    
    Args:
        file_path: Path to the audio file
        debug: If True, return a conservative estimate based on file size
        
    Returns:
        float: Length in seconds
    """
    try:
        # Use pydub to get actual length
        audio = AudioSegment.from_file(file_path)
        return len(audio) / 1000.0  # Convert ms to seconds
    except Exception as e:
        print(f"Error getting length of {file_path}: {e}")
        # Fallback for debug mode
        if debug:
            # Assumption: ~1MB per minute for MP3s as a very conservative estimate
            return os.path.getsize(file_path) / (1024 * 1024) * 60
        return 0  # If not debug, safer to return 0

def find_duplicates(files, force_instrumental=False, artist=None):
    """Find duplicate files based on their base names and potential output filename collisions."""
    # Group files by base name (removing vox/instrumental indicators)
    base_names = {}
    
    for file in files:
        # Get the base name without extension
        file_name = os.path.basename(file) if os.path.sep in file else file
        base_name = os.path.splitext(file_name)[0]
        
        # Remove vox/instrumental indicators
        clean_base = re.sub(r'with.*vox|\+.*vox|no.*vox|instrumental', '', base_name, flags=re.IGNORECASE)
        clean_base = clean_base.strip()
        
        if clean_base not in base_names:
            base_names[clean_base] = []
        base_names[clean_base].append(file)
    
    # Also check for potential output filename collisions
    output_names = {}
    for file in files:
        file_name = os.path.basename(file) if os.path.sep in file else file
        is_instrumental_track = force_instrumental or is_instrumental(file_name)
        output_name = clean_filename(file_name, is_instrumental_track, artist)
        
        if output_name not in output_names:
            output_names[output_name] = []
        output_names[output_name].append(file)
    
    # Find base names with multiple files or output name collisions
    duplicates = {}
    
    # First add regular duplicates
    for base_name, files_list in base_names.items():
        if len(files_list) > 1:
            duplicates[base_name] = files_list
    
    # Then add output name collisions
    for output_name, files_list in output_names.items():
        if len(files_list) > 1:
            # Create a unique key for this group
            collision_key = f"collision_{output_name}"
            duplicates[collision_key] = files_list
    
    return duplicates

def create_pdf_report(processed_dir, manual_dir, excluded_dir, manual_entries, processed_files, manual_files, excluded_files, force_instrumental=False, artist=None):
    """Create a PDF report of the processing results."""
    # Create report filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(processed_dir, f"processing_report_{timestamp}.pdf")
    
    # Create the PDF document
    doc = SimpleDocTemplate(report_file, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30
    )
    elements.append(Paragraph("Audio Processing Report", title_style))
    
    # Calculate total excluded files
    total_excluded = len(excluded_files['short']) + len(excluded_files['error'])
    
    # Summary section
    elements.append(Paragraph("Summary", styles['Heading2']))
    summary_data = [
        ["Total Files Processed", str(len(processed_files))],
        ["Files Moved to Manual", str(len(manual_files))],
        ["Files Excluded", str(total_excluded)]
    ]
    
    summary_table = Table(summary_data, colWidths=[200, 100])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    # Processed Files section
    elements.append(Paragraph("Successfully Processed Files", styles['Heading2']))
    if processed_files:
        processed_data = [["Original Filename", "New Filename"]]
        # Create list of (original, new) filename pairs
        filename_pairs = []
        for original in processed_files:
            # Generate the new filename using the same logic as in process_audio_files
            is_instrumental_track = force_instrumental or is_instrumental(original)
            new_filename = clean_filename(original, is_instrumental_track, artist)
            filename_pairs.append((original, new_filename))
        
        # Sort by new filename
        filename_pairs.sort(key=lambda x: x[1].lower())
        processed_data.extend(filename_pairs)
        
        processed_table = Table(processed_data, colWidths=[250, 250])
        processed_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(processed_table)
    else:
        elements.append(Paragraph("No files were processed", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Manual Files section
    elements.append(Paragraph("Files Requiring Manual Review", styles['Heading2']))
    if manual_entries:
        manual_data = [["Filename", "Reason"]]
        
        # Sort by filename
        sorted_manual = sorted(manual_entries, key=lambda x: x[0].lower())
        manual_data.extend(sorted_manual)
        
        manual_table = Table(manual_data, colWidths=[300, 200])
        manual_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(manual_table)
    else:
        elements.append(Paragraph("No files require manual review", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Excluded Files section
    elements.append(Paragraph("Excluded Files", styles['Heading2']))
    if excluded_files['short'] or excluded_files['error']:
        excluded_data = [["Filename", "Reason"]]
        
        # Create and sort the excluded files data
        excluded_entries = []
        # Add files that are too short
        for file in excluded_files['short']:
            excluded_entries.append([file, "Too short"])
            
        # Add files with processing errors
        for file in excluded_files['error']:
            excluded_entries.append([file, "Processing error"])
        
        # Sort by filename
        excluded_entries.sort(key=lambda x: x[0].lower())
        excluded_data.extend(excluded_entries)
        
        excluded_table = Table(excluded_data, colWidths=[300, 200])
        excluded_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(excluded_table)
    else:
        elements.append(Paragraph("No files were excluded", styles['Normal']))
    
    # Build the PDF
    doc.build(elements)
    return report_file

def process_audio_files(input_dir, output_dir=None, manual_dir=None, excluded_dir=None, 
                        min_length=120, force_instrumental=False, artist=None, debug=False):
    """Process audio files in the input directory."""
    # Set up output directories
    if output_dir is None:
        output_dir = os.path.join(input_dir, "processed")
    if manual_dir is None:
        manual_dir = os.path.join(output_dir, "manual")
    if excluded_dir is None:
        excluded_dir = os.path.join(output_dir, "excluded")
    
    # Always create the output directory for the report, even in debug mode
    os.makedirs(output_dir, exist_ok=True)
    
    # Create manual and excluded directories only if not in debug mode
    if not debug:
        os.makedirs(manual_dir, exist_ok=True)
        os.makedirs(excluded_dir, exist_ok=True)
    
    # Get all audio files (just filenames in debug mode, full paths otherwise)
    audio_extensions = ['.mp3', '.wav', '.flac', '.aac', '.ogg']
    audio_files = []
    file_paths = []  # Store full paths for debug mode file size check
    
    for root, _, files in os.walk(input_dir):
        for file in files:
            if os.path.splitext(file)[1].lower() in audio_extensions:
                full_path = os.path.join(root, file)
                
                if debug:
                    # Store both filename and full path for debug mode
                    audio_files.append(file)
                    file_paths.append(full_path)
                else:
                    # Store full path for actual processing
                    audio_files.append(full_path)
    
    if not audio_files:
        print(f"No audio files found in {input_dir}")
        return
    
    print(f"Found {len(audio_files)} audio files to process.")
    
    # First pass: check for known short files in debug mode
    excluded_files = {'short': [], 'error': []}
    valid_files = []
    valid_file_paths = []
    
    for i, file in enumerate(audio_files):
        if debug:
            filename = file  # In debug mode, file is already just the filename
            file_path = file_paths[i]  # Get the full path for file size check
        else:
            file_path = file
            filename = os.path.basename(file)
        
        # Check for known short files by name patterns
        is_short = False
        
        if debug:
            # Specifically known short files
            known_short_files = [
                "Sax Menatesaah",
                "GAME INTRO",
                "SHEE NIHIYA BRIEIM INTRO"
            ]
            
            # Files with likely short patterns in name
            if any(short_name in filename for short_name in known_short_files) or "short" in filename.lower() or "intro" in filename.lower():
                excluded_files['short'].append(filename)
                is_short = True
            else:
                # In debug mode, assume all other files are long enough
                valid_files.append(file)
                valid_file_paths.append(file_path)
        else:
            # Non-debug mode: Actually check audio length
            length = get_audio_length(file_path, debug)
            if length < min_length:
                excluded_files['short'].append(filename)
                is_short = True
            else:
                valid_files.append(file)
                if debug:
                    valid_file_paths.append(file_path)
    
    # Now find duplicates only among valid files
    if debug:
        duplicates = find_duplicates(valid_files, force_instrumental, artist)
    else:
        duplicates = find_duplicates([os.path.basename(f) for f in valid_files], force_instrumental, artist)
    
    # Track processing results
    to_process = []
    to_manual = []
    manual_reasons = {}
    
    # Process each valid file
    for i, file in enumerate(valid_files):
        if debug:
            filename = file  # In debug mode, file is already just the filename
            file_path = valid_file_paths[i]  # Get the full path
        else:
            file_path = file
            filename = os.path.basename(file)
            
        base_name = os.path.splitext(filename)[0]
        clean_base = re.sub(r'with.*vox|\+.*vox|no.*vox|instrumental', '', base_name, flags=re.IGNORECASE).strip()
        
        # Check if file is part of a duplicate set (either base name or output name collision)
        is_duplicate = False
        for key, files_list in duplicates.items():
            if filename in [os.path.basename(f) if os.path.sep in f else f for f in files_list]:
                to_manual.append(filename)
                if key.startswith("collision_"):
                    manual_reasons[filename] = "Output name collision"
                else:
                    manual_reasons[filename] = "Duplicate base name"
                is_duplicate = True
                break
                
        if is_duplicate:
            continue
            
        # If not a duplicate, process normally
        to_process.append(filename)
    
    # Perform the actual processing if not in debug mode
    if not debug:
        processed_files = []
        manual_files = []
        
        for filename in to_process:
            input_file = os.path.join(input_dir, filename)
            try:
                # Determine if track is instrumental based on filename
                is_instrumental_track = force_instrumental or is_instrumental(filename)
                
                # Generate clean output filename
                output_filename = clean_filename(filename, is_instrumental_track, artist)
                output_file = os.path.join(output_dir, output_filename)
                
                # Convert file to WAV (16-bit, 44.1kHz)
                audio = AudioSegment.from_file(input_file)
                audio = audio.set_frame_rate(44100).set_channels(2).set_sample_width(2)
                audio.export(output_file, format="wav")
                
                processed_files.append(filename)
                print(f"Processed: {filename} -> {output_filename}")
                
            except Exception as e:
                # Move file to excluded if there's an error
                print(f"Error processing {filename}: {e}")
                excluded_files['error'].append(filename)
                shutil.copy2(input_file, os.path.join(excluded_dir, filename))
        
        for filename in to_manual:
            input_file = os.path.join(input_dir, filename)
            # Copy to manual directory
            shutil.copy2(input_file, os.path.join(manual_dir, filename))
            manual_files.append(filename)
            print(f"Manual review needed: {filename} (Reason: {manual_reasons[filename]})")
    else:
        # In debug mode, just report what would happen
        processed_files = to_process
        manual_files = to_manual
    
    # Print summary
    print("\nAnalysis complete. Here's what would happen:\n")
    
    print(f"Files to be processed ({len(to_process)}):")
    for file in sorted(to_process):
        print(f"  - {file}")
    
    print(f"\nFiles for manual review ({len(to_manual)}):")
    for file in sorted(to_manual):
        print(f"  - {file} (Reason: {manual_reasons[file]})")
    
    # Create report
    manual_entries = [(f, manual_reasons[f]) for f in to_manual]
    
    if debug:
        report_file = create_pdf_report(output_dir, manual_dir, excluded_dir,
                                       manual_entries, to_process, to_manual, excluded_files,
                                       force_instrumental, artist)
        print(f"\nDebug report saved as: {report_file}")
    else:
        report_file = create_pdf_report(output_dir, manual_dir, excluded_dir,
                                       manual_entries, processed_files, manual_files, excluded_files,
                                       force_instrumental, artist)
        print(f"\nProcessing complete! Report saved as: {report_file}")

def main():
    parser = argparse.ArgumentParser(description='Process audio files for music library.')
    parser.add_argument('input_dir', help='Directory containing audio files')
    parser.add_argument('--output_dir', help='Directory for processed files')
    parser.add_argument('--manual_dir', help='Directory for files needing manual review')
    parser.add_argument('--excluded_dir', help='Directory for excluded files')
    parser.add_argument('--min_length', type=int, default=120, help='Minimum length in seconds (default: 120)')
    parser.add_argument('--artist', help='Artist name to prepend to filenames')
    parser.add_argument('--force_instrumental', action='store_true', help='Force all files to be treated as instrumental')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode (analyze only, no changes)')
    
    args = parser.parse_args()
    
    if args.debug:
        print("Debug mode: Running analysis only - no files will be moved or converted")
    
    process_audio_files(
        args.input_dir,
        args.output_dir,
        args.manual_dir,
        args.excluded_dir,
        args.min_length,
        args.force_instrumental,
        args.artist,
        args.debug
    )

if __name__ == "__main__":
    main()
