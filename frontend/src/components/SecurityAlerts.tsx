import { useAlerts } from '../hooks/useAlerts';
import {
  AlertTriangle,
  ShieldAlert,
  X,
  Bell,
  RefreshCw
} from 'lucide-react';

export function SecurityAlerts() {
  const {
    alerts,
    alertsBySeverity,
    isLoading,
    hasAlerts,
    criticalCount,
    highCount,
    fetchAlerts,
    dismissAlert,
    clearAllAlerts
  } = useAlerts(30000); // Poll every 30 seconds

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
      case 'high':
        return <AlertTriangle className="w-5 h-5 text-red-400" />;
      case 'medium':
        return <ShieldAlert className="w-5 h-5 text-amber-400" />;
      default:
        return <Bell className="w-5 h-5 text-slate-400" />;
    }
  };

  const getSeverityClass = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500/10 border-red-500/20 text-red-400';
      case 'high':
        return 'bg-red-500/10 border-red-500/20 text-red-400';
      case 'medium':
        return 'bg-amber-500/10 border-amber-500/20 text-amber-400';
      default:
        return 'bg-slate-500/10 border-slate-500/20 text-slate-400';
    }
  };

  if (!hasAlerts && !isLoading) {
    return null;
  }

  return (
    <div className="bg-slate-900 border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-amber-400" />
            <h2 className="text-lg font-semibold text-white tracking-tight">Security Alerts</h2>
            {(criticalCount > 0 || highCount > 0) && (
              <span className="bg-red-500 text-white text-xs px-2 py-1 rounded-full font-medium">
                {criticalCount + highCount}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchAlerts}
              disabled={isLoading}
              className="p-2 text-slate-400 hover:text-violet-400 transition-colors rounded-lg hover:bg-slate-800"
              title="Refresh alerts"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={clearAllAlerts}
              className="text-sm text-slate-400 hover:text-white transition-colors"
            >
              Dismiss All
            </button>
          </div>
        </div>

        {isLoading && alerts.length === 0 ? (
          <div className="flex items-center gap-2 text-slate-400">
            <div className="w-4 h-4 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin" />
            <span>Checking for security alerts...</span>
          </div>
        ) : (
          <div className="space-y-2">
            {/* Critical Alerts */}
            {alertsBySeverity.critical.map((alert) => (
              <div
                key={alert.id}
                className={`flex items-start gap-3 p-3 rounded-lg border ${getSeverityClass(alert.severity)}`}
              >
                {getSeverityIcon(alert.severity)}
                <div className="flex-1">
                  <p className="font-medium text-white">{alert.message}</p>
                  {alert.details && (
                    <p className="text-sm text-slate-400 mt-1">
                      {alert.details.ip_address && `IP: ${alert.details.ip_address} • `}
                      {alert.details.action_type && `Action: ${alert.details.action_type}`}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => dismissAlert(alert.id)}
                  className="p-1 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-lg transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}

            {/* High Priority Alerts */}
            {alertsBySeverity.high.map((alert) => (
              <div
                key={alert.id}
                className={`flex items-start gap-3 p-3 rounded-lg border ${getSeverityClass(alert.severity)}`}
              >
                {getSeverityIcon(alert.severity)}
                <div className="flex-1">
                  <p className="font-medium text-white">{alert.message}</p>
                  {alert.details && (
                    <p className="text-sm text-slate-400 mt-1">
                      {alert.details.ip_address && `IP: ${alert.details.ip_address} • `}
                      {alert.details.action_type && `Action: ${alert.details.action_type}`}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => dismissAlert(alert.id)}
                  className="p-1 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-lg transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}

            {/* Medium Priority Alerts */}
            {alertsBySeverity.medium.slice(0, 3).map((alert) => (
              <div
                key={alert.id}
                className={`flex items-start gap-3 p-3 rounded-lg border ${getSeverityClass(alert.severity)}`}
              >
                {getSeverityIcon(alert.severity)}
                <div className="flex-1">
                  <p className="font-medium text-white">{alert.message}</p>
                  {alert.details && (
                    <p className="text-sm text-slate-400 mt-1">
                      {alert.details.ip_address && `IP: ${alert.details.ip_address} • `}
                      {alert.details.action_type && `Action: ${alert.details.action_type}`}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => dismissAlert(alert.id)}
                  className="p-1 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-lg transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}

            {alertsBySeverity.medium.length > 3 && (
              <p className="text-sm text-text-muted text-center">
                +{alertsBySeverity.medium.length - 3} more medium priority alerts
              </p>
            )}
          </div>
        )}

        {alertsBySeverity.medium.length > 3 && (
          <p className="text-sm text-slate-500 text-center mt-4">
            +{alertsBySeverity.medium.length - 3} more medium priority alerts
          </p>
        )}
      </div>
    </div>
  );
}
