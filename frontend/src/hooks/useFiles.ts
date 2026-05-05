import { useState, useCallback } from 'react';
import { api } from '../api';

export interface FileItem {
  id: number;
  filename: string;
  file_hash: string;
  owner_id: number;
  upload_time: string;
  is_deleted: boolean;
  blockchain_tx_hash?: string;
  blockchain_index?: number;
  is_anomalous?: boolean;
}

export interface AccessLog {
  id: number;
  user_id: number;
  file_id: number | null;
  access_time: string;
  access_status: string;
  ip_address: string | null;
  device_info: string | null;
  action_type: string;
}

export interface PaginatedFiles {
  items: FileItem[];
  total: number;
  page: number;
  pages: number;
  limit: number;
}

export interface ShareLink {
  id: number;
  token: string;
  created_at: string;
  expires_at: string | null;
  max_downloads: number | null;
  downloads_count: number;
  is_active: boolean;
}

export interface FetchFilesParams {
  page?: number;
  limit?: number;
  search?: string;
  from_date?: string;
  to_date?: string;
  file_type?: string;
}

export function useFiles() {
  const [filesData, setFilesData] = useState<PaginatedFiles>({
    items: [],
    total: 0,
    page: 1,
    pages: 1,
    limit: 20
  });
  
  const [accessLogs, setAccessLogs] = useState<AccessLog[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchFiles = useCallback(async (params: FetchFilesParams = {}): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get<PaginatedFiles>('/files/', { params });
      // In case the backend returns an array due to incomplete migration, handle both
      if (Array.isArray(response.data)) {
         setFilesData({
             items: response.data,
             total: response.data.length,
             page: 1,
             pages: 1,
             limit: 20
         });
      } else {
         setFilesData(response.data);
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to fetch files';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchAccessLogs = useCallback(async (fileId?: number): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get<AccessLog[]>('/access-logs/', {
        params: fileId ? { file_id: fileId } : undefined
      });
      setAccessLogs(response.data);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to fetch access logs';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const uploadFile = useCallback(async (file: File): Promise<{ file_id: number; message: string }> => {
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await api.post('/files/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      return response.data;
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Upload failed';
      setError(errorMessage);
      throw err;
    } 
  }, []);

  const getFileStatus = useCallback(async (fileId: number) => {
    const response = await api.get(`/files/${fileId}/status`);
    return response.data;
  }, []);

  const downloadFile = useCallback(async (fileId: number, filename: string): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get(`/files/download/${fileId}`, {
        responseType: 'blob'
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Download failed';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const deleteFile = useCallback(async (fileId: number): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      await api.delete(`/files/${fileId}`);
      setFilesData(prev => ({
          ...prev,
          items: prev.items.filter(f => f.id !== fileId),
          total: prev.total - 1
      }));
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Delete failed';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const verifyFile = useCallback(async (fileId: number): Promise<{
    integrity_ok: boolean;
    blockchain_verified: boolean | null;
    stored_hash: string;
    current_hash: string;
  }> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get(`/files/${fileId}/verify`);
      return response.data;
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Verification failed';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);
  
  // File Sharing Hooks
  const createShareLink = useCallback(async (fileId: number, expiresInHours: number | null, maxDownloads: number | null) => {
    const response = await api.post(`/files/${fileId}/share`, {
        expires_in_hours: expiresInHours,
        max_downloads: maxDownloads
    });
    return response.data;
  }, []);

  const getShareLinks = useCallback(async (fileId: number) => {
    const response = await api.get(`/files/${fileId}/shares`);
    return response.data;
  }, []);

  const revokeShareLink = useCallback(async (fileId: number, token: string) => {
    const response = await api.delete(`/files/${fileId}/share/${token}`);
    return response.data;
  }, []);

  return {
    filesData,
    accessLogs,
    isLoading,
    error,
    fetchFiles,
    fetchAccessLogs,
    uploadFile,
    getFileStatus,
    downloadFile,
    deleteFile,
    verifyFile,
    createShareLink,
    getShareLinks,
    revokeShareLink
  };
}
