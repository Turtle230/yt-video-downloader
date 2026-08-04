document.addEventListener('DOMContentLoaded', () => {
    const downloadBtn = document.getElementById('download-btn');
    const urlInput = document.getElementById('url-input');
    const modeSelect = document.getElementById('mode-select');
    const statusBox = document.getElementById('status-box');

    if (!downloadBtn || !urlInput) return;

    function normalizeUrl(url) {
        const match = url.match(/youtu\.be\/([a-zA-Z0-9_-]+)/);
        return match ? `https://www.youtube.com/watch?v=${match[1]}` : url;
    }

    downloadBtn.addEventListener('click', async () => {
        const rawUrl = urlInput.value.trim();
        const mode = modeSelect ? modeSelect.value : 'mp4';

        if (!rawUrl) {
            updateStatus('Please enter a valid YouTube URL.', 'error');
            return;
        }

        const targetUrl = normalizeUrl(rawUrl);
        const isAudio = mode === 'mp3' || mode === 'ogg';

        setLoadingState(true);
        updateStatus('Connecting to resolver...');

        const instances = [
            'https://api.cobalt.tools',
            'https://co.wuk.sh',
            'https://cobalt-api.kwiatekmons.com'
        ];

        const payload = {
            url: targetUrl,
            downloadMode: isAudio ? 'audio' : 'auto',
            audioFormat: isAudio ? mode : 'mp3',
            videoQuality: '720'
        };

        let resolved = false;

        for (const instance of instances) {
            try {
                updateStatus('Resolving stream...');

                const response = await fetch(`${instance}/`, {
                    method: 'POST',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });

                const data = await response.json();

                if (response.ok && data.url) {
                    updateStatus('Stream found! Initiating download...', 'success');

                    // Trigger direct browser download
                    window.location.href = data.url;
                    resolved = true;
                    break;
                }
            } catch (err) {
                console.warn(`Instance ${instance} failed:`, err);
            }
        }

        if (!resolved) {
            updateStatus('Error: Failed to resolve stream link.', 'error');
        }

        setLoadingState(false);
    });

    function updateStatus(message, type = 'info') {
        if (!statusBox) return;
        statusBox.textContent = message;

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