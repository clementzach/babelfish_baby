/**
 * Audio recording functionality using Web Audio API
 */

let mediaRecorder = null;
let audioChunks = [];
let recordingStartTime = null;
let timerInterval = null;
let stream = null;

const MAX_DURATION_SECONDS = 60;

const recordButton = document.getElementById('recordButton');
const buttonText = document.getElementById('buttonText');
const timerEl = document.getElementById('timer');
const instructionsEl = document.getElementById('instructions');
const processingEl = document.getElementById('processing');

// Recording state
let isRecording = false;

// Initialize
recordButton.addEventListener('click', toggleRecording);

async function toggleRecording() {
    if (!isRecording) {
        await startRecording();
    } else {
        await stopRecording();
    }
}

async function startRecording() {
    try {
        // Request microphone access
        stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                sampleRate: 24000 // Request 24 kHz (may not be honored by all browsers)
            }
        });

        // Create MediaRecorder
        // Try different MIME types based on browser support
        let mimeType = 'audio/webm';
        if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
            mimeType = 'audio/webm;codecs=opus';
        } else if (MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')) {
            mimeType = 'audio/ogg;codecs=opus';
        } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
            mimeType = 'audio/mp4';
        }

        mediaRecorder = new MediaRecorder(stream, {
            mimeType: mimeType
        });

        audioChunks = [];

        mediaRecorder.addEventListener('dataavailable', (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        });

        mediaRecorder.addEventListener('stop', () => {
            handleRecordingComplete();
        });

        // Start recording
        mediaRecorder.start();
        isRecording = true;
        recordingStartTime = Date.now();

        // Update UI
        recordButton.classList.add('recording');
        buttonText.textContent = 'Stop Recording';
        instructionsEl.textContent = 'Recording... Click to stop (max 60 seconds)';
        timerEl.style.display = 'block';

        // Start timer
        updateTimer();
        timerInterval = setInterval(updateTimer, 100);

    } catch (error) {
        console.error('Error accessing microphone:', error);
        if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
            showNotification('Microphone permission denied. Please allow access and try again.', 'error');
        } else {
            showNotification('Failed to access microphone: ' + error.message, 'error');
        }
    }
}

async function stopRecording() {
    if (!mediaRecorder || !isRecording) return;

    isRecording = false;

    // Stop media recorder
    mediaRecorder.stop();

    // Stop all tracks
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }

    // Clear timer
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }

    // Update UI
    recordButton.classList.remove('recording');
    recordButton.disabled = true;
}

function updateTimer() {
    if (!isRecording || !recordingStartTime) return;

    const elapsed = (Date.now() - recordingStartTime) / 1000;
    const minutes = Math.floor(elapsed / 60);
    const seconds = Math.floor(elapsed % 60);

    timerEl.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

    // Auto-stop at max duration
    if (elapsed >= MAX_DURATION_SECONDS) {
        stopRecording();
        showNotification('Maximum recording duration reached (60 seconds)', 'info');
    }
}

async function handleRecordingComplete() {
    // Hide timer
    timerEl.style.display = 'none';

    // Check if recording is too short
    const duration = (Date.now() - recordingStartTime) / 1000;
    if (duration < 1) {
        showNotification('Recording too short. Please record at least 1 second.', 'error');
        resetUI();
        return;
    }

    // Show processing
    processingEl.style.display = 'block';
    instructionsEl.textContent = 'Processing your recording...';

    // Create blob from chunks
    const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType });

    // Upload to server
    try {
        await uploadRecording(audioBlob);
    } catch (error) {
        console.error('Upload failed:', error);
        showNotification('Failed to upload recording: ' + error.message, 'error');
        resetUI();
    }
}

async function uploadRecording(audioBlob) {
    // Create form data
    const formData = new FormData();

    // Convert blob to file
    const filename = `recording_${Date.now()}.webm`;
    const file = new File([audioBlob], filename, { type: audioBlob.type });
    formData.append('audio_file', file);

    // Add timestamp
    const now = new Date().toISOString();
    formData.append('recorded_at', now);

    // Upload
    const response = await fetch('/api/cries/record', {
        method: 'POST',
        body: formData
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
    }

    const result = await response.json();

    // Show success and redirect
    showNotification('Recording saved successfully!', 'success');

    setTimeout(() => {
        window.location.href = '/history';
    }, 1500);
}

function resetUI() {
    recordButton.classList.remove('recording');
    recordButton.disabled = false;
    buttonText.textContent = 'Start Recording';
    instructionsEl.textContent = 'Click the button below to start recording';
    processingEl.style.display = 'none';
    timerEl.style.display = 'none';
    timerEl.textContent = '00:00';
}

// Check for microphone support
if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    instructionsEl.textContent = 'Your browser does not support audio recording.';
    instructionsEl.style.color = 'red';
    recordButton.disabled = true;
}
