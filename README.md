# Audio File Processing Script

A Python script for converting and organizing audio files according to specific naming conventions and quality standards.

## Requirements

- Python 3.x
- pydub
- eyed3
- reportlab

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Basic usage:
```bash
python convert_to_wav.py <input_directory>
```

With options:
```bash
python convert_to_wav.py <input_directory> --output_dir <output_directory> --artist "artist_name" --instrumental
```

## Processing Rules

1. File Type Rules:
   - Accepts both .mp3 and .wav files as input
   - Converts all files to .wav format with specs:
     * Stereo (2 channels)
     * 44.1kHz sample rate
     * 16-bit depth

2. Duration Rule:
   - Files shorter than 2 minutes are moved to `Excluded/` folder
   - Reason marked as "Too short"

3. Vox/Instrumental Pair Detection (Priority 1):
   - Identifies files with "with vox" or "+ vox" in name
   - Both the vox file and its matching base file go to `manually/`
   - Reason marked as "Type undetermined"

4. Version Conflict Detection (Priority 2):
   - Multiple files sharing exact same base name (e.g., "SONG.mp3" and "SONG 123.mp3")
   - All versions moved to `manually/`
   - Reason marked as "Versioning"

5. Manual Processing Triggers:
   - Files with explicit version numbers (V1, V2, etc.)
   - Files with length variants in name (short, long, longer)
   - Purely numeric filenames (e.g., "12345.mp3")

6. Filename Cleaning Rules:
   - Convert to lowercase
   - Replace spaces with underscores
   - Remove:
     * Technical specs (khz, bit)
     * Numbers after hyphens
     * Special characters
     * Multiple underscores
     * Trailing underscores
   - Add "instrumental" suffix if:
     * File has instrumental indicators ("no vox", "instrumental", etc.)
     * `--instrumental` flag is used
   - Add artist prefix if `--artist` flag is used

7. Directory Structure:
   - `processed/` - Successfully converted files
   - `manually/` - Files needing manual review
   - `Excluded/` - Files that are too short or had errors

8. Error Handling:
   - Files that fail processing are moved to `Excluded/`
   - Reason marked as "Processing error"

## Command Line Options

- `input_directory`: Directory containing the audio files to process
- `--output_dir`: Optional. Directory to save processed files (defaults to input directory)
- `--artist`: Optional. Artist name to prefix to all filenames
- `--instrumental`: Optional. Mark all files as instrumentals

## Output

The script creates three directories:
1. `processed/` - Contains all successfully converted WAV files
2. `manually/` - Contains files that need manual review
3. `Excluded/` - Contains files that are either too short (< 2 minutes) or failed to process

A PDF report is generated in the processed directory with details of all processed files. 