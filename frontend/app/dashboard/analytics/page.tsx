'use client';

import { useEffect, useState } from 'react';
import { Activity, ArrowUpRight, Clock3, PhoneCall, TrendingUp } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface AnalyticsData {
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  incomplete_calls: number;
  success_rate_percent: number;
  by_category: Record<string, number>;
  by_channel: Record<string, number>;
}

interface RecentCall {
  call_id: string;
  started_at: string;
  outcome: string;
  outcome_category: string;
  duration_seconds: number;
  summary: string;
  channel: string;
}

function formatPercent(value: number) {
  return `${Number.isFinite(value) ? value.toFixed(1) : '0.0'}%`;
}

export default function AnalyticsDashboard() {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [recentCalls, setRecentCalls] = useState<RecentCall[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<string>('');

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const [analyticsRes, recentRes] = await Promise.all([
          fetch('/api/analytics?since_hours=24'),
          fetch('/api/analytics/recent?limit=10&since_hours=168'),
        ]);

        if (analyticsRes.ok) {
          const analyticsData = await analyticsRes.json();
          setAnalytics(analyticsData);
        }

        if (recentRes.ok) {
          const recentData = await recentRes.json();
          setRecentCalls(recentData.calls ?? []);
        }

        setLastUpdated(new Date().toLocaleTimeString());
      } catch (error) {
        console.error('Failed to fetch analytics', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 15000);
    return () => clearInterval(interval);
  }, []);

  if (loading || !analytics) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex items-center gap-3 text-slate-600">
          <Activity className="h-6 w-6 animate-pulse" />
          <span className="text-lg font-medium">Loading analytics…</span>
        </div>
      </div>
    );
  }

  const metricCards = [
    {
      title: 'Total calls',
      value: analytics.total_calls,
      icon: <PhoneCall className="h-5 w-5 text-emerald-600" />,
      color: 'border-l-emerald-500',
    },
    {
      title: 'Successful',
      value: analytics.successful_calls,
      icon: <TrendingUp className="h-5 w-5 text-blue-600" />,
      color: 'border-l-blue-500',
    },
    {
      title: 'Failed',
      value: analytics.failed_calls,
      icon: <ArrowUpRight className="h-5 w-5 text-orange-500" />,
      color: 'border-l-orange-500',
    },
    {
      title: 'Success rate',
      value: formatPercent(analytics.success_rate_percent),
      icon: <Clock3 className="h-5 w-5 text-violet-600" />,
      color: 'border-l-violet-500',
    },
  ];

  return (
    <div className="mx-auto max-w-7xl p-8">
      <div className="mb-8 flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-emerald-600">Operations dashboard</p>
          <h1 className="mt-2 text-3xl font-bold text-slate-900 dark:text-white">Call Analytics</h1>
        </div>
        <div className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
          Updated {lastUpdated || 'just now'}
        </div>
      </div>

      <div className="mb-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {metricCards.map((card) => (
          <Card key={card.title} className={`border-l-4 ${card.color}`}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium text-slate-500 dark:text-slate-400">{card.title}</CardTitle>
                <div>{card.icon}</div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-slate-900 dark:text-white">{card.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Outcome by category</CardTitle>
          </CardHeader>
          <CardContent>
            {Object.keys(analytics.by_category).length === 0 ? (
              <p className="text-sm text-slate-500">No call categories recorded yet.</p>
            ) : (
              <div className="space-y-3">
                {Object.entries(analytics.by_category).map(([category, count]) => (
                  <div key={category}>
                    <div className="mb-1 flex justify-between text-sm">
                      <span className="capitalize text-slate-700 dark:text-slate-200">{category}</span>
                      <span className="font-medium text-slate-900 dark:text-white">{count}</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
                      <div
                        className="h-full rounded-full bg-emerald-500"
                        style={{ width: `${(count / Math.max(analytics.total_calls, 1)) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Channel mix</CardTitle>
          </CardHeader>
          <CardContent>
            {Object.keys(analytics.by_channel).length === 0 ? (
              <p className="text-sm text-slate-500">No channel metrics available yet.</p>
            ) : (
              <div className="space-y-3">
                {Object.entries(analytics.by_channel).map(([channel, count]) => (
                  <div key={channel} className="flex items-center justify-between text-sm">
                    <span className="capitalize text-slate-700 dark:text-slate-200">{channel}</span>
                    <span className="font-medium text-slate-900 dark:text-white">{count}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="mt-8">
        <CardHeader>
          <CardTitle>Recent calls</CardTitle>
        </CardHeader>
        <CardContent>
          {recentCalls.length === 0 ? (
            <p className="text-sm text-slate-500">No recent call activity found.</p>
          ) : (
            <div className="space-y-4">
              {recentCalls.map((call) => (
                <div key={call.call_id} className="rounded-lg border border-slate-200 p-4 dark:border-slate-700">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-900 dark:text-white">{call.call_id}</p>
                      <p className="text-xs text-slate-500">{new Date(call.started_at).toLocaleString()}</p>
                    </div>
                    <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-medium capitalize text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                      {call.outcome}
                    </span>
                  </div>
                  <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">{call.summary}</p>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
                    <span>Channel: {call.channel}</span>
                    <span>Category: {call.outcome_category}</span>
                    <span>Duration: {call.duration_seconds}s</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
