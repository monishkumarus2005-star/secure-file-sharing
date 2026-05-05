import { useState, useEffect, useCallback } from 'react';
import { useApi } from './useApi';

export interface SecurityAlert {
  id: string;
  type: 'anomaly' | 'suspicious_login' | 'access_denied' | 'rate_limit';
  message: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  timestamp: string;
  details?: {
    user_id?: number;
    file_id?: number;
    action_type?: string;
    ip_address?: string | null;
    device_info?: string;
  };
}

interface AccessStats {
  total_accesses: number;
  by_action: {
    upload: number;
    download: number;
    delete: number;
  };
  by_status: {
    granted: number;
    denied: number;
  };
  recent_activity: Array<{
    id: number;
    action_type: string;
    access_status: string;
    access_time: string;
    ip_address: string | null;
  }>;
}

export function useAlerts(pollInterval: number = 30000) {
  const { request } = useApi();
  const [alerts, setAlerts] = useState<SecurityAlert[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const generateAlertsFromStats = useCallback((stats: AccessStats): SecurityAlert[] => {
    const generatedAlerts: SecurityAlert[] = [];

    // Check for suspicious patterns
    const deniedRatio = stats.total_accesses > 0
      ? stats.by_status.denied / stats.total_accesses
      : 0;

    if (deniedRatio > 0.3) {
      generatedAlerts.push({
        id: `denied-ratio-${Date.now()}`,
        type: 'access_denied',
        message: 'High rate of denied access attempts detected',
        severity: 'high',
        timestamp: new Date().toISOString(),
        details: {
          denied_count: stats.by_status.denied,
          total_accesses: stats.total_accesses
        } as unknown as Record<string, unknown>
      });
    }

    // Check recent activity for anomalies
    stats.recent_activity.forEach(activity => {
      // Detect rapid successive actions (potential anomaly)
      const recentActions = stats.recent_activity.filter(
        a => new Date(a.access_time).getTime() > Date.now() - 60000
      );

      if (recentActions.length > 10) {
        const existingAlert = generatedAlerts.find(a => a.type === 'anomaly');
        if (!existingAlert) {
          generatedAlerts.push({
            id: `rapid-actions-${Date.now()}`,
            type: 'anomaly',
            message: 'Suspicious access pattern: Rapid file operations detected',
            severity: 'medium',
            timestamp: new Date().toISOString(),
            details: {
              action_count: recentActions.length,
              time_window: '1 minute'
            } as unknown as Record<string, unknown>
          });
        }
      }

      // Detect denied access attempts
      if (activity.access_status === 'denied') {
        generatedAlerts.push({
          id: `denied-${activity.id}-${Date.now()}`,
          type: 'access_denied',
          message: `Access denied: ${activity.action_type} attempt blocked`,
          severity: 'medium',
          timestamp: activity.access_time,
          details: {
            action_type: activity.action_type,
            ip_address: activity.ip_address
          }
        });
      }
    });

    return generatedAlerts;
  }, []);

  const fetchAlerts = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      // Fetch access stats and logs from backend
      const stats = await request<AccessStats>('/access-logs/stats', { requiresAuth: true });

      // Generate alerts based on the stats
      const generatedAlerts = generateAlertsFromStats(stats);
      setAlerts(generatedAlerts);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch alerts';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [request, generateAlertsFromStats]);

  const dismissAlert = useCallback((alertId: string): void => {
    setAlerts(prev => prev.filter(alert => alert.id !== alertId));
  }, []);

  const clearAllAlerts = useCallback((): void => {
    setAlerts([]);
  }, []);

  // Poll for alerts at the specified interval
  useEffect(() => {
    fetchAlerts();

    const intervalId = setInterval(() => {
      fetchAlerts();
    }, pollInterval);

    return () => clearInterval(intervalId);
  }, [fetchAlerts, pollInterval]);

  // Group alerts by severity for easier display
  const alertsBySeverity = {
    critical: alerts.filter(a => a.severity === 'critical'),
    high: alerts.filter(a => a.severity === 'high'),
    medium: alerts.filter(a => a.severity === 'medium'),
    low: alerts.filter(a => a.severity === 'low')
  };

  const hasAlerts = alerts.length > 0;
  const criticalCount = alertsBySeverity.critical.length;
  const highCount = alertsBySeverity.high.length;

  return {
    alerts,
    alertsBySeverity,
    isLoading,
    error,
    hasAlerts,
    criticalCount,
    highCount,
    fetchAlerts,
    dismissAlert,
    clearAllAlerts
  };
}
