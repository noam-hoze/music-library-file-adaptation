#!/usr/bin/env python3

import os
import argparse
from pydub import AudioSegment
import eyed3
import re
import shutil

def convert_mp3_to_wav(input_dir, output_dir=None, batch_mode=False, default_artist=None, is_instrumental=False):
    """
    Convert all mp3 files in input_dir to WAV (Stereo, 16-bit, 44.1kHz)
    and rename them to follow the format: artistname_songname.wav or artistname_songnameinstrumental.wav
    Songs shorter than 2 minutes are moved to an 'Excluded' folder.
    
    Args:
        input_dir (str): Directory containing mp3 files
        output_dir (str, optional): Directory to save converted files. If None, saves in input_dir
        batch_mode (bool): If True, attempt to use ID3 tags without asking for input
        default_artist (str, optional): Default artist name to use for all files
        is_instrumental (bool): If True, all songs are treated as instrumentals
    """
    if output_dir is None:
        output_dir = input_dir
        
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Create Excluded directory if it doesn't exist
    excluded_dir = os.path.join(output_dir, "Excluded")
    if not os.path.exists(excluded_dir):
        os.makedirs(excluded_dir)
    
    # Get all mp3 files in the input directory
    mp3_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.mp3')]
    
    if not mp3_files:
        print(f"No mp3 files found in {input_dir}")
        return
    
    print(f"Found {len(mp3_files)} mp3 files to process.")
    
    for mp3_file in mp3_files:
        mp3_path = os.path.join(input_dir, mp3_file)
        
        try:
            # Load the mp3 file
            audio = AudioSegment.from_mp3(mp3_path)
            
            # Check duration (in milliseconds)
            duration_ms = len(audio)
            if duration_ms < 120000:  # 2 minutes = 120 seconds = 120000 ms
                print(f"Skipping '{mp3_file}' - Duration ({duration_ms/1000:.1f}s) is less than 2 minutes")
                # Copy original MP3 to Excluded folder
                shutil.copy2(mp3_path, os.path.join(excluded_dir, mp3_file))
                continue
            
            # Ensure the audio is stereo, 16-bit, 44.1kHz
            audio = audio.set_channels(2)  # Stereo
            audio = audio.set_frame_rate(44100)  # 44.1kHz
            audio = audio.set_sample_width(2)  # 16-bit
            
            # Get song name from the filename (removing extension)
            filename_without_ext = os.path.splitext(mp3_file)[0]
            
            # Try to get metadata from the mp3 file
            mp3_tags = eyed3.load(mp3_path)
            artist_name = default_artist
            song_name = None
            
            # Extract metadata if available and no default artist is provided
            if mp3_tags and mp3_tags.tag:
                # Only use metadata artist if no default_artist is specified
                if not default_artist:
                    artist_name = mp3_tags.tag.artist
                song_name = mp3_tags.tag.title
            
            # If default artist is provided, skip all prompts and use filename as song name
            if default_artist:
                if not song_name:
                    song_name = filename_without_ext
            else:
                # If no artist name is available and not in batch mode, ask user
                if not artist_name and not batch_mode:
                    artist_name = input(f"Enter artist name for '{mp3_file}': ") or "Unknown"
                
                # If not batch mode or no song name available, ask user
                if not batch_mode or not song_name:
                    song_suggestion = song_name if song_name else filename_without_ext
                    song_name = input(f"Enter song name for '{mp3_file}' [Suggested: {song_suggestion}]: ") or song_suggestion
                
                # Ask about instrumental only if not in batch mode and not specified by parameter
                if not batch_mode and not is_instrumental:
                    is_instrumental_input = input(f"Is '{song_name}' an instrumental? (y/n): ").lower()
                    is_instrumental = is_instrumental_input == 'y'
            
            # Remove any illegal characters for filenames
            artist_name = re.sub(r'[\\/*?:"<>|]', "", artist_name)
            song_name = re.sub(r'[\\/*?:"<>|]', "", song_name)
            
            # Format the new filename
            if is_instrumental:
                new_filename = f"{artist_name}_{song_name}instrumental.wav"
            else:
                new_filename = f"{artist_name}_{song_name}.wav"
            
            # Replace spaces with underscores in the filename and make lowercase
            new_filename = new_filename.replace(" ", "_").lower()
            
            new_path = os.path.join(output_dir, new_filename)
            
            # Convert and save the file
            audio.export(new_path, format="wav")
            print(f"Converted '{mp3_file}' to '{new_filename}'")
            
        except Exception as e:
            print(f"Error processing {mp3_file}: {e}")
            # In case of error, move to Excluded folder
            try:
                shutil.copy2(mp3_path, os.path.join(excluded_dir, mp3_file))
                print(f"Moved '{mp3_file}' to Excluded folder due to error")
            except Exception as copy_error:
                print(f"Error moving file to Excluded folder: {copy_error}")
    
    print("Conversion complete!")

def main():
    parser = argparse.ArgumentParser(description='Convert mp3 files to WAV and rename them')
    parser.add_argument('input_dir', help='Directory containing mp3 files')
    parser.add_argument('--output_dir', help='Directory to save converted files (optional)')
    parser.add_argument('--batch', action='store_true', help='Batch mode - use metadata without asking for input')
    parser.add_argument('--artist', help='Default artist name to use for all files (optional)')
    parser.add_argument('--instrumental', action='store_true', help='Mark all songs as instrumentals')
    
    args = parser.parse_args()
    
    convert_mp3_to_wav(args.input_dir, args.output_dir, args.batch, args.artist, args.instrumental)

if __name__ == "__main__":
    main() 