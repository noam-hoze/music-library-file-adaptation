# MP3 to WAV Converter

This script converts MP3 files to high quality WAV files (Stereo, 16-bit, 44.1kHz) and renames them according to the format: `artistname_songname.wav` or `artistname_songnameinstrumental.wav`. Songs shorter than 2 minutes are automatically moved to an 'Excluded' folder.

## Requirements

- Python 3.6+
- Required packages:
  - pydub
  - eyed3

## Installation

Install the required packages using pip:

```bash
pip install pydub eyed3
```

Note: pydub requires ffmpeg or libav to be installed on your system.

- For Mac (using Homebrew):
  ```bash
  brew install ffmpeg
  ```

- For Windows:
  Download from [FFmpeg website](https://ffmpeg.org/download.html) and add to PATH

- For Linux:
  ```bash
  sudo apt-get install ffmpeg
  ```

## Usage

```bash
python convert_to_wav.py [input_directory] [--output_dir OUTPUT_DIRECTORY] [--batch] [--artist ARTIST_NAME] [--instrumental]
```

### Arguments:

- `input_directory`: Directory containing the MP3 files (required)
- `--output_dir`: Directory to save the converted WAV files (optional, defaults to input directory)
- `--batch`: Enable batch mode to use metadata without asking for input (optional)
- `--artist`: Default artist name to use for all files (optional, skips all prompts and uses filenames as song names)
- `--instrumental`: Mark all songs as instrumentals (optional, adds "instrumental" to all filenames)

### Examples:

Convert MP3 files in the current directory:
```bash
python convert_to_wav.py .
```

Convert MP3 files and save WAVs to a different directory:
```bash
python convert_to_wav.py ~/Music/mp3s --output_dir ~/Music/wavs
```

Use batch mode for automatic conversion using metadata:
```bash
python convert_to_wav.py ~/Music/mp3s --batch
```

Set the same artist name for all files (without any prompts):
```bash
python convert_to_wav.py ~/Music/mp3s --artist "Artist Name"
```

Mark all songs as instrumentals:
```bash
python convert_to_wav.py ~/Music/mp3s --instrumental
```

Combine options:
```bash
python convert_to_wav.py ~/Music/mp3s --output_dir ~/Music/wavs --artist "Artist Name" --instrumental
```

## How It Works

1. The script scans the input directory for MP3 files
2. For each MP3 file:
   - Checks if the song duration is at least 2 minutes
   - If duration is less than 2 minutes, moves the MP3 to the 'Excluded' folder
   - Otherwise:
     - Converts it to WAV format with stereo, 16-bit, 44.1kHz quality
     - If `--artist` is provided:
       - Uses that name for all files
       - Uses the MP3 filename (without extension) as the song name
       - No user prompts will appear
     - If `--instrumental` is provided:
       - Adds "instrumental" to all filenames
     - Otherwise:
       - Attempts to extract artist and song information from ID3 tags
       - Asks for input if information is missing or if not in batch mode
     - Saves the file in the format: `artistname_songname.wav` or `artistname_songnameinstrumental.wav`

## Notes

- Songs shorter than 2 minutes are automatically moved to an 'Excluded' folder
- Files that fail to process are also moved to the 'Excluded' folder
- All output filenames are converted to lowercase
- When using `--artist`, the script uses MP3 filenames as song names and never prompts the user
- When using `--instrumental`, all songs are marked as instrumentals regardless of content
- Spaces in filenames are automatically replaced with underscores
- Illegal filename characters are removed from artist and song names 