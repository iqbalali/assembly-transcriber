import sys
import os
import json
import appdirs
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QFileDialog,
    QGroupBox, QScrollArea, QFrame, QDialog, QDialogButtonBox,
    QSplitter, QMessageBox, QComboBox, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
import sounddevice as sd
import numpy as np
import wave
import assemblyai as aai
import google.generativeai as genai
from pydub import AudioSegment
import time

# Define default settings
def cleanup_prompt(transcript=""):
    return f"""Clean up a transcript to enhance readability and coherence.

    Focus on removing filler words, correcting grammatical errors, and maintaining the original meaning while ensuring the text flows smoothly.

    # Steps

    1. **Remove Filler Words:** Identify common filler words such as "um," "uh," "like," and "you know," and remove them from the transcript.
    
    2. **Correct Grammatical Errors:** Identify and fix any grammatical errors, such as subject-verb agreement and punctuation mistakes.

    3. **Enhance Readability:** Restructure sentences where needed to improve clarity and coherence, ensuring the text flows logically from one point to the next.

    4. **Preserve Core Meaning:** While editing, make sure to maintain the original meaning and intent of the transcript.

    5. Maintain the original tone of voice and perspective.

    6. Suggest improvements to the transcript.

  7. Apply suggested improvements in a finalised edited version


    # Notes

    - Avoid removing any essential information that could alter the meaning of the transcript.
    - Pay attention to the context to ensure continuity and coherence in the conversation.

    # Example output

    %CLEANED UP
   [Provide a clean, edited transcript, formatted as a coherent paragraph or series of paragraphs. Use section headings as appropriate to separate to clarify meaning]

    %SUGGESTIONS FOR IMPROVEMENT
    [Critique the transcript and suggest improvements]

    %SUGGESTED FINAL
[review suggested improvements and apply into this edited version]

    Transcript:
    {transcript}"""

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Settings")
        
        # Set up config directory and file
        self.config_dir = appdirs.user_config_dir("TranscribeApp")
        self.config_file = os.path.join(self.config_dir, "settings.json")
        
        # Ensure config directory exists
        os.makedirs(self.config_dir, exist_ok=True)
        
        print(f"Using config file: {self.config_file}")  # Debug print
        
        self.setup_ui()
        self.load_settings()

    def load_settings(self):
        """Load settings from JSON file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    settings = json.load(f)
                    
                print("Loading settings from:", self.config_file)
                
                # Set values in UI
                self.assembly_key.setText(settings.get('ASSEMBLY_API_KEY', ''))
                self.gemini_key.setText(settings.get('GOOGLE_API_KEY', ''))
                self.dir_entry.setText(settings.get('OUTPUT_DIR', os.path.join(os.path.expanduser("~"), "Documents", "Transcriptions")))
                self.prompt_text.setPlainText(settings.get('CLEANUP_PROMPT', cleanup_prompt()))
                
                # Set model selection, default to gemini-1.5-flash
                model_name = settings.get('GEMINI_MODEL', 'gemini-1.5-flash')
                index = self.model_combo.findText(model_name)
                if index >= 0:
                    self.model_combo.setCurrentIndex(index)
                
                # Load custom vocabulary
                vocab_list = settings.get('CUSTOM_VOCABULARY', [])
                if vocab_list:
                    self.vocab_entry.setText(', '.join(vocab_list))
                
                print("Settings loaded successfully")
            else:
                print("No existing settings file found, using defaults")
                # Set default output directory
                self.dir_entry.setText(os.path.join(os.path.expanduser("~"), "Documents", "Transcriptions"))
                # Set default cleanup prompt
                self.prompt_text.setPlainText(cleanup_prompt())
                # Model defaults to first item (gemini-1.5-flash)
                
        except Exception as e:
            print(f"Error loading settings: {e}")
            QMessageBox.warning(self, "Warning", "Could not load settings. Using defaults.")

    def save_settings(self):
        """Save settings to JSON file"""
        try:
            # Collect settings
            settings = {
                'ASSEMBLY_API_KEY': self.assembly_key.text().strip(),
                'GOOGLE_API_KEY': self.gemini_key.text().strip(),
                'OUTPUT_DIR': self.dir_entry.text().strip(),
                'CLEANUP_PROMPT': self.prompt_text.toPlainText().strip(),
                'GEMINI_MODEL': self.model_combo.currentText()
            }
            
            # Save to JSON file
            with open(self.config_file, 'w') as f:
                json.dump(settings, f, indent=4)
            
            print(f"Settings saved to: {self.config_file}")
            
            # Update parent's settings
            if self.parent:
                self.parent.assembly_api_key = settings['ASSEMBLY_API_KEY']
                self.parent.gemini_api_key = settings['GOOGLE_API_KEY']
                self.parent.output_dir = settings['OUTPUT_DIR']
                self.parent.cleanup_prompt = settings['CLEANUP_PROMPT']
                self.parent.gemini_model = settings['GEMINI_MODEL']
            
            QMessageBox.information(self, "Success", "Settings saved successfully!")
            self.accept()
            
        except Exception as e:
            error_msg = f"Failed to save settings: {str(e)}"
            print(f"Error: {error_msg}")
            QMessageBox.critical(self, "Error", error_msg)

    def setup_ui(self):
        """Setup the settings dialog UI"""
        layout = QVBoxLayout(self)
        
        # API Keys group
        api_group = QGroupBox("API Keys")
        api_layout = QVBoxLayout()
        
        # AssemblyAI Key
        assembly_layout = QHBoxLayout()
        assembly_label = QLabel("AssemblyAI API Key:")
        self.assembly_key = QLineEdit()
        self.assembly_key.setEchoMode(QLineEdit.EchoMode.Password)
        show_assembly = QPushButton("Show")
        show_assembly.clicked.connect(lambda: self.toggle_password_visibility(self.assembly_key, show_assembly))
        assembly_layout.addWidget(assembly_label)
        assembly_layout.addWidget(self.assembly_key)
        assembly_layout.addWidget(show_assembly)
        
        # Gemini Key
        gemini_layout = QHBoxLayout()
        gemini_label = QLabel("Gemini API Key:")
        self.gemini_key = QLineEdit()
        self.gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        show_gemini = QPushButton("Show")
        show_gemini.clicked.connect(lambda: self.toggle_password_visibility(self.gemini_key, show_gemini))
        gemini_layout.addWidget(gemini_label)
        gemini_layout.addWidget(self.gemini_key)
        gemini_layout.addWidget(show_gemini)
        
        api_layout.addLayout(assembly_layout)
        api_layout.addLayout(gemini_layout)
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)

        # Model Selection group
        model_group = QGroupBox("Model Selection")
        model_layout = QVBoxLayout()
        
        model_label = QLabel("Select Gemini Model:")
        self.model_combo = QComboBox()
        
        # Fetch available models
        if self.parent:
            available_models = self.parent.fetch_available_models()
            self.model_combo.addItems(available_models)
        else:
            self.model_combo.addItems(["gemini-1.5-pro", "gemini-1.5-flash"])
        
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        # Output Directory group
        output_group = QGroupBox("Output Directory")
        output_layout = QHBoxLayout()
        
        dir_label = QLabel("Save files to:")
        self.dir_entry = QLineEdit()
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.select_directory)
        
        output_layout.addWidget(dir_label)
        output_layout.addWidget(self.dir_entry)
        output_layout.addWidget(browse_button)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        # Cleanup Prompt group
        prompt_group = QGroupBox("Cleanup/Summary Settings")
        prompt_layout = QVBoxLayout()
        
        prompt_label = QLabel("Prompt template for generating summaries:")
        self.prompt_text = QTextEdit()
        self.prompt_text.setMinimumHeight(150)
        
        # Add reset button
        reset_prompt_button = QPushButton("Reset to Default")
        reset_prompt_button.clicked.connect(self.reset_prompt_to_default)
        
        prompt_layout.addWidget(prompt_label)
        prompt_layout.addWidget(self.prompt_text)
        prompt_layout.addWidget(reset_prompt_button)  # Add the reset button
        prompt_group.setLayout(prompt_layout)
        layout.addWidget(prompt_group)

        # Add standard dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Set dialog size
        self.resize(600, 500)

    def toggle_password_visibility(self, line_edit, button):
        """Toggle password visibility"""
        if line_edit.echoMode() == QLineEdit.EchoMode.Password:
            line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            button.setText("Hide")
        else:
            line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            button.setText("Show")

    def select_directory(self):
        """Open directory selection dialog"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            self.dir_entry.text() or os.path.expanduser("~"),
            QFileDialog.Option.ShowDirsOnly
        )
        if dir_path:
            self.dir_entry.setText(dir_path)
            # Create directory if it doesn't exist
            os.makedirs(dir_path, exist_ok=True)

    def reset_prompt_to_default(self):
        """Reset the prompt text to the default value"""
        self.prompt_text.setPlainText(cleanup_prompt(""))
        QMessageBox.information(self, "Success", "Prompt reset to default template")

    def fetch_available_models(self):
        """Fetch available models from Google API"""
        try:
            if not self.gemini_api_key:
                self.log_debug("No API key set, using default models")
                return ["gemini-1.5-pro", "gemini-1.5-flash"]  # Default fallback
            
            self.log_debug("Fetching available models from Google API...")
            genai.configure(api_key=self.gemini_api_key)
            models = genai.list_models()
            
            # Filter for Gemini models
            gemini_models = [model.name.split('/')[-1] for model in models if 'gemini' in model.name.lower()]
            
            self.log_debug(f"Available models: {gemini_models}")
            return gemini_models if gemini_models else ["gemini-1.5-pro", "gemini-1.5-flash"]
            
        except Exception as e:
            self.log_debug(f"Error fetching models: {e}")
            return ["gemini-1.5-pro", "gemini-1.5-flash"]  # Fallback to defaults

