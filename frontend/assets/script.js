document.addEventListener('DOMContentLoaded', () => {
    const downloadBtn = document.getElementById('download-btn');
    const urlInput = document.getElementById('url-input');
    const modeSelect = document.getElementById('mode-select');
    const statusBox = document.getElementById('status-box');

    if (!downloadBtn || !urlInput) return;

    let timerInterval = null;

    downloadBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        const mode = modeSelect ? modeSelect.value : 'mp4';

        if (!url) {
            updateStatus('Please enter a valid YouTube URL.', 'error');
            return;
        }

        setLoadingState(true);
        
        let seconds = 0;
        updateStatus(`Downloading... ${seconds}s`);

        timerInterval = setInterval(() => {
            seconds++;
            updateStatus(`Downloading... ${seconds}s`);
        }, 1000);

        try {
            const response = await fetch('/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url, mode })
            });

            clearInterval(timerInterval);

            if (!response.ok) {
                let errorMessage = `Server Error (${response.status})`;
                const contentType = response.headers.get('content-type');
                
                if (contentType && contentType.includes('application/json')) {
                    const errData = await response.json();
                    errorMessage = errData.error || errorMessage;
                } else {
                    const rawText = await response.text();
                    console.error('Server HTML Error Response:', rawText);
                }
                throw new Error(errorMessage);
            }

            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            
            const contentDisposition = response.headers.get('Content-Disposition');
            let fileName = `download.${mode === 'ogg' ? 'ogg' : mode === 'mp3' ? 'mp3' : 'mp4'}`;
            if (contentDisposition && contentDisposition.includes('filename=')) {
                fileName = contentDisposition.split('filename=')[1].replace(/"/g, '');
            }

            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = fileName;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(downloadUrl);

            updateStatus(`Download complete! (${seconds}s)`, 'success');

        } catch (err) {
            clearInterval(timerInterval);
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