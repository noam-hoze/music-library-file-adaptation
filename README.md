# Music Library File Adapter

A tool for converting audio files to WAV format with standardized naming conventions, particularly focused on handling instrumental tracks.

## Requirements

- Python 3.12
- FFmpeg (required for processing MP3 and other formats)
- Python packages:
  - pydub
  - reportlab

## Installation

1. Install FFmpeg if not already installed:
   ```
   # macOS
   brew install ffmpeg
   
   # Ubuntu/Debian
   sudo apt-get install ffmpeg
   
   # Windows
   # Download from https://ffmpeg.org/download.html
   ```

2. Set up a virtual environment:
   ```
   python3.12 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # or
   venv\Scripts\activate  # On Windows
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

```
python convert_to_wav.py input_dir [options]
```

For example:
```
python convert_to_wav.py songs/my_music
```

### Options

```
input_dir            Directory containing audio files (required)
--output_dir DIR     Directory for processed files
--manual_dir DIR     Directory for files needing manual review
--excluded_dir DIR   Directory for excluded files
--min_length SEC     Minimum length in seconds (default: 120)
--no_length_check    Disable the minimum length check (default: enabled)
--artist NAME        Artist name to prepend to filenames
--force_instrumental Force all files to be treated as instrumental
--debug              Run in debug mode (analyze only, no changes)
```

## Features

- Converts audio files to 16-bit, 44.1kHz WAV format
- Standardizes filenames:
  - Lowercase
  - Words concatenated directly (no spaces or underscores)
  - Artist name added as prefix with underscore separator (if provided)
  - "instrumental" suffix for instrumental tracks
- Detects instrumental tracks and adds "instrumental" suffix
- Length check is disabled by default (processes all files regardless of duration)
- Identifies duplicates for manual review
- Generates detailed PDF report after processing

## Directory Structure

After processing, the following directory structure is created:

```
output_dir/
  ├── processed/  (successfully converted files)
  ├── manual/     (files needing manual review)
  └── excluded/   (files that are too short or had errors)
```

## Instrumental Detection

The script automatically detects instrumental tracks by looking for keywords:
- "instrumental" in the filename
- "no vox" in the filename

You can also force all files to be treated as instrumental with the `--force_instrumental` flag.

## Current Capabilities

This tool currently formats audio files according to the requirements of **Triple Scoop Music**:
- WAV format (16-bit, 44.1kHz)
- Standardized naming conventions (lowercase, concatenated words)
- Artist name prefixes
- Proper instrumental detection and labeling
- Detailed processing reports with PDF output
- Robust error handling and duplicate detection

## Future Development

The tool can be extended to support additional music libraries and platforms:

### Planned Features
- Support for Artlist naming and format requirements
- Support for APM Music standards
- Batch processing with multiple output formats simultaneously
- GUI interface for easier operation
- Audio waveform visualization and quality analysis
- Integration with metadata embedding for ID3 tags
- Support for additional audio formats (FLAC, AIFF, etc.)
- Cloud storage integration options

Want to contribute? Feel free to submit pull requests or feature suggestions. 