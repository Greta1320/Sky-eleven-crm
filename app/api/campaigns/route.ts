import { NextRequest, NextResponse } from 'next/server';
import pool from '@/lib/db';

export async function GET(request: NextRequest) {
    try {
        const result = await pool.query('SELECT * FROM campaigns ORDER BY created_at DESC');
        return NextResponse.json({ success: true, data: result.rows });
    } catch (error: any) {
        console.error('Error fetching campaigns:', error);
        return NextResponse.json({ success: false, error: 'Internal Server Error' }, { status: 500 });
    }
}

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();
        const { name, niche, location } = body;

        if (!name) {
            return NextResponse.json({ success: false, error: 'Name is required' }, { status: 400 });
        }

        const result = await pool.query(
            `INSERT INTO campaigns (name, niche, location, channel, status) 
             VALUES ($1, $2, $3, 'google_maps', 'active') 
             RETURNING *`,
            [name, niche, location]
        );

        return NextResponse.json({ success: true, data: result.rows[0] });
    } catch (error: any) {
        console.error('Error creating campaign:', error.message, error.detail);
        return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }
}
