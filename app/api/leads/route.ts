import { NextRequest, NextResponse } from 'next/server';
import pool from '@/lib/db';

// GET /api/leads - Listar leads con filtros
export async function GET(request: NextRequest) {
    try {
        const searchParams = request.nextUrl.searchParams;
        const source = searchParams.get('source');
        const stage = searchParams.get('stage');
        const limit = parseInt(searchParams.get('limit') || '50');
        const offset = parseInt(searchParams.get('offset') || '0');

        let query = 'SELECT * FROM leads WHERE 1=1';
        const params: any[] = [];
        let paramIndex = 1;

        if (source) {
            query += ` AND source = $${paramIndex}`;
            params.push(source);
            paramIndex++;
        }

        if (stage) {
            query += ` AND stage = $${paramIndex}`;
            params.push(stage);
            paramIndex++;
        }

        query += ` ORDER BY created_at DESC LIMIT $${paramIndex} OFFSET $${paramIndex + 1}`;
        params.push(limit, offset);

        const result = await pool.query(query, params);

        return NextResponse.json({
            success: true,
            data: result.rows,
            count: result.rows.length,
        });
    } catch (error: any) {
        console.error('Error fetching leads:', error);
        return NextResponse.json(
            { success: false, error: error.message },
            { status: 500 }
        );
    }
}

// POST /api/leads - Crear nuevo lead
export async function POST(request: NextRequest) {
    try {
        const body = await request.json();
        const { phone, name, email, source, intent, score, stage, tags, metadata } = body;

        if (!phone || !source) {
            return NextResponse.json(
                { success: false, error: 'Phone and source are required' },
                { status: 400 }
            );
        }

        const result = await pool.query(
            `INSERT INTO leads (phone, name, email, source, intent, score, stage, tags, metadata)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
       ON CONFLICT (phone) DO UPDATE SET
         name = COALESCE(EXCLUDED.name, leads.name),
         email = COALESCE(EXCLUDED.email, leads.email),
         intent = COALESCE(EXCLUDED.intent, leads.intent),
         score = COALESCE(EXCLUDED.score, leads.score),
         stage = COALESCE(EXCLUDED.stage, leads.stage),
         tags = COALESCE(EXCLUDED.tags, leads.tags),
         metadata = COALESCE(EXCLUDED.metadata, leads.metadata),
         updated_at = NOW()
       RETURNING *`,
            [phone, name, email, source, intent, score || 0, stage || 'new', tags || [], metadata || {}]
        );

        return NextResponse.json({
            success: true,
            data: result.rows[0],
        });
    } catch (error: any) {
        console.error('Error creating lead:', error);
        return NextResponse.json(
            { success: false, error: error.message },
            { status: 500 }
        );
    }
}
