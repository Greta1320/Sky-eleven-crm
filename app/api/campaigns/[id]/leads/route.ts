import { NextRequest, NextResponse } from 'next/server';
import pool from '@/lib/db';

export async function GET(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    try {
        const campaignId = params.id;

        // Sort by opportunity_score DESC (hottest leads first), fallback to created_at
        const result = await pool.query(
            `SELECT *,
                COALESCE((metadata->>'opportunity_score')::int, 0) AS computed_score
             FROM leads
             WHERE campaign_id = $1
             ORDER BY computed_score DESC, created_at DESC`,
            [campaignId]
        );

        return NextResponse.json({ success: true, data: result.rows });
    } catch (error: any) {
        console.error('Error fetching campaign leads:', error.message);
        return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }
}
