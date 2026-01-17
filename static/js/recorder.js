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
const photoSection = document.getElementById('photoSection');
const photoInput = document.getElementById('photoInput');
const photoPreview = document.getElementById('photoPreview');
const photoPreviewImage = document.getElementById('photoPreviewImage');
const uploadButton = document.getElementById('uploadButton');

// Recording state
let isRecording = false;

// Initialize
recordButton.addEventListener('click', toggleRecording);
photoInput.addEventListener('change', handlePhotoSelect);
uploadButton.addEventListener('click', handleUpload);

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

    // Create blob from chunks
    const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType });

    // Store audio blob globally for later upload
    window.recordedAudioBlob = audioBlob;

    // Show photo upload section
    instructionsEl.textContent = 'Recording complete! Optionally add a photo, then upload.';
    photoSection.style.display = 'block';
}

function handlePhotoSelect(event) {
    const file = event.target.files[0];
    if (!file) {
        photoPreview.style.display = 'none';
        return;
    }

    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
        showNotification('Please select a valid image file (JPEG, PNG, or WebP)', 'error');
        photoInput.value = '';
        return;
    }

    // Validate file size (10MB max)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
        showNotification('Photo file is too large (max 10MB)', 'error');
        photoInput.value = '';
        return;
    }

    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => {
        photoPreviewImage.src = e.target.result;
        photoPreview.style.display = 'block';
    };
    reader.readAsDataURL(file);
}

async function handleUpload() {
    if (!window.recordedAudioBlob) {
        showNotification('No recording found', 'error');
        return;
    }

    // Show processing
    uploadButton.disabled = true;
    processingEl.style.display = 'block';
    instructionsEl.textContent = 'Uploading your recording...';
    photoSection.style.display = 'none';

    try {
        await uploadRecording(window.recordedAudioBlob);
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

    // Add photo if selected
    if (photoInput.files && photoInput.files[0]) {
        formData.append('photo_file', photoInput.files[0]);
    }

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
    photoSection.style.display = 'none';
    photoInput.value = '';
    photoPreview.style.display = 'none';
    uploadButton.disabled = false;
    window.recordedAudioBlob = null;
}

// Check for microphone support
if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    instructionsEl.textContent = 'Your browser does not support audio recording.';
    instructionsEl.style.color = 'red';
    recordButton.disabled = true;
}
