document.addEventListener('DOMContentLoaded', () => {
    const downloadBtn = document.getElementById('downloadBtn');
    const urlInput = document.getElementById('url');
    const modeSelect = document.getElementById('mode');
    const statusDiv = document.getElementById('status');

    let timerInterval = null;

    downloadBtn.addEventListener('click', handleDownload);

    async function handleDownload() {
        const url = urlInput.value.trim();
        const mode = modeSelect.value;

        if (!url) {
            updateStatus('Error: Please enter a YouTube URL.');
            return;
        }

        setFormState(true);
        startTimer();

        try {
            const response = await fetch('/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, mode })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `Server error (${response.status})`);
            }

            const blob = await response.blob();
            const filename = extractFilename(response, mode);
            triggerFileDownload(blob, filename);

            const totalTime = stopTimer();
            updateStatus(`Completed in ${totalTime}s! Ready.`);
        } catch (err) {
            stopTimer();
            updateStatus(`Error: ${err.message}`);
        } finally {
            setFormState(false);
        }
    }

    /* Helper Functions */

    function setFormState(disabled) {
        downloadBtn.disabled = disabled;
        urlInput.disabled = disabled;
        modeSelect.disabled = disabled;
    }

    function updateStatus(text) {
        statusDiv.textContent = text;
    }

    function startTimer() {
        let seconds = 0;
        updateStatus('Connecting to server (waking up instance)... 0s');

        timerInterval = setInterval(() => {
            seconds++;
            if (seconds < 15) {
                updateStatus(`Connecting to server (waking up instance)... ${seconds}s`);
            } else {
                updateStatus(`Processing & converting media... ${seconds}s`);
            }
        }, 1000);
    }

    function stopTimer() {
        if (!timerInterval) return 0;
        const elapsedText = statusDiv.textContent.match(/\d+/g);
        const finalSeconds = elapsedText ? elapsedText[elapsedText.length - 1] : 0;
        clearInterval(timerInterval);
        timerInterval = null;
        return finalSeconds;
    }

    function extractFilename(response, fallbackMode) {
        const header = response.headers.get('Content-Disposition');
        if (header && header.includes('filename=')) {
            return header.split('filename=')[1].replace(/["']/g, '');
        }
        return `download.${fallbackMode}`;
    }

    function triggerFileDownload(blob, filename) {
        const downloadUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(downloadUrl);
    }
});