#!/usr/bin/env python3

import os
import argparse
from pydub import AudioSegment
import eyed3
import re
import shutil
from collections import defaultdict
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime

def is_numeric_filename(filename):
    """Check if filename contains only numbers and spaces."""
    name_without_ext = os.path.splitext(filename)[0]
    # Remove spaces and check if remaining chars are all digits
    return bool(name_without_ext.replace(" ", "").isdigit())

def should_move_to_manual(filename):
    """Check if a file should be moved to manual processing."""
    lower_name = filename.lower()
    return bool(
        re.search(r'v\d+', lower_name) or  # Version numbers
        any(variant in lower_name for variant in ['short', 'long', 'longer']) or  # Length variants
        is_numeric_filename(filename)  # Numeric filenames
    )

def is_instrumental(filename):
    """Check if file is instrumental based on filename."""
    instrumental_indicators = ['no vox', 'intrumrntal', 'instrumental', 'no vocals']
    return any(indicator.lower() in filename.lower() for indicator in instrumental_indicators)

def clean_filename(filename, is_instrumental_track=False, artist_prefix=None):
    """Clean filename according to our rules."""
    # Remove extension and numbers with underscores
    name = os.path.splitext(filename)[0]
    # Remove technical specifications
    name = re.sub(r'\d+\s*khz', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\d+\s*bit', '', name, flags=re.IGNORECASE)
    # Remove numbers after hyphens (e.g., -462092)
    name = re.sub(r'-\d+', '', name)
    # Remove trailing hyphens
    name = name.rstrip('-')
    # Remove numbers and special characters
    name = re.sub(r'[\d_]+$', '', name)
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    # Replace multiple spaces with single underscore
    name = re.sub(r'\s+', '_', name.strip())
    # Convert to lowercase
    name = name.lower()
    # Remove multiple underscores
    name = re.sub(r'_+', '_', name)
    # Remove trailing underscores
    name = name.rstrip('_')
    # Remove any existing 'instrumental' suffix before potentially adding it
    name = name.replace('instrumental', '')
    
    # Add artist prefix if provided
    if artist_prefix:
        name = f"{artist_prefix}_{name}"
    
    # Add instrumental if needed
    if is_instrumental_track:
        name = f"{name}instrumental"
    
    return f"{name}.wav"

def check_wav_specs(audio):
    """Check if WAV file meets our specifications."""
    return (audio.channels == 2 and 
            audio.frame_rate == 44100 and 
            audio.sample_width == 2)

def clean_base_name(filename):
    """Clean a filename to get its base name without vox indicators."""
    name = os.path.splitext(filename)[0].lower()
    # Remove all vox patterns
    name = name.replace('with_vox', '').replace('+_vox', '')
    name = name.replace('with vox', '').replace('+ vox', '')
    # Clean up any double underscores and trailing underscores
    name = re.sub(r'_+', '_', name).strip('_')
    return name

def move_to_manual(file, manual_dir, reason):
    """Move a file to the manual processing directory."""
    try:
        source_path = os.path.join(os.path.dirname(manual_dir), file)
        dest_path = os.path.join(manual_dir, file)
        shutil.copy2(source_path, dest_path)
        print(f"Moved to manual processing: {file} (Reason: {reason})")
    except Exception as e:
        print(f"Error moving {file} to manual directory: {e}")

def is_vox_file(filename):
    """Check if file has any vox pattern in its name."""
    lower_name = filename.lower()
    return any(pattern in lower_name for pattern in ['with_vox', 'with vox', '+_vox', '+ vox'])

def find_with_vox_pairs(files):
    """Find pairs of files where one has 'with vox' or '+_vox' and the other doesn't.
    
    Returns a tuple of two lists:
    1. List of (file, reason) tuples for files that need manual processing (only non-vox files that are part of a pair)
    2. List of files that are confirmed vocal versions (with vox indicators)
    """
    manual_pairs = []
    vocal_files = []
    base_names = {}
    
    # First pass: collect all base names and identify vox files
    for file in files:
        name = os.path.splitext(os.path.basename(file))[0].lower()
        # Store original name with numbers
        name_with_numbers = name
        # Remove all numbers for base name comparison
        name_no_numbers = re.sub(r'\d+', '', name).strip()
        
        # Check if this is a vox file by looking for various vox patterns
        is_vox = bool(re.search(r'(?:with|with_|\+|\+ ).*vox', name_no_numbers, re.IGNORECASE))
        
        # Get clean base name by removing vox pattern if present
        clean_name = re.sub(r'(?:with|with_|\+|\+ ).*vox', '', name_no_numbers, re.IGNORECASE).strip()
        clean_name = re.sub(r'\s+', ' ', clean_name)  # normalize spaces
        
        # Keep the numbers in the key to distinguish between different versions
        key = re.sub(r'(?:with|with_|\+|\+ ).*vox', '', name_with_numbers, re.IGNORECASE).strip()
        key = re.sub(r'\s+', ' ', key)  # normalize spaces
        
        if key not in base_names:
            base_names[key] = {'vox': [], 'non_vox': []}
        
        # Add to appropriate list
        if is_vox:
            base_names[key]['vox'].append(file)
        else:
            base_names[key]['non_vox'].append(file)
    
    # Second pass: identify pairs and vocal files
    for base_name, files_dict in base_names.items():
        vox_files = files_dict['vox']
        non_vox_files = files_dict['non_vox']
        
        # If we have both vox and non-vox files for this exact base name
        if vox_files and non_vox_files:
            # Add non-vox files to manual processing
            for file in non_vox_files:
                manual_pairs.append((file, "Vocal or Instrumental?"))
            # Add vox files to vocal_files list for processing
            vocal_files.extend(vox_files)
        # If we only have vox files, they're confirmed vocals
        elif vox_files:
            vocal_files.extend(vox_files)
        # If we only have non-vox files, they go to normal processing
        # (we don't do anything with them here)
    
    return manual_pairs, vocal_files

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
    
    # Vox Pairs section (files with "Vocal or Instrumental?" reason)
    vox_entries = [(f, r) for f, r in manual_entries if r == "Vocal or Instrumental?"]
    if vox_entries:
        elements.append(Paragraph("Files Needing Type Verification", styles['Heading2']))
        vox_data = [["Original File", "Reason"]]
        # Sort by filename
        vox_entries.sort(key=lambda x: x[0].lower())
        vox_data.extend(vox_entries)
        
        vox_table = Table(vox_data, colWidths=[300, 200])
        vox_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(vox_table)
        elements.append(Spacer(1, 20))
    
    # Other Manual Files section (files with reasons other than "Vocal or Instrumental?")
    other_manual_entries = [(f, r) for f, r in manual_entries if r != "Vocal or Instrumental?"]
    if other_manual_entries:
        elements.append(Paragraph("Other Files Moved to Manual Processing", styles['Heading2']))
        manual_data = [["Filename", "Reason"]]
        
        # Sort by filename
        other_manual_entries.sort(key=lambda x: x[0].lower())
        manual_data.extend(other_manual_entries)
        
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
        elements.append(Spacer(1, 20))
    
    # Excluded Files section (always show this section)
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

def validate_file_lists(all_files, to_process, to_manual, manual_reasons):
    """
    Validate that our file categorization makes sense before moving any files.
    Ensures we have proper pairs in manual processing and no orphaned files.
    """
    # Group files by their base names (keeping numbers, removing only vox indicators)
    manual_groups = defaultdict(list)
    process_groups = defaultdict(list)
    
    # Group manual files
    for file in to_manual:
        name = os.path.splitext(file)[0].lower()
        # Keep numbers, only remove vox indicators
        key = re.sub(r'(?:with|with_|\+|\+ ).*vox', '', name, re.IGNORECASE).strip()
        key = re.sub(r'\s+', ' ', key)  # normalize spaces
        manual_groups[key].append((file, manual_reasons[file]))
    
    # Group processed files
    for file in to_process:
        name = os.path.splitext(file)[0].lower()
        # Keep numbers, only remove vox indicators
        key = re.sub(r'(?:with|with_|\+|\+ ).*vox', '', name, re.IGNORECASE).strip()
        key = re.sub(r'\s+', ' ', key)  # normalize spaces
        process_groups[key].append(file)
    
    # Validate each manual group
    for base_name, group in manual_groups.items():
        # If any file in group is "Vocal or Instrumental?", verify it's part of a vox pair
        if any(reason == "Vocal or Instrumental?" for _, reason in group):
            # All files in the group must have the same reason
            if not all(reason == "Vocal or Instrumental?" for _, reason in group):
                print(f"Inconsistency found: Mixed reasons in group {base_name}")
                print(f"Files: {group}")
                return False
            
            # There must be a corresponding vox file in processing
            if base_name not in process_groups or not any(bool(re.search(r'(?:with|with_|\+|\+ ).*vox', f, re.IGNORECASE)) for f in process_groups[base_name]):
                print(f"Inconsistency found: No corresponding vox file found for manual group")
                print(f"Files: {group}")
                return False
    
    # Check that no file marked for processing has a related file in manual with a different reason
    for base_name, files in process_groups.items():
        if base_name in manual_groups:
            manual_group = manual_groups[base_name]
            if any(reason != "Vocal or Instrumental?" for _, reason in manual_group):
                print(f"Inconsistency found: File marked for processing has related files in manual with different reasons")
                print(f"Files: {files}")
                print(f"Related group: {manual_group}")
                return False
    
    return True

def process_audio_files(input_dir, output_dir=None, artist=None, force_instrumental=False, debug=False):
    """
    Process audio files according to specifications.
    
    Args:
        input_dir: Directory containing input files
        output_dir: Directory for output files (defaults to input_dir)
        artist: Artist name to prefix files with
        force_instrumental: Whether to mark all files as instrumental
        debug: If True, only analyze files and create report without moving/converting
    """
    if output_dir is None:
        output_dir = input_dir
        
    # Define directory paths
    processed_dir = os.path.join(output_dir, "processed")
    excluded_dir = os.path.join(output_dir, "Excluded")
    manual_dir = os.path.join(output_dir, "manually")
    
    # In debug mode, we'll create directories only if they don't exist
    if not debug:
        # Clean up existing directories
        for directory in [processed_dir, excluded_dir, manual_dir]:
            if os.path.exists(directory):
                try:
                    shutil.rmtree(directory)
                    print(f"Cleaned up existing directory: {directory}")
                except Exception as e:
                    print(f"Error cleaning up {directory}: {e}")
        
        # Create fresh directories
        for directory in [processed_dir, excluded_dir, manual_dir]:
            os.makedirs(directory)
            print(f"Created directory: {directory}")
    else:
        # In debug mode, just ensure directories exist
        for directory in [processed_dir, excluded_dir, manual_dir]:
            os.makedirs(directory, exist_ok=True)
        print("Debug mode: Running analysis only - no files will be moved or converted")
    
    # Get all audio files
    audio_files = [f for f in os.listdir(input_dir) 
                  if f.lower().endswith(('.mp3', '.wav'))]
    
    if not audio_files:
        print(f"No audio files found in {input_dir}")
        return
    
    print(f"Found {len(audio_files)} audio files to process.")
    if artist:
        print(f"Using artist prefix: {artist}")
    if force_instrumental:
        print("All files will be marked as instrumental")
    
    # Initialize tracking variables
    to_process = set()
    to_manual = set()
    manual_reasons = {}
    excluded_files = {'short': set(), 'error': set()}
    
    # First pass: Find vox pairs and confirmed vocal files
    manual_pairs, vocal_files = find_with_vox_pairs(audio_files)
    for file, reason in manual_pairs:
        to_manual.add(file)
        manual_reasons[file] = reason
    
    # Add confirmed vocal files to processing list
    for file in vocal_files:
        to_process.add(file)
    
    # Second pass: Check for versioning conflicts in remaining files
    remaining_files = [f for f in audio_files if f not in to_manual and f not in to_process]
    base_names = defaultdict(list)
    for file in remaining_files:
        base_name = os.path.splitext(file)[0]
        # Remove all numbers for grouping
        clean_base = re.sub(r'\d+', '', base_name).strip()
        base_names[clean_base].append(file)
    
    # Move files with versioning conflicts to manual
    for base_name, files in base_names.items():
        if len(files) > 1:
            for file in files:
                to_manual.add(file)
                manual_reasons[file] = "Versioning"
    
    # Mark remaining files for processing or manual review
    for file in audio_files:
        if file not in to_manual and file not in to_process:
            if should_move_to_manual(file):
                to_manual.add(file)
                # Check for version numbers first
                if re.search(r'v\d+', file, re.IGNORECASE):
                    manual_reasons[file] = "Versioning"
                # Then check for length variants
                elif any(variant in file.lower() for variant in ['short', 'long', 'longer']):
                    manual_reasons[file] = "Length variant"
                # Finally, check for numeric filenames
                elif is_numeric_filename(file):
                    manual_reasons[file] = "Numeric filename"
                else:
                    manual_reasons[file] = "Unknown"
            else:
                to_process.add(file)
    
    # Validate our categorization
    if not validate_file_lists(audio_files, to_process, to_manual, manual_reasons):
        raise Exception("CRITICAL: File categorization validation failed. This indicates a bug in the code logic - please report this issue.")
    
    if debug:
        print("\nAnalysis complete. Here's what would happen:")
        print(f"\nFiles to be processed ({len(to_process)}):")
        for file in sorted(to_process):
            print(f"  - {file}")
        
        print(f"\nFiles for manual review ({len(to_manual)}):")
        for file in sorted(to_manual):
            print(f"  - {file} (Reason: {manual_reasons[file]})")
        
        # Create PDF report without moving files
        report_file = create_pdf_report(processed_dir, manual_dir, excluded_dir,
                                      [(f, manual_reasons[f]) for f in to_manual],
                                      to_process, to_manual, excluded_files, force_instrumental, artist)
        
        print(f"\nDebug report saved as: {report_file}")
        return report_file
    
    # If not in debug mode, proceed with actual file operations
    processed_files = set()
    manual_files = set()
    
    # First handle manual files - we already know their reasons
    for file in to_manual:
        input_path = os.path.join(input_dir, file)
        manual_path = os.path.join(manual_dir, file)
        try:
            shutil.copy2(input_path, manual_path)
            manual_files.add(file)
            print(f"Moved to manual processing: {file} (Reason: {manual_reasons[file]})")
        except Exception as e:
            print(f"Error moving {file} to manual directory: {e}")
            excluded_files['error'].add(file)
    
    # Then process the files that passed validation
    for file in to_process:
        input_path = os.path.join(input_dir, file)
        
        try:
            # Load the audio file
            if file.lower().endswith('.mp3'):
                audio = AudioSegment.from_mp3(input_path)
            else:  # .wav
                audio = AudioSegment.from_wav(input_path)
            
            # Check duration (in milliseconds)
            duration_ms = len(audio)
            if duration_ms < 120000:  # 2 minutes = 120 seconds = 120000 ms
                print(f"Skipping '{file}' - Duration ({duration_ms/1000:.1f}s) is less than 2 minutes")
                excluded_path = os.path.join(excluded_dir, file)
                shutil.copy2(input_path, excluded_path)
                excluded_files['short'].add(file)
                continue
            
            # Ensure the audio meets our specifications
            audio = audio.set_channels(2)  # Stereo
            audio = audio.set_frame_rate(44100)  # 44.1kHz
            audio = audio.set_sample_width(2)  # 16-bit
            
            # Generate new filename
            is_instrumental_track = force_instrumental or is_instrumental(file)
            new_filename = clean_filename(file, is_instrumental_track, artist)
            new_path = os.path.join(processed_dir, new_filename)
            
            # Convert and save the file
            audio.export(new_path, format="wav")
            processed_files.add(file)
            print(f"Processed '{file}' → '{new_filename}'")
            
        except Exception as e:
            print(f"Error processing {file}: {e}")
            try:
                excluded_path = os.path.join(excluded_dir, file)
                shutil.copy2(input_path, excluded_path)
                excluded_files['error'].add(file)
                print(f"Moved '{file}' to Excluded folder due to error")
            except Exception as copy_error:
                print(f"Error moving file to Excluded folder: {copy_error}")
    
    # Create PDF report with the validated categorizations
    report_file = create_pdf_report(processed_dir, manual_dir, excluded_dir, 
                                  [(f, manual_reasons[f]) for f in to_manual], 
                                  processed_files, manual_files, excluded_files, force_instrumental, artist)
    
    print(f"\nProcessing complete! Report saved as: {report_file}")
    print(f"- Processed files are in: {processed_dir}")
    print(f"- Files needing manual review are in: {manual_dir}")
    print(f"- Excluded files (too short or errors) are in: {excluded_dir}")
    
    return report_file

def main():
    parser = argparse.ArgumentParser(description='Convert audio files to WAV format with specific requirements')
    parser.add_argument('input_dir', help='Directory containing input files')
    parser.add_argument('--output_dir', help='Directory for output files (defaults to input directory)')
    parser.add_argument('--artist', help='Artist name to prefix files with')
    parser.add_argument('--instrumental', action='store_true', help='Mark all files as instrumental')
    parser.add_argument('--debug', action='store_true', help='Analyze files and create report without moving/converting')
    
    args = parser.parse_args()
    
    process_audio_files(args.input_dir, args.output_dir, args.artist, args.instrumental, args.debug)

if __name__ == "__main__":
    main() 