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
        updateStatus('Connecting to active resolvers...');

        // Active Cobalt v10 instances
        const instances = [
            'https://api.cobalt.tools',
            'https://cobalt.api.sciter.io'
        ];

        // Valid Cobalt v10 API payload format
        const payload = {
            url: targetUrl,
            downloadMode: isAudio ? 'audio' : 'auto',
            videoQuality: 'max'
        };

        if (isAudio) {
            payload.audioFormat = mode;
        }

        let resolved = false;

        for (const instance of instances) {
            try {
                updateStatus(`Resolving stream...`);

                const response = await fetch(`${instance}/`, {
                    method: 'POST',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });

                const data = await response.json();

                if (response.ok && (data.url || data.status === 'redirect' || data.status === 'tunnel' || data.status === 'picker')) {
                    const downloadUrl = data.url || data.link || (data.picker && data.picker[0] ? data.picker[0].url : null);
                    
                    if (downloadUrl) {
                        updateStatus('Stream found! Opening download...', 'success');
                        window.location.href = downloadUrl;
                        resolved = true;
                        break;
                    }
                } else if (data.text) {
                    console.warn(`Instance ${instance} returned error:`, data.text);
                }
            } catch (err) {
                console.warn(`Failed reaching ${instance}:`, err);
            }
        }

        if (!resolved) {
            updateStatus('Error: Resolvers failed or blocked. Try another link.', 'error');
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