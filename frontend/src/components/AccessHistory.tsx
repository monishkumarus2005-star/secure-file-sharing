import { useEffect } from 'react';
import { useFiles } from '../hooks/useFiles';
import {
  Clock,
  Upload,
  Download,
  Trash2,
  CheckCircle,
  XCircle,
  AlertTriangle
} from 'lucide-react';

export function AccessHistory() {
  const { accessLogs, isLoading, error, fetchAccessLogs } = useFiles();

  useEffect(() => {
    fetchAccessLogs();
  }, [fetchAccessLogs]);

  const getActionIcon = (actionType: string) => {
    switch (actionType) {
      case 'upload':
        return <Upload className="w-4 h-4" />;
      case 'download':
        return <Download className="w-4 h-4" />;
      case 'delete':
        return <Trash2 className="w-4 h-4" />;
      default:
        return <Clock className="w-4 h-4" />;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
      case 'granted':
        return <CheckCircle className="w-4 h-4 text-emerald-400" />;
      case 'denied':
        return <XCircle className="w-4 h-4 text-red-400" />;
      default:
        return <AlertTriangle className="w-4 h-4 text-amber-400" />;
    }
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="w-8 h-8 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin mx-auto" />
        <p className="text-slate-400 mt-2">Loading access history...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
        <AlertTriangle className="w-4 h-4 text-red-400" />
        <span className="text-red-400 text-sm">{error}</span>
      </div>
    );
  }

  if (accessLogs.length === 0) {
    return (
      <div className="text-center py-8">
        <Clock className="w-12 h-12 text-slate-600 mx-auto mb-3" />
        <p className="text-slate-400">No access logs found</p>
        <p className="text-sm text-slate-500 mt-1">
          File access activities will appear here
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-800">
              <th className="text-left py-3 px-4 text-sm font-medium text-slate-400 uppercase tracking-wide">
                Time
              </th>
              <th className="text-left py-3 px-4 text-sm font-medium text-slate-400 uppercase tracking-wide">
                Action
              </th>
              <th className="text-left py-3 px-4 text-sm font-medium text-slate-400 uppercase tracking-wide">
                File ID
              </th>
              <th className="text-left py-3 px-4 text-sm font-medium text-slate-400 uppercase tracking-wide">
                Status
              </th>
              <th className="text-left py-3 px-4 text-sm font-medium text-slate-400 uppercase tracking-wide">
                IP Address
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {accessLogs.map((log) => (
              <tr key={log.id} className="hover:bg-slate-800/50 transition-colors">
                <td className="py-3 px-4 text-sm text-slate-300">
                  {formatDate(log.access_time)}
                </td>
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    <span className="text-violet-400">{getActionIcon(log.action_type)}</span>
                    <span className="text-sm text-slate-300 capitalize">{log.action_type}</span>
                  </div>
                </td>
                <td className="py-3 px-4 text-sm text-slate-300">
                  {log.file_id || '-'}
                </td>
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    {getStatusIcon(log.access_status)}
                    <span className="text-sm text-slate-300 capitalize">{log.access_status}</span>
                  </div>
                </td>
                <td className="py-3 px-4 text-sm text-slate-500">
                  {log.ip_address || 'Unknown'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between pt-4 border-t border-slate-800">
        <p className="text-sm text-slate-500">
          Showing {accessLogs.length} recent access logs
        </p>
        <button
          onClick={() => fetchAccessLogs()}
          className="text-sm text-violet-400 hover:text-violet-300 font-medium transition-colors"
        >
          Refresh
        </button>
      </div>
    </div>
  );
}
