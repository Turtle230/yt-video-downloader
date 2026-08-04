document.addEventListener('DOMContentLoaded', () => {
    const downloadBtn = document.getElementById('download-btn');
    const urlInput = document.getElementById('url-input');
    const modeSelect = document.getElementById('mode-select');
    const statusBox = document.getElementById('status-box');

    if (!downloadBtn || !urlInput) return;

    downloadBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        const mode = modeSelect ? modeSelect.value : 'mp4';

        if (!url) {
            updateStatus('Please enter a valid YouTube URL.', 'error');
            return;
        }

        setLoadingState(true);
        updateStatus('Extracting video stream...');

        try {
            const response = await fetch('/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url, mode })
            });

            const data = await response.json();

            if (!response.ok || data.error) {
                throw new Error(data.error || 'Server processing error.');
            }

            if (data.download_url) {
                updateStatus('Stream resolved! Downloading...', 'success');
                window.location.href = data.download_url;
            } else {
                throw new Error('No valid download URL returned.');
            }

        } catch (err) {
            console.error('Download error:', err);
            updateStatus(`Error: ${err.message}`, 'error');
        } finally {
            setLoadingState(false);
        }
    });

    function updateStatus(message, type = 'info') {
        if (!statusBox) return;
        statusBox.textContent = message;
        statusBox.className = 'status-box';
        if (type === 'error') statusBox.classList.add('status-error');
        if (type === 'success') statusBox.classList.add('status-success');
    }

    function setLoadingState(isLoading) {
        downloadBtn.disabled = isLoading;
        urlInput.disabled = isLoading;
        if (modeSelect) modeSelect.disabled = isLoading;
        downloadBtn.textContent = isLoading ? 'Processing...' : 'Download';
    }
});