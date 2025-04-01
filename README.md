# Audio Transcription App

A desktop application for real-time audio transcription and file upload transcription with AI-powered cleanup features.

## Features

- Real-time audio transcription
- Audio/video file upload and transcription
- Multiple language support
- Speaker diarization (multiple speaker detection)
- Custom vocabulary support
- AI-powered transcript cleanup using Google's Gemini
- Debug logging
- Configurable settings

## System Requirements

- Python 3.8 or higher
- FFmpeg (for audio processing)
- Working microphone (for real-time transcription)
- Internet connection

## Installation

### 1. Install FFmpeg

FFmpeg is required for audio processing. Install it based on your operating system:

#### Windows
```bash
winget install FFmpeg
```
or download from [FFmpeg website](https://ffmpeg.org/download.html)

#### macOS
```bash
brew install ffmpeg
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# Fedora
sudo dnf install ffmpeg

# Arch Linux
sudo pacman -S ffmpeg
```

### 2. Python Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Create and activate a virtual environment:
```bash
# Create virtual environment
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on macOS/Linux
source venv/bin/activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

### 3. API Keys Setup

The application requires two API keys:

#### AssemblyAI API Key
1. Sign up at [AssemblyAI](https://www.assemblyai.com/dashboard/signup)
2. Get your API key from the dashboard
3. Free tier includes 5 hours of audio processing per month

#### Google Gemini API Key
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Free tier available with usage limits

### 4. Configure API Keys

You can set up the API keys in two ways:

#### Option 1: Environment File
Create a `.env` file in the project root directory:
```plaintext
ASSEMBLY_API_KEY=your_assembly_ai_key_here
GOOGLE_API_KEY=your_google_gemini_key_here
```

#### Option 2: Settings Dialog
1. Launch the application
2. Click the "Settings" button
3. Enter your API keys in the respective fields (if not already entered in the .env file)
4. Enter location for output files (e.g. C:\Users\YourUsername\Documents\TranscriptionApp)
5. Click "Save"

## Usage

1. Start the application:
```bash
python main.py
```

2. Real-time Transcription:
   - Enter a session name (optional, if none entered, the current date and time will be used)
   - Select language and enable speaker detection if needed
   - Click "Start Recording"
   - Speak into your microphone
   - Click "Stop Recording" when finished

3. File Upload Transcription:
   - Click "Upload Audio"
   - Select an audio file (supported formats: mp3, wav, m4a, ogg)
   - Or select a video file (supported formats: mp4, mov, avi, mkv, webm)
   - Wait for transcription to complete

4. Additional Features:
   - Enable speaker diarization for multiple speakers
   - Select from multiple supported languages
   - Add custom vocabulary for better recognition
   - Use "AI Clean Up" for improved readability (change the prompt in the settings)

## Supported Languages

- Global English (en)
- US English (en_us)
- British English (en_uk)
- Australian English (en_au)
- Spanish (es)
- French (fr)
- German (de)
- Italian (it)
- Portuguese (pt)
- Dutch (nl)
- Hindi (hi)
- Japanese (ja)
- Chinese (zh)
- Finnish (fi)
- Korean (ko)
- Polish (pl)
- Russian (ru)
- Turkish (tr)
- Ukrainian (uk)
- Vietnamese (vi)

## Troubleshooting

1. Audio Issues:
   - Ensure FFmpeg is properly installed and accessible from command line
   - Check your microphone is properly connected and set as default input device
   - Verify microphone permissions are enabled for the application

2. API Key Issues:
   - Verify API keys are correctly entered in settings (in the UI) or .env file
   - Check API key validity and usage limits
   - Ensure internet connection is active

3. File Processing Issues:
   - Ensure file format is supported
   - Check file is not corrupted
   - Verify sufficient disk space for temporary files

4. Debug Logging:
   - Check the debug log panel in the application for detailed error messages
   - Logs are displayed in real-time during operation

## Dependencies

Key Python packages (automatically installed via requirements.txt):
- PyQt6 - GUI framework
- sounddevice - Audio recording
- assemblyai - Transcription service
- google-generativeai - AI cleanup
- pydub - Audio processing
- python-dotenv - Environment configuration
- numpy - Numerical processing
- wave - Audio file handling
- appdirs - Application directories

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.