class RecordingThread(QThread):
    transcript_received = pyqtSignal(object)
    error_occurred = pyqtSignal(str)
    recording_stopped = pyqtSignal()

    def __init__(self, api_key):
        super().__init__()
        print("RecordingThread initialized")
        self.api_key = api_key
        self.is_recording = False
        self.transcriber = None
        self.microphone_stream = None

    def run(self):
        """Main recording loop"""
        print("RecordingThread.run() started")
        try:
            # Initialize AssemblyAI
            print("Setting up AssemblyAI...")
            aai.settings.api_key = self.api_key
            
            print("Creating transcriber...")
            self.transcriber = aai.RealtimeTranscriber(
                on_data=self._on_data,
                on_error=self._on_error,
                sample_rate=44100,
                end_utterance_silence_threshold=700
            )

            print("Connecting to AssemblyAI...")
            self.transcriber.connect()
            
            print("Initializing microphone...")
            self.microphone_stream = aai.extras.MicrophoneStream(
                sample_rate=44100
            )
            
            print("Starting audio stream...")
            self.is_recording = True
            self.transcriber.stream(self.microphone_stream)
            
        except Exception as e:
            print(f"Error in recording thread: {e}")
            self.error_occurred.emit(str(e))
            import traceback
            traceback.print_exc()
        finally:
            print("RecordingThread.run() ending")
            self.cleanup()

    def _on_data(self, transcript):
        """Handle incoming transcripts"""
        try:
            print(f"Received transcript: {transcript.text}")
            self.transcript_received.emit(transcript)
        except RuntimeError:
            # Suppress RuntimeError from thread issues
            pass
        except Exception as e:
            print(f"Error in _on_data: {e}")
            self.error_occurred.emit(str(e))

    def _on_error(self, error):
        """Handle errors"""
        print(f"Transcription error: {error}")
        self.error_occurred.emit(str(error))

    def cleanup(self):
        """Clean up resources"""
        print("Starting cleanup...")
        try:
            self.is_recording = False
            
            if self.transcriber:
                print("Closing transcriber...")
                self.transcriber.close()
                self.transcriber = None
            
            if self.microphone_stream:
                print("Closing microphone stream...")
                self.microphone_stream.close()
                self.microphone_stream = None
                
            print("Cleanup complete")
            self.recording_stopped.emit()
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
            self.error_occurred.emit(str(e))

    def requestStop(self):
        """Request the thread to stop"""
        print("Stop requested")
        self.is_recording = False
        if self.transcriber:
            self.transcriber.close()

