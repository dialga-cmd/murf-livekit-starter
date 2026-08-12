import { NextResponse } from 'next/server';
import Database from 'better-sqlite3';
import path from 'path';

// Path to the SQLite database in the backend directory
const dbPath = path.resolve(process.cwd(), '../backend/src/caller_memory.db');

export async function GET() {
  try {
    const db = new Database(dbPath, { readonly: true });
    
    // Check if table exists
    const tableExists = db.prepare(`SELECT count(*) FROM sqlite_master WHERE type='table' AND name='escalations'`).pluck().get();
    
    if (!tableExists) {
      return NextResponse.json({ escalations: [] });
    }

    const escalations = db.prepare(`
      SELECT id, user_id, summary, urgency, language, status, human_response, created_at 
      FROM escalations 
      ORDER BY created_at DESC
    `).all();
    
    db.close();
    
    return NextResponse.json({ escalations });
  } catch (error) {
    console.error('Database error:', error);
    return NextResponse.json({ error: 'Failed to fetch escalations' }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { id, response } = body;

    if (!id || !response) {
      return NextResponse.json({ error: 'Missing id or response' }, { status: 400 });
    }

    const db = new Database(dbPath);
    
    const stmt = db.prepare(`
      UPDATE escalations 
      SET status = 'resolved', human_response = ? 
      WHERE id = ?
    `);
    
    const info = stmt.run(response, id);
    db.close();

    if (info.changes > 0) {
      return NextResponse.json({ success: true });
    } else {
      return NextResponse.json({ error: 'Escalation not found' }, { status: 404 });
    }
  } catch (error) {
    console.error('Database error:', error);
    return NextResponse.json({ error: 'Failed to update escalation' }, { status: 500 });
  }
}
