import { NextRequest, NextResponse } from 'next/server';
import Database from 'better-sqlite3';
import path from 'path';

const dbPath = path.resolve(process.cwd(), '../backend/src/caller_memory.db');

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = Number(searchParams.get('limit') ?? '10');
    const sinceHours = Number(searchParams.get('since_hours') ?? '168');

    const db = new Database(dbPath, { readonly: true });
    const tableExists = db
      .prepare(`SELECT count(*) FROM sqlite_master WHERE type='table' AND name='call_outcomes'`)
      .pluck()
      .get();

    if (!tableExists) {
      db.close();
      return NextResponse.json({ calls: [] });
    }

    const cutoff = new Date(Date.now() - sinceHours * 60 * 60 * 1000).toISOString();
    const rows = db
      .prepare(`
        SELECT outcome, summary, category, channel, created_at
        FROM call_outcomes
        WHERE created_at >= ?
        ORDER BY created_at DESC
        LIMIT ?
      `)
      .all(cutoff, Number.isFinite(limit) ? limit : 10) as Array<{
        outcome: string;
        summary: string;
        category: string;
        channel: string;
        created_at: string;
      }>;

    db.close();

    const calls = rows.map((row, index) => ({
      call_id: `call-${index + 1}`,
      started_at: row.created_at,
      outcome: row.outcome,
      outcome_category: row.category || 'general',
      duration_seconds: 0,
      summary: row.summary || 'No summary recorded.',
      channel: row.channel || 'voice',
    }));

    return NextResponse.json({ calls });
  } catch (error) {
    console.error('Recent analytics DB error:', error);
    return NextResponse.json({ error: 'Failed to load recent analytics' }, { status: 500 });
  }
}
