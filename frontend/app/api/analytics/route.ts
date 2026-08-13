import { NextRequest, NextResponse } from 'next/server';
import Database from 'better-sqlite3';
import path from 'path';

const dbPath = path.resolve(process.cwd(), '../backend/src/caller_memory.db');

function getBaseSummary() {
  return {
    total_calls: 0,
    successful_calls: 0,
    failed_calls: 0,
    incomplete_calls: 0,
    success_rate_percent: 0,
    by_category: {},
    by_channel: {},
  };
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const sinceHours = Number(searchParams.get('since_hours') ?? '24');

    const db = new Database(dbPath, { readonly: true });
    const tableExists = db
      .prepare(`SELECT count(*) FROM sqlite_master WHERE type='table' AND name='call_outcomes'`)
      .pluck()
      .get();

    if (!tableExists) {
      db.close();
      return NextResponse.json(getBaseSummary());
    }

    const cutoff = new Date(Date.now() - sinceHours * 60 * 60 * 1000).toISOString();
    const rows = db
      .prepare(`
        SELECT outcome, category, channel, created_at
        FROM call_outcomes
        WHERE created_at >= ?
        ORDER BY created_at DESC
      `)
      .all(cutoff) as Array<{
        outcome: string;
        category: string;
        channel: string;
        created_at: string;
      }>;

    db.close();

    const total_calls = rows.length;
    const successful_calls = rows.filter((row) => row.outcome === 'success').length;
    const failed_calls = rows.filter((row) => row.outcome === 'failed').length;
    const incomplete_calls = rows.filter((row) => row.outcome === 'incomplete').length;
    const success_rate_percent = total_calls > 0 ? (successful_calls / total_calls) * 100 : 0;

    const by_category: Record<string, number> = {};
    const by_channel: Record<string, number> = {};

    for (const row of rows) {
      const category = row.category || 'general';
      by_category[category] = (by_category[category] ?? 0) + 1;

      const channel = row.channel || 'voice';
      by_channel[channel] = (by_channel[channel] ?? 0) + 1;
    }

    return NextResponse.json({
      total_calls,
      successful_calls,
      failed_calls,
      incomplete_calls,
      success_rate_percent,
      by_category,
      by_channel,
    });
  } catch (error) {
    console.error('Analytics DB error:', error);
    return NextResponse.json({ error: 'Failed to load analytics' }, { status: 500 });
  }
}
