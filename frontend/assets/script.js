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
        updateStatus('Connecting to public resolvers...');

        // Public Cobalt mirrors that do not enforce JWT authorization
        const instances = [
            'https://cobalt-api.kwiatekmons.com',
            'https://co.wuk.sh',
            'https://api.cobalt.tools'
        ];

        const payload = {
            url: targetUrl,
            downloadMode: isAudio ? 'audio' : 'auto'
        };

        if (isAudio) {
            payload.audioFormat = mode;
        }

        let resolved = false;

        for (const instance of instances) {
            try {
                updateStatus(`Resolving via ${new URL(instance).hostname}...`);

                const response = await fetch(`${instance}/`, {
                    method: 'POST',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });

                const data = await response.json();

                if (response.ok && (data.url || data.status === 'redirect' || data.status === 'tunnel')) {
                    const downloadUrl = data.url || data.link;
                    updateStatus('Stream found! Initiating download...', 'success');
                    window.location.href = downloadUrl;
                    resolved = true;
                    break;
                } else if (data.text) {
                    console.warn(`Instance ${instance} error:`, data.text);
                }
            } catch (err) {
                console.warn(`Instance ${instance} request failed:`, err);
            }
        }

        if (!resolved) {
            updateStatus('Error: All resolvers failed or rate-limited. Try again shortly.', 'error');
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