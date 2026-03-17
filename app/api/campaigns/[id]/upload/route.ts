import { NextRequest, NextResponse } from 'next/server';
import pool from '@/lib/db';

// POST /api/campaigns/[id]/upload
export async function POST(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    try {
        const campaignId = params.id; // UUID string
        const leads = await request.json(); // Esperamos un array de leads procesado por papaparse en el cliente

        if (!Array.isArray(leads) || leads.length === 0) {
            return NextResponse.json({ success: false, error: 'No data provided' }, { status: 400 });
        }

        const client = await pool.connect();
        try {
            await client.query('BEGIN');

            let insertedCount = 0;
            let skippedCount = 0;

            for (const lead of leads) {
                const phone = lead.telefono || lead.phone;
                const name = lead.nombre || lead.name || 'Sin nombre';
                const website = lead.website || lead.website_actual || '';

                if (!phone) {
                    skippedCount++;
                    continue;
                }

                // Insert or update on conflict (evitar duplicados de número telefónico)
                const result = await client.query(`
                    INSERT INTO leads (phone, name, email, source, intent, stage, metadata, campaign_id)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (phone) DO UPDATE SET
                      name = COALESCE(EXCLUDED.name, leads.name),
                      campaign_id = EXCLUDED.campaign_id,
                      updated_at = NOW()
                    RETURNING id
                `, [
                    phone,
                    name,
                    '', // email 
                    'google_maps_scraper', // source
                    'cold_outreach', // intent temporal
                    'new', // stage
                    JSON.stringify({ website, original_data: lead }),
                    campaignId
                ]);

                insertedCount++;
            }

            // Cambiar status de campaña
            await client.query(`UPDATE campaigns SET status = 'active' WHERE id = $1`, [campaignId]);

            await client.query('COMMIT');

            return NextResponse.json({
                success: true,
                inserted: insertedCount,
                skipped: skippedCount
            });
        } catch (e) {
            await client.query('ROLLBACK');
            throw e;
        } finally {
            client.release();
        }

    } catch (error: any) {
        console.error('Error uploading leads:', error);
        return NextResponse.json({ success: false, error: 'Internal Server Error' }, { status: 500 });
    }
}
