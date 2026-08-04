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

        // Working public Cobalt API instances
        const instances = [
            'https://api.cobalt.tools',
            'https://cobalt.api.sciter.io',
            'https://cobalt-api.m3u8.dev'
        ];

        // Minimal, strict Cobalt API v10 payload
        const payload = {
            url: targetUrl
        };

        if (isAudio) {
            payload.downloadMode = 'audio';
            payload.audioFormat = mode;
        }

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
                    window.location.href = data.url;
                    resolved = true;
                    break;
                } else if (data.text) {
                    console.warn(`Instance ${instance} error:`, data.text);
                    updateStatus(`Error: ${data.text}`, 'error');
                }
            } catch (err) {
                console.warn(`Instance ${instance} request failed:`, err);
            }
        }

        if (!resolved && !statusBox.textContent.startsWith('Error:')) {
            updateStatus('Error: Failed to resolve stream link.', 'error');
        }

        setLoadingState(false);
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