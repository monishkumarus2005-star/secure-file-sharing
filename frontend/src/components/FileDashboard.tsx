import { useState, useEffect, useCallback } from 'react';
import {
  File as FileIcon,
  Upload,
  Download,
  Trash2,
  Shield,
  AlertTriangle,
  CheckCircle,
  History,
  X,
  Share2,
  ChevronLeft,
  ChevronRight,
  Search,
  Filter,
  Loader2,
  Copy
} from 'lucide-react';
import { useFiles, type FileItem } from '../hooks/useFiles';
import { SecurityAlerts } from './SecurityAlerts';
import { AccessHistory } from './AccessHistory';

interface FileDashboardProps {
  onLogout: () => void;
}

export function FileDashboard({ onLogout }: FileDashboardProps) {
  const {
    filesData,
    isLoading,
    error,
    fetchFiles,
    uploadFile,
    getFileStatus,
    downloadFile,
    deleteFile,
    verifyFile,
    createShareLink,
    getShareLinks,
    revokeShareLink
  } = useFiles();

  const [showHistory, setShowHistory] = useState(false);
  const [verifyingFile, setVerifyingFile] = useState<number | null>(null);
  const [verificationResult, setVerificationResult] = useState<any>(null);
  const [processingStatus, setProcessingStatus] = useState<Record<number, string>>({});

  // Pagination & Search States
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(20);
  const [search, setSearch] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [fileType, setFileType] = useState("all");

  // Share Modal States
  const [shareFile, setShareFile] = useState<FileItem | null>(null);
  const [expiryHours, setExpiryHours] = useState("24");
  const [maxDownloads, setMaxDownloads] = useState("0"); // 0 = unlimited
  const [activeShares, setActiveShares] = useState<any[]>([]);
  const [newShareUrl, setNewShareUrl] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetchFiles({ 
        page, 
        limit, 
        search: search || undefined, 
        from_date: fromDate || undefined, 
        to_date: toDate || undefined, 
        file_type: fileType === "all" ? undefined : fileType 
    });
  }, [fetchFiles, page, limit]);

  const handleSearchContext = (e: React.FormEvent) => {
      e.preventDefault();
      setPage(1); // Reset to page 1 on new search
      fetchFiles({ 
          page: 1, 
          limit, 
          search: search || undefined, 
          from_date: fromDate || undefined, 
          to_date: toDate || undefined, 
          file_type: fileType === "all" ? undefined : fileType 
      });
  };

  const clearFilters = () => {
      setSearch("");
      setFromDate("");
      setToDate("");
      setFileType("all");
      setPage(1);
      fetchFiles({ page: 1, limit });
  };

  const handleFileUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      // FIX 2: Upload status polling
      const res = await uploadFile(file);
      const fileId = res.file_id;
      
      setProcessingStatus(prev => ({...prev, [fileId]: "pending"}));

      const pollStatus = setInterval(async () => {
          try {
              const statusResponse = await getFileStatus(fileId);
              const currentStatus = statusResponse.status;
              
              setProcessingStatus(prev => ({...prev, [fileId]: currentStatus}));

              if (currentStatus === "complete") {
                  clearInterval(pollStatus);
                  fetchFiles({ page, limit, search, from_date: fromDate, to_date: toDate, file_type: fileType === "all" ? undefined : fileType });
              } else if (currentStatus === "failed") {
                  clearInterval(pollStatus);
              }
          } catch (e) {
              console.error("Polling error", e);
              clearInterval(pollStatus);
              setProcessingStatus(prev => ({...prev, [fileId]: "failed"}));
          }
      }, 2000);

      // Failsafe timeout
      setTimeout(() => clearInterval(pollStatus), 120000);

    } catch {
      // Error handled by hook
    }
    // Reset file input
    e.target.value = "";
  }, [uploadFile, getFileStatus, fetchFiles, page, limit, search, fromDate, toDate, fileType]);

  const openShareModal = async (file: FileItem) => {
      setShareFile(file);
      setNewShareUrl(null);
      try {
          const links = await getShareLinks(file.id);
          setActiveShares(links);
      } catch (e) {
          console.error("Failed to fetch share links", e);
      }
  };

  const handleGenerateShare = async () => {
      if (!shareFile) return;
      try {
          const hours = parseInt(expiryHours);
          const downloads = parseInt(maxDownloads);
          const result = await createShareLink(
              shareFile.id, 
              hours > 0 ? hours : null, 
              downloads > 0 ? downloads : null
          );
          // Generate full URL
          const shareUrl = `${window.location.origin}/share/${result.token}`;
          setNewShareUrl(shareUrl);
          
          // Refresh active links
          const links = await getShareLinks(shareFile.id);
          setActiveShares(links);
      } catch (e) {
          console.error("Failed to generate share link", e);
      }
  };

  const handleRevokeShare = async (token: string) => {
      if (!shareFile) return;
      try {
          await revokeShareLink(shareFile.id, token);
          setActiveShares(prev => prev.filter(s => s.token !== token));
      } catch (e) {
          console.error("Failed to revoke share link", e);
      }
  };

  const copyToClipboard = () => {
      if (newShareUrl) {
          navigator.clipboard.writeText(newShareUrl);
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
      }
  };

  const handleVerify = useCallback(async (fileId: number) => {
    setVerifyingFile(fileId);
    setVerificationResult(null);

    try {
      const result = await verifyFile(fileId);
      setVerificationResult({
        fileId,
        integrity_ok: result.integrity_ok,
        blockchain_verified: result.blockchain_verified
      });
    } catch {
      // Error handled by hook
    } finally {
      setVerifyingFile(null);
    }
  }, [verifyFile]);

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  const renderStatusLabel = (fileId: number) => {
      const status = processingStatus[fileId];
      if (!status) return null;

      if (status === "complete") {
          return <span className="text-xs bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full flex items-center gap-1 border border-emerald-500/20"><CheckCircle className="w-3 h-3" /> Ready</span>;
      }
      if (status === "failed") {
          return <span className="text-xs bg-red-500/10 text-red-400 px-2 py-0.5 rounded-full flex items-center gap-1 border border-red-500/20"><X className="w-3 h-3" /> Failed</span>;
      }

      let text = "Pending...";
      if (status === "encrypting") text = "Encrypting...";
      if (status === "hashing") text = "Hashing...";
      if (status === "anchoring") text = "Anchoring to blockchain...";

      return (
          <span className="text-xs bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded-full flex items-center gap-1 border border-blue-500/20">
              <Loader2 className="w-3 h-3 animate-spin" /> {text}
          </span>
      );
  };

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-800 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-violet-500/10 rounded-lg flex items-center justify-center">
                <Shield className="w-6 h-6 text-violet-500" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white tracking-tight">Secure File Share</h1>
                <p className="text-xs text-slate-400">Blockchain-Enabled File Storage</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={() => setShowHistory(!showHistory)}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors border border-slate-700"
              >
                <History className="w-4 h-4" />
                {showHistory ? 'Hide History' : 'Access History'}
              </button>
              <button
                onClick={onLogout}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600/80 hover:bg-red-500 rounded-lg transition-colors"
                id="logout-btn"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Security Alerts */}
      <SecurityAlerts />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Upload Section */}
            <div className="bg-slate-900 rounded-xl p-6 border border-slate-800 shadow-lg">
              <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2 tracking-tight">
                <Upload className="w-5 h-5 text-violet-500" />
                Upload File
              </h2>
              <div className="border-2 border-dashed border-slate-700 rounded-xl p-8 text-center hover:border-violet-500/50 transition-all duration-200">
                <input
                  type="file"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="file-upload"
                  disabled={isLoading}
                />
                <label
                  htmlFor="file-upload"
                  className="cursor-pointer flex flex-col items-center gap-3"
                >
                  <div className="w-14 h-14 bg-violet-500/10 rounded-full flex items-center justify-center">
                    <Upload className="w-7 h-7 text-violet-500" />
                  </div>
                  <div>
                    <p className="text-white font-medium">Click to upload a file</p>
                    <p className="text-slate-400 text-sm mt-1">
                      Files are encrypted with AES-128 and hashed for blockchain
                    </p>
                  </div>
                </label>
              </div>
            </div>

            {/* Filter Section */}
            <div className="bg-slate-900 rounded-xl p-6 border border-slate-800 shadow-lg">
                <form onSubmit={handleSearchContext} className="space-y-4">
                    <div className="flex gap-4 items-center">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                            <input 
                                type="text" 
                                placeholder="Search filenames..."
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                className="w-full pl-9 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-violet-500"
                            />
                        </div>
                        <select 
                            value={fileType}
                            onChange={(e) => setFileType(e.target.value)}
                            className="bg-slate-800 border border-slate-700 text-white text-sm rounded-lg px-4 py-2 focus:outline-none focus:border-violet-500"
                        >
                            <option value="all">All Types</option>
                            <option value=".pdf">PDF</option>
                            <option value="image">Image</option>
                            <option value=".txt">Text</option>
                            <option value=".csv">CSV</option>
                        </select>
                    </div>
                    <div className="flex gap-4 items-center">
                        <div className="flex items-center gap-2 text-slate-400 text-sm">
                            <Filter className="w-4 h-4" /> Dates:
                        </div>
                        <input 
                            type="date"
                            value={fromDate}
                            onChange={(e) => setFromDate(e.target.value)}
                            className="bg-slate-800 border border-slate-700 text-white text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-violet-500"
                        />
                        <span className="text-slate-500">to</span>
                        <input 
                            type="date"
                            value={toDate}
                            onChange={(e) => setToDate(e.target.value)}
                            className="bg-slate-800 border border-slate-700 text-white text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-violet-500"
                        />
                        <div className="flex-1"></div>
                        <button type="button" onClick={clearFilters} className="text-sm text-slate-400 hover:text-white">Clear</button>
                        <button type="submit" className="bg-violet-600 hover:bg-violet-500 text-white px-4 py-1.5 rounded-lg text-sm font-medium transition-colors">Apply Search</button>
                    </div>
                </form>
            </div>

            {/* Files List */}
            <div className="bg-slate-900 rounded-xl p-6 border border-slate-800 shadow-lg">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white flex items-center gap-2 tracking-tight">
                  <FileIcon className="w-5 h-5 text-violet-500" />
                  Your Files
                </h2>
                <div className="flex items-center gap-3">
                    <span className="text-sm text-slate-400">{filesData.total} files</span>
                    <button
                      onClick={() => fetchFiles({ page, limit, search, from_date: fromDate, to_date: toDate, file_type: fileType === "all" ? undefined : fileType })}
                      className="text-sm text-violet-400 hover:text-violet-300 font-medium transition-colors"
                      disabled={isLoading}
                    >
                      Refresh
                    </button>
                </div>
              </div>

              {error && (
                <div className="mb-4 flex items-center gap-2 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
                  <AlertTriangle className="w-4 h-4 text-red-400" />
                  <span className="text-red-400 text-sm">{error}</span>
                </div>
              )}

              {isLoading && filesData.items.length === 0 ? (
                <div className="text-center py-8">
                  <div className="w-8 h-8 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin mx-auto" />
                  <p className="text-slate-400 mt-2">Loading files...</p>
                </div>
              ) : filesData.items.length === 0 ? (
                <div className="text-center py-8">
                  <FileIcon className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                  <p className="text-slate-400">No files found</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {filesData.items.map((file) => (
                    <div
                      key={file.id}
                      className="flex flex-col p-4 bg-slate-800/50 rounded-xl border border-slate-700/50 hover:border-slate-600 hover:bg-slate-800 transition-all duration-200"
                    >
                      <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-violet-500/10 rounded-lg flex items-center justify-center flex-shrink-0">
                              <FileIcon className="w-5 h-5 text-violet-500" />
                            </div>
                            <div>
                              <p className="font-medium text-white">{file.filename}</p>
                              <p className="text-xs text-slate-400">
                                Uploaded {formatDate(file.upload_time)}
                              </p>
                              <div className="flex items-center gap-2 mt-1">
                                {renderStatusLabel(file.id)}
                                {file.blockchain_tx_hash && (
                                  <span className="text-xs bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full flex items-center gap-1 border border-emerald-500/20">
                                    <CheckCircle className="w-3 h-3" />
                                    Blockchain Anchored
                                  </span>
                                )}
                                {file.is_anomalous && (
                                  <span className="text-xs bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded-full flex items-center gap-1 border border-amber-500/20">
                                    <AlertTriangle className="w-3 h-3" />
                                    Anomaly Detected
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => openShareModal(file)}
                              className="p-2 text-slate-400 hover:text-blue-400 transition-colors rounded-lg hover:bg-slate-700/50"
                              title="Share file"
                            >
                              <Share2 className="w-5 h-5" />
                            </button>
                            <button
                              onClick={() => handleVerify(file.id)}
                              disabled={verifyingFile === file.id}
                              className="p-2 text-slate-400 hover:text-violet-400 transition-colors rounded-lg hover:bg-slate-700/50"
                              title="Verify file integrity"
                            >
                              {verifyingFile === file.id ? (
                                <div className="w-5 h-5 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin" />
                              ) : (
                                <Shield className="w-5 h-5" />
                              )}
                            </button>
                            <button
                              onClick={() => downloadFile(file.id, file.filename)}
                              className="p-2 text-slate-400 hover:text-emerald-400 transition-colors rounded-lg hover:bg-slate-700/50"
                              title="Download file"
                            >
                              <Download className="w-5 h-5" />
                            </button>
                            <button
                              onClick={() => deleteFile(file.id)}
                              className="p-2 text-slate-400 hover:text-red-400 transition-colors rounded-lg hover:bg-slate-700/50"
                              title="Delete file"
                            >
                              <Trash2 className="w-5 h-5" />
                            </button>
                          </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Pagination Controls */}
              {filesData.pages > 0 && (
                  <div className="mt-6 flex flex-col md:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-800">
                      <div className="flex items-center gap-2">
                          <span className="text-sm text-slate-400">Show</span>
                          <select 
                              value={limit}
                              onChange={(e) => { setLimit(Number(e.target.value)); setPage(1); }}
                              className="bg-slate-800 border border-slate-700 text-white text-sm rounded px-2 py-1 focus:outline-none focus:border-violet-500"
                          >
                              <option value="10">10</option>
                              <option value="20">20</option>
                              <option value="50">50</option>
                          </select>
                          <span className="text-sm text-slate-400">per page</span>
                      </div>
                      
                      <div className="flex items-center gap-4">
                          <span className="text-sm text-slate-400">
                              Page {filesData.page} of {filesData.pages}
                          </span>
                          <div className="flex gap-1">
                              <button 
                                  onClick={() => setPage(p => Math.max(1, p - 1))}
                                  disabled={filesData.page === 1}
                                  className="p-1 rounded bg-slate-800 disabled:opacity-50 text-slate-300 hover:bg-slate-700 transition-colors"
                              >
                                  <ChevronLeft className="w-5 h-5" />
                              </button>
                              <button 
                                  onClick={() => setPage(p => Math.min(filesData.pages, p + 1))}
                                  disabled={filesData.page >= filesData.pages}
                                  className="p-1 rounded bg-slate-800 disabled:opacity-50 text-slate-300 hover:bg-slate-700 transition-colors"
                              >
                                  <ChevronRight className="w-5 h-5" />
                              </button>
                          </div>
                      </div>
                  </div>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Stats Card */}
            <div className="bg-slate-900 rounded-xl p-6 border border-slate-800 shadow-lg">
              <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
                Storage Overview
              </h3>
              <div className="space-y-4">
                <div className="border-b border-slate-800 pb-4">
                  <p className="text-3xl font-bold text-white">{filesData.total}</p>
                  <p className="text-sm text-slate-400">Total Files</p>
                </div>
              </div>
            </div>

            {/* Security Info */}
            <div className="bg-slate-900 rounded-xl p-6 border border-slate-800 shadow-lg">
              <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
                Security Features
              </h3>
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <CheckCircle className="w-5 h-5 text-emerald-500" />
                  <span className="text-sm text-slate-300">AES-128 Encryption</span>
                </div>
                <div className="flex items-center gap-3">
                  <CheckCircle className="w-5 h-5 text-emerald-500" />
                  <span className="text-sm text-slate-300">SHA-256 File Hashing</span>
                </div>
                <div className="flex items-center gap-3">
                  <CheckCircle className="w-5 h-5 text-emerald-500" />
                  <span className="text-sm text-slate-300">Blockchain Anchoring</span>
                </div>
                <div className="flex items-center gap-3">
                  <CheckCircle className="w-5 h-5 text-emerald-500" />
                  <span className="text-sm text-slate-300">ML Anomaly Detection</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Access History Modal */}
      {showHistory && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 rounded-xl shadow-2xl w-full max-w-4xl max-h-[80vh] overflow-hidden border border-slate-800">
            <div className="flex items-center justify-between p-6 border-b border-slate-800">
              <h2 className="text-xl font-bold text-white flex items-center gap-2 tracking-tight">
                <History className="w-5 h-5 text-violet-500" />
                File Access History
              </h2>
              <button
                onClick={() => setShowHistory(false)}
                className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[60vh]">
              <AccessHistory />
            </div>
          </div>
        </div>
      )}

      {/* Share Modal */}
      {shareFile && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 rounded-xl shadow-2xl w-full max-w-lg overflow-hidden border border-slate-800 flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between p-5 border-b border-slate-800 flex-shrink-0">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Share2 className="w-5 h-5 text-blue-500" />
                Share File: {shareFile.filename}
              </h2>
              <button
                onClick={() => setShareFile(null)}
                className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto">
                <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-3">Create New Link</h3>
                <div className="grid grid-cols-2 gap-4 mb-4">
                    <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1">Expiry Date</label>
                        <select 
                            value={expiryHours}
                            onChange={(e) => setExpiryHours(e.target.value)}
                            className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg p-2.5 text-sm focus:outline-none focus:border-blue-500"
                        >
                            <option value="1">1 Hour</option>
                            <option value="24">24 Hours</option>
                            <option value="168">7 Days</option>
                            <option value="720">30 Days</option>
                        </select>
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1">Max Downloads</label>
                        <select 
                            value={maxDownloads}
                            onChange={(e) => setMaxDownloads(e.target.value)}
                            className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg p-2.5 text-sm focus:outline-none focus:border-blue-500"
                        >
                            <option value="0">Unlimited</option>
                            <option value="1">1 Time</option>
                            <option value="5">5 Times</option>
                            <option value="10">10 Times</option>
                        </select>
                    </div>
                </div>
                
                <button 
                    onClick={handleGenerateShare}
                    className="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-2.5 px-4 rounded-lg transition-colors mb-6"
                >
                    Generate Link
                </button>

                {newShareUrl && (
                    <div className="mb-8 p-4 bg-slate-800/80 rounded-lg border border-blue-500/30">
                        <p className="text-xs text-blue-400 mb-2 font-medium">Link Generated Successfully:</p>
                        <div className="flex gap-2">
                            <input 
                                type="text"
                                readOnly
                                value={newShareUrl}
                                className="flex-1 bg-slate-900 border border-slate-700 text-slate-300 text-sm rounded px-3 py-2 outline-none"
                            />
                            <button 
                                onClick={copyToClipboard}
                                className="flex items-center gap-1 bg-slate-700 hover:bg-slate-600 text-white px-3 py-2 rounded text-sm font-medium transition-colors"
                            >
                                {copied ? <CheckCircle className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                                {copied ? 'Copied!' : 'Copy'}
                            </button>
                        </div>
                    </div>
                )}

                <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-3 pt-4 border-t border-slate-800">Manage Shares ({activeShares.length})</h3>
                {activeShares.length === 0 ? (
                    <p className="text-sm text-slate-500 italic">No active share links.</p>
                ) : (
                    <div className="space-y-3">
                        {activeShares.map(share => (
                            <div key={share.token} className="flex flex-col gap-2 p-3 bg-slate-800/50 rounded border border-slate-700/50">
                                <div className="flex items-center justify-between">
                                    <div className="text-xs text-slate-300 font-mono">{share.token.substring(0, 16)}...</div>
                                    <button 
                                        onClick={() => handleRevokeShare(share.token)}
                                        className="text-xs text-red-400 hover:text-red-300 font-medium"
                                    >
                                        Revoke
                                    </button>
                                </div>
                                <div className="flex justify-between text-xs text-slate-500">
                                    <span>Uses: {share.downloads_count} / {share.max_downloads || '∞'}</span>
                                    <span>Expires: {share.expires_at ? new Date(share.expires_at).toLocaleDateString() : 'Never'}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
          </div>
        </div>
      )}

      {/* Verification Result Modal */}
      {verificationResult && (
        // (Unchanged Verification Result Modal Code omitted for brevity from UI mapping)
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 rounded-xl shadow-2xl w-full max-w-md p-6 border border-slate-800">
            <h3 className="text-lg font-bold text-white mb-4 tracking-tight">File Verification Result</h3>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                {verificationResult.integrity_ok ? (
                  <>
                    <CheckCircle className="w-8 h-8 text-emerald-500" />
                    <div>
                      <p className="font-medium text-white">Integrity Verified</p>
                      <p className="text-sm text-slate-400">File hash matches stored hash</p>
                    </div>
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-8 h-8 text-red-500" />
                    <div>
                      <p className="font-medium text-white">Integrity Check Failed</p>
                      <p className="text-sm text-slate-400">File hash does not match</p>
                    </div>
                  </>
                )}
              </div>
              {verificationResult.blockchain_verified !== null && (
                <div className="flex items-center gap-3">
                  {verificationResult.blockchain_verified ? (
                    <>
                      <CheckCircle className="w-8 h-8 text-emerald-500" />
                      <div>
                        <p className="font-medium text-white">Blockchain Verified</p>
                        <p className="text-sm text-slate-400">Hash matches blockchain record</p>
                      </div>
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="w-8 h-8 text-amber-500" />
                      <div>
                        <p className="font-medium text-white">Blockchain Mismatch</p>
                        <p className="text-sm text-slate-400">Hash differs from blockchain</p>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
            <button
              onClick={() => setVerificationResult(null)}
              className="w-full mt-6 bg-violet-600 hover:bg-violet-500 text-white font-bold py-3 px-6 rounded-lg transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