class TranscriberApp(QMainWindow):
    def __init__(self):
        try:
            super().__init__()
            print("Initializing TranscriberApp...")
            
            self.setWindowTitle("TranscribeApp")
            self.setGeometry(100, 100, 800, 600)  # Set window size and position
            
            # Set up config paths
            self.config_dir = appdirs.user_config_dir("TranscribeApp")
            print(f"Config directory: {self.config_dir}")
            self.config_file = os.path.join(self.config_dir, "settings.json")
            print(f"Config file: {self.config_file}")
            
            # Initialize settings with defaults
            self.assembly_api_key = ''
            self.gemini_api_key = ''
            self.output_dir = os.path.join(os.path.expanduser("~"), "Documents", "Transcriptions")
            self.cleanup_prompt = cleanup_prompt()
            
            # Initialize other variables
            self.recording_thread = None
            self.current_output_file = None
            
            print("Loading settings...")
            self.load_settings()
            
            print("Setting up UI...")
            self.setup_ui()
            print("UI setup complete")
            
            # Show settings dialog if no API keys
            if not self.assembly_api_key or not self.gemini_api_key:
                print("No API keys found, showing settings dialog...")
                self.show_settings()
                
            print("TranscriberApp initialization complete")
            
        except Exception as e:
            print(f"Error initializing TranscriberApp: {e}")
            import traceback
            traceback.print_exc()
            raise

    def load_settings(self):
        """Load settings from JSON file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    settings = json.load(f)
                
                self.assembly_api_key = settings.get('ASSEMBLY_API_KEY', '')
                self.gemini_api_key = settings.get('GOOGLE_API_KEY', '')
                self.output_dir = settings.get('OUTPUT_DIR', os.path.join(os.path.expanduser("~"), "Documents", "Transcriptions"))
                self.cleanup_prompt = settings.get('CLEANUP_PROMPT', cleanup_prompt)
                self.gemini_model = settings.get('GEMINI_MODEL', 'gemini-1.5-flash')
                
                # Load custom vocabulary
                vocab_list = settings.get('CUSTOM_VOCABULARY', [])
                if vocab_list:
                    self.vocab_entry.setText(', '.join(vocab_list))
                
                print("Settings loaded successfully")
            else:
                print("No existing settings file found, using defaults")
                # Ensure output directory exists
                os.makedirs(self.output_dir, exist_ok=True)
                
        except Exception as e:
            print(f"Error loading settings: {e}")
            # Use defaults on error
            self.assembly_api_key = ''
            self.gemini_api_key = ''
            self.output_dir = os.path.join(os.path.expanduser("~"), "Documents", "Transcriptions")
            self.cleanup_prompt = cleanup_prompt()
            self.gemini_model = 'gemini-1.5-flash'
            # Ensure output directory exists
            os.makedirs(self.output_dir, exist_ok=True)

    def setup_ui(self):
        """Setup the UI components"""
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create input section
        input_group = QGroupBox("Recording Settings")
        input_layout = QVBoxLayout(input_group)

        # Name input
        name_layout = QHBoxLayout()
        name_label = QLabel("Session Name:")
        self.name_entry = QLineEdit()
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_entry)
        input_layout.addLayout(name_layout)

        # Add output directory display label
        self.output_dir_label = QLabel()
        self.output_dir_label.setWordWrap(True)
        self.output_dir_label.setStyleSheet("color: #666666; font-size: 10pt;")
        input_layout.addWidget(self.output_dir_label)
        
        # Connect session name change to update output path
        self.name_entry.textChanged.connect(self.update_output_path_display)
        
        # Initial update of output path
        self.update_output_path_display()

        # Add input group to main layout
        main_layout.addWidget(input_group)

        # Custom Vocabulary section (between Recording Settings and transcript)
        vocab_group = QGroupBox("Additional features")
        vocab_layout = QVBoxLayout()
        
        # Language and speakers layout
        features_layout = QHBoxLayout()
        
        # Language selection
        language_layout = QHBoxLayout()
        language_label = QLabel("Language:")
        self.language_combo = QComboBox()
        self.language_combo.addItems([
            "Global English (en)",
            "US English (en_us)", 
            "British English (en_uk)",
            "Australian English (en_au)",
            "Spanish (es)",
            "French (fr)",
            "German (de)",
            "Italian (it)",
            "Portuguese (pt)",
            "Dutch (nl)",
            "Hindi (hi)",
            "Japanese (ja)",
            "Chinese (zh)",
            "Finnish (fi)",
            "Korean (ko)",
            "Polish (pl)",
            "Russian (ru)",
            "Turkish (tr)",
            "Ukrainian (uk)",
            "Vietnamese (vi)"
        ])
        self.language_combo.setCurrentText("Global English (en)")
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.language_combo)
        features_layout.addLayout(language_layout)

        # Multiple speakers checkbox
        self.multiple_speakers_cb = QCheckBox("Detect Multiple Speakers")
        self.multiple_speakers_cb.setToolTip("Enable speaker diarization to identify different speakers")
        features_layout.addWidget(self.multiple_speakers_cb)
        
        # Add stretch to keep items left-aligned
        features_layout.addStretch()
        
        # Add features layout to vocab group
        vocab_layout.addLayout(features_layout)
        
        # Add vocabulary help text and entry
        vocab_help = QLabel("Enter technical terms or proper nouns (comma-separated) to improve recognition:")
        vocab_help.setWordWrap(True)
        vocab_help.setStyleSheet("color: #666666; font-size: 10pt;")
        
        self.vocab_entry = QLineEdit()
        self.vocab_entry.setPlaceholderText("Example: PyQt6, JSON, API endpoint, AssemblyAI")
        
        vocab_layout.addWidget(vocab_help)
        vocab_layout.addWidget(self.vocab_entry)
        vocab_group.setLayout(vocab_layout)
        main_layout.addWidget(vocab_group)

        # Button section
        button_layout = QHBoxLayout()
        
        # Create buttons
        self.record_button = QPushButton("Start Recording")
        self.upload_button = QPushButton("Upload Audio")
        self.summarize_button = QPushButton("AI Clean Up")
        self.settings_button = QPushButton("Settings")
        
        # Connect button signals
        self.record_button.clicked.connect(self.toggle_recording)
        self.upload_button.clicked.connect(self.upload_audio)
        self.summarize_button.clicked.connect(self.create_summary)
        self.settings_button.clicked.connect(self.show_settings)
        
        # Style the action buttons
        for button in [self.record_button, self.upload_button]:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #0d6efd;
                    color: white;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #0b5ed7;
                }
                QPushButton:pressed {
                    background-color: #0a58ca;
                }
                QPushButton:disabled {
                    background-color: #6c757d;
                }
            """)
        
        # Set initial button states
        self.summarize_button.setEnabled(False)
        
        # Add buttons to layout
        button_layout.addWidget(self.record_button)
        button_layout.addWidget(self.upload_button)
        button_layout.addWidget(self.summarize_button)
        button_layout.addWidget(self.settings_button)
        
        # Add button layout to main layout
        main_layout.addLayout(button_layout)

        # Create splitter for transcript and debug
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Transcript section
        transcript_group = QGroupBox("Transcript")
        transcript_layout = QVBoxLayout(transcript_group)
        self.transcript_display = QTextEdit()
        self.transcript_display.setReadOnly(True)
        transcript_layout.addWidget(self.transcript_display)
        splitter.addWidget(transcript_group)
        
        # Debug section
        debug_group = QGroupBox("Debug Log")
        debug_layout = QVBoxLayout(debug_group)
        self.debug_display = QTextEdit()
        self.debug_display.setReadOnly(True)
        debug_layout.addWidget(self.debug_display)
        splitter.addWidget(debug_group)
        
        # Set splitter sizes
        splitter.setSizes([300, 100])
        
        # Add splitter to main layout
        main_layout.addWidget(splitter)
        
        # Create status bar
        self.statusBar().showMessage("Ready")

    def toggle_recording(self):
        """Toggle recording state"""
        if self.record_button.text() == "Start Recording":
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        """Start recording with proper setup"""
        print("\n=== Starting Recording ===")
        self.log_debug("Starting recording...")
        
        try:
            if not self.validate_api_keys():
                return
            
            # Update UI immediately
            self.record_button.setText("Stop Recording")
            self.record_button.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #bb2d3b;
                }
                QPushButton:pressed {
                    background-color: #a52834;
                }
            """)
            self.upload_button.setEnabled(False)
            self.summarize_button.setEnabled(False)
            self.statusBar().showMessage("Initializing recording...")
            
            # Get session name and create session directory
            session_name = self.name_entry.text().strip()
            if not session_name:
                session_name = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            session_dir = os.path.join(self.output_dir, session_name)
            os.makedirs(session_dir, exist_ok=True)
            
            output_file = os.path.join(
                session_dir,
                "transcript.txt"
            )
            
            # Create new recording thread with updated configuration
            self.recording_thread = RecordingThread(self.assembly_api_key)
            
            # Configure transcription settings
            config = {
                "speaker_labels": self.multiple_speakers_cb.isChecked(),
                "language_code": self.language_combo.currentText().lower()
            }
            self.recording_thread.transcriber_config = config
            
            # Connect signals
            self.recording_thread.transcript_received.connect(self.handle_transcript)
            self.recording_thread.error_occurred.connect(self.handle_recording_error)
            self.recording_thread.recording_stopped.connect(self.update_ui_recording_stopped)
            self.recording_thread.finished.connect(self.handle_thread_finished)
            
            # Store output file
            self.current_output_file = output_file
            
            # Start thread
            self.recording_thread.start()
            
        except Exception as e:
            print(f"Error starting recording: {e}")
            self.log_debug(f"Error starting recording: {e}")
            self.statusBar().showMessage(f"Error: {str(e)}")
            self.update_ui_recording_stopped()

    def stop_recording(self):
        """Stop recording"""
        # Update UI immediately
        self.record_button.setEnabled(False)
        self.record_button.setText("Please wait...")
        self.statusBar().showMessage("Stopping recording (this may take a few seconds)...")
        
        # Now proceed with the actual stopping logic
        self.log_debug("Stopping recording...")
        
        try:
            if self.recording_thread and self.recording_thread.isRunning():
                self.recording_thread.requestStop()
                
                # Wait with timeout
                if not self.recording_thread.wait(5000):  # 5 second timeout
                    self.log_debug("Force stopping thread...")
                    self.recording_thread.terminate()
                    self.recording_thread.wait()
            
        except Exception as e:
            self.log_debug(f"Error stopping recording: {e}")
            self.statusBar().showMessage(f"Error: {str(e)}")
        finally:
            self.update_ui_recording_stopped()

    def handle_transcript(self, transcript):
        """Handle incoming transcript"""
        if not transcript.text:
            return
        
        if isinstance(transcript, aai.RealtimeFinalTranscript):
            # For final transcripts, save to file and display
            text = f"{transcript.text}\n"
            with open(self.current_output_file, "a") as f:
                f.write(text)
            self.transcript_display.append(text)
            self.log_debug(f"Saved transcript: {len(text)} chars")
        else:
            # For partial transcripts, just display
            print(f"{transcript.text}")

    def update_ui_recording_stopped(self):
        """Update UI when recording is stopped"""
        self.record_button.setEnabled(True)
        self.record_button.setText("Start Recording")
        self.record_button.setStyleSheet("""
            QPushButton {
                background-color: #0d6efd;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
            QPushButton:pressed {
                background-color: #0a58ca;
            }
        """)
        self.upload_button.setEnabled(True)
        self.summarize_button.setEnabled(True)
        self.statusBar().showMessage("Recording stopped")

    def handle_thread_finished(self):
        """Handle thread completion"""
        self.log_debug("Recording thread finished")
        if self.recording_thread:
            self.recording_thread.deleteLater()
            self.recording_thread = None
        self.update_ui_recording_stopped()

    def handle_recording_error(self, error_msg):
        """Handle recording errors"""
        self.log_debug(f"Recording error: {error_msg}")
        self.statusBar().showMessage(f"Error: {error_msg}")
        self.stop_recording()

    def create_summary(self):
        """Create summary of transcription"""
        self.log_debug("Creating summary...")
        self.statusBar().showMessage("Creating summary...")
        
        try:
            if not self.current_output_file or not os.path.exists(self.current_output_file):
                raise Exception("No transcription file available")
            
            # Read the transcription file
            with open(self.current_output_file, 'r') as f:
                transcript = f.read()
            
            if not transcript.strip():
                raise Exception("Transcription file is empty")
            
            # Initialize Gemini
            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel(self.gemini_model)
            
            # Create summary prompt using the cleanup_prompt function
            prompt = cleanup_prompt(transcript)
            
            # Generate summary
            response = model.generate_content(prompt)
            summary = response.text
            
            # Add separator and summary to transcript display
            self.transcript_display.append("\n" + "="*50 + "\n")
            self.transcript_display.append("SUMMARY:\n")
            self.transcript_display.append(summary)
            self.transcript_display.append("\n" + "="*50 + "\n")
            
            # Save summary
            summary_file = self.current_output_file.replace('.txt', '_summary.txt')
            with open(summary_file, 'w') as f:
                f.write(summary)
            
            self.log_debug(f"Summary saved to: {summary_file}")
            self.statusBar().showMessage("Summary created successfully")
            
        except Exception as e:
            error_msg = f"Error creating summary: {e}"
            self.log_debug(error_msg)
            self.statusBar().showMessage(error_msg)

    def validate_api_keys(self):
        """Validate that API keys are present"""
        return bool(self.assembly_api_key and self.gemini_api_key)

    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            self.load_settings()  # Reload settings after dialog is accepted
            self.update_output_path_display()  # Update the path display with new output directory
            if self.validate_api_keys():
                self.log_debug("Settings updated successfully")
                self.statusBar().showMessage("Settings updated successfully", 3000)
            else:
                self.log_debug("Warning: Invalid or missing API keys after update")
                self.statusBar().showMessage("Warning: Invalid or missing API keys", 3000)

    def log_debug(self, message):
        """Add debug logging method if it's missing"""
        print(f"DEBUG: {message}")
        if hasattr(self, 'debug_display'):
            self.debug_display.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def update_output_path_display(self):
        """Update the displayed output directory path"""
        session_name = self.name_entry.text().strip()
        if session_name:
            full_path = os.path.join(self.output_dir, session_name)
        else:
            full_path = os.path.join(self.output_dir, f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        self.output_dir_label.setText(f"Output directory: {full_path}")

    def closeEvent(self, event):
        """Handle application closing"""
        try:
            # Get current settings
            settings = {
                'ASSEMBLY_API_KEY': self.assembly_api_key,
                'GOOGLE_API_KEY': self.gemini_api_key,
                'OUTPUT_DIR': self.output_dir,
                'CLEANUP_PROMPT': self.cleanup_prompt,
                'GEMINI_MODEL': self.gemini_model,
                'SPEAKERS_EXPECTED': self.speakers_expected,
                'CUSTOM_VOCABULARY': [word.strip() for word in self.vocab_entry.text().split(',') if word.strip()]
            }
            
            # Save to file
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(settings, f, indent=4)
            
            print("Settings saved successfully")
            
        except Exception as e:
            print(f"Error saving settings: {e}")
        finally:
            event.accept()

    def get_custom_vocabulary(self):
        """Get custom vocabulary as a list"""
        vocab_text = self.vocab_entry.text().strip()
        if not vocab_text:
            return []
        return [word.strip() for word in vocab_text.split(',') if word.strip()]

    def fetch_available_models(self):
        """Fetch available models from Google API"""
        try:
            if not self.gemini_api_key:
                self.log_debug("No API key set, using default models")
                return ["gemini-1.5-pro", "gemini-1.5-flash"]  # Default fallback
            
            self.log_debug("Fetching available models from Google API...")
            genai.configure(api_key=self.gemini_api_key)
            models = genai.list_models()
            
            # Filter for Gemini models
            gemini_models = [model.name.split('/')[-1] for model in models if 'gemini' in model.name.lower()]
            
            self.log_debug(f"Available models: {gemini_models}")
            return gemini_models if gemini_models else ["gemini-1.5-pro", "gemini-1.5-flash"]
            
        except Exception as e:
            self.log_debug(f"Error fetching models: {e}")
            return ["gemini-1.5-pro", "gemini-1.5-flash"]  # Fallback to defaults

    def upload_audio(self):
        """Handle audio/video file upload and transcription"""
        try:
            if not self.validate_api_keys():
                return

            # Open file dialog for audio/video selection
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Audio/Video File",
                "",
                "Media Files (*.mp3 *.wav *.m4a *.ogg *.mp4 *.mov *.avi *.mkv *.webm *.flv);;All Files (*.*)"
            )

            if not file_path:
                return

            # Get file extension
            file_ext = os.path.splitext(file_path)[1].lower()
            video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv'}
            
            # Path for temporary audio file
            temp_audio_path = None

            try:
                # If it's a video file, extract audio
                if file_ext in video_extensions:
                    self.statusBar().showMessage("Extracting audio from video...")
                    self.log_debug("Extracting audio from video file...")

                    # Create _temp directory if it doesn't exist
                    temp_dir = os.path.join(self.output_dir, "_temp")
                    os.makedirs(temp_dir, exist_ok=True)

                    # Generate temp audio file path
                    temp_audio_path = os.path.join(
                        temp_dir,
                        f"temp_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
                    )

                    # Extract audio using pydub
                    audio = AudioSegment.from_file(file_path)
                    audio.export(temp_audio_path, format="mp3")

                    # Use the temporary audio file for transcription
                    file_to_transcribe = temp_audio_path
                else:
                    file_to_transcribe = file_path

                # Get session name or create one from file name
                session_name = self.name_entry.text().strip()
                if not session_name:
                    session_name = os.path.splitext(os.path.basename(file_path))[0]
                    self.name_entry.setText(session_name)

                # Create session directory
                session_dir = os.path.join(self.output_dir, session_name)
                os.makedirs(session_dir, exist_ok=True)

                # Set up output file path
                self.current_output_file = os.path.join(session_dir, "transcript.txt")

                # Update UI
                self.statusBar().showMessage("Transcribing media file...")
                self.record_button.setEnabled(False)
                self.upload_button.setEnabled(False)
                self.summarize_button.setEnabled(False)

                # Initialize AssemblyAI
                aai.settings.api_key = self.assembly_api_key
                
                # Get language code from combo box
                selected_language = self.language_combo.currentText()
                language_code = selected_language.split('(')[-1].strip(')')
                
                # Configure transcription options
                config = aai.TranscriptionConfig(
                    speaker_labels=self.multiple_speakers_cb.isChecked(),
                    language_code=language_code  # Use the extracted language code
                )
                
                # Create transcriber and start transcription
                self.log_debug("Creating transcriber for file upload...")
                transcriber = aai.Transcriber()
                
                # Start transcription and wait for completion
                transcript = transcriber.transcribe(file_to_transcribe, config=config)

                # Process the completed transcript
                if self.multiple_speakers_cb.isChecked():
                    formatted_text = ""
                    for utterance in transcript.utterances:
                        formatted_text += f"Speaker {utterance.speaker}: {utterance.text}\n\n"
                    with open(self.current_output_file, 'w') as f:
                        f.write(formatted_text)
                    self.transcript_display.setText(formatted_text)
                else:
                    # Save regular transcript
                    with open(self.current_output_file, 'w') as f:
                        f.write(transcript.text)
                    self.transcript_display.setText(transcript.text)
                
                self.log_debug("Transcription processing completed")
                self.statusBar().showMessage("Transcription completed successfully")
                
            except Exception as e:
                error_msg = f"Error processing media file: {e}"
                self.log_debug(error_msg)
                self.statusBar().showMessage(error_msg)
                
            finally:
                # Re-enable buttons
                self.record_button.setEnabled(True)
                self.upload_button.setEnabled(True)
                self.summarize_button.setEnabled(True)
                
                # Clean up temp file if it exists
                if temp_audio_path and os.path.exists(temp_audio_path):
                    try:
                        os.remove(temp_audio_path)
                    except Exception as e:
                        self.log_debug(f"Error removing temp file: {e}")

        except Exception as e:
            error_msg = f"Error processing media file: {e}"
            self.log_debug(error_msg)
            self.statusBar().showMessage(error_msg)
            self.record_button.setEnabled(True)
            self.upload_button.setEnabled(True)

def main():
    try:
        print("Starting application...")
        app = QApplication(sys.argv)
        print("QApplication created")
        
        window = TranscriberApp()
        print("TranscriberApp window created")
        
        window.show()
        print("Window shown")
        
        print("Starting mainloop...")
        return app.exec()
        
    except Exception as e:
        print(f"Error in main: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 