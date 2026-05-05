import { useEffect, useState, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { Download, ShieldAlert, Loader2 } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export function ShareDownload() {
    const { token } = useParams<{ token: string }>();
    const [status, setStatus] = useState<'loading' | 'error'>('loading');
    const [errorMsg, setErrorMsg] = useState('This link has expired or been revoked');
    const hasFetched = useRef(false);

    useEffect(() => {
        if (!token || hasFetched.current) return;
        hasFetched.current = true;

        const downloadFile = async () => {
            try {
                // This route does not require auth, we don't use api.ts interceptors here.
                const response = await fetch(`${API_BASE_URL}/share/${token}`);
                
                if (!response.ok) {
                    if (response.status === 410 || response.status === 404) {
                        setErrorMsg('This link has expired or been revoked.');
                    } else {
                        setErrorMsg('Failed to download file. It may be corrupt or removed.');
                    }
                    setStatus('error');
                    return;
                }

                // Extract filename from Content-Disposition if present
                let filename = 'downloaded_file';
                const disposition = response.headers.get('content-disposition');
                if (disposition && disposition.indexOf('filename=') !== -1) {
                    const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                    const matches = filenameRegex.exec(disposition);
                    if (matches != null && matches[1]) {
                        filename = matches[1].replace(/['"]/g, '');
                    }
                }

                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);

                // Re-prompt user if they want to close page or something
                // Keep loading status physically spinning or change to 'complete' if desired
                // In my case I'll flip to an error to gracefully halt UI state and tell them it worked
                setErrorMsg('Your download has started securely.'); 
                setStatus('error'); // Just to stop the loader
                
            } catch (err) {
                console.error(err);
                setErrorMsg('Network error while attempting to retrieve file.');
                setStatus('error');
            }
        };

        downloadFile();
    }, [token]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-950 p-4">
            <div className="w-full max-w-md bg-slate-900 rounded-2xl p-10 shadow-2xl border border-slate-800 text-center">
                {status === 'loading' ? (
                    <div className="space-y-6 flex flex-col items-center">
                        <Loader2 className="w-16 h-16 text-blue-500 animate-spin" />
                        <h2 className="text-xl font-bold text-white tracking-wide">Connecting securely...</h2>
                        <p className="text-sm text-slate-400 font-medium">Decrypting and verifying file bounds...</p>
                    </div>
                ) : (
                    <div className="space-y-6 flex flex-col items-center">
                        {errorMsg.includes('started') ? (
                            <div className="w-20 h-20 bg-emerald-500/10 rounded-full flex items-center justify-center mb-2 border border-emerald-500/20">
                                <Download className="w-10 h-10 text-emerald-500" />
                            </div>
                        ) : (
                            <div className="w-20 h-20 bg-red-500/10 rounded-full flex items-center justify-center mb-2 border border-red-500/20">
                                <ShieldAlert className="w-10 h-10 text-red-500" />
                            </div>
                        )}
                        <h2 className="text-xl font-bold text-white tracking-wide">
                            {errorMsg.includes('started') ? 'Download Complete' : 'Secure Transfer Failed'}
                        </h2>
                        <p className={`text-sm font-medium px-4 py-2 rounded-lg 
                            ${errorMsg.includes('started') ? 'text-emerald-400 bg-emerald-500/10' : 'text-red-400 bg-red-500/10'}`}>
                            {errorMsg}
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}
