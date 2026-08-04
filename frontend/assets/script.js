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

        // Disable UI controls during extraction
        setLoadingState(true);
        updateStatus('Connecting to server... Resolving media stream...');

        try {
            const response = await fetch('/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url: url, mode: mode })
            });

            const data = await response.json();

            if (!response.ok || data.error) {
                throw new Error(data.error || 'Failed to resolve download stream.');
            }

            if (data.download_url) {
                updateStatus('Stream found! Initiating download...', 'success');
                
                // Trigger browser download via direct URL redirection
                window.location.href = data.download_url;
            } else {
                throw new Error('No download URL returned from server.');
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
        
        // Reset classes
        statusBox.className = 'status-box';
        if (type === 'error') {
            statusBox.classList.add('status-error');
        } else if (type === 'success') {
            statusBox.classList.add('status-success');
        }
    }

    function setLoadingState(isLoading) {
        downloadBtn.disabled = isLoading;
        urlInput.disabled = isLoading;
        if (modeSelect) modeSelect.disabled = isLoading;
        
        downloadBtn.textContent = isLoading ? 'Processing...' : 'Download';
    }
});