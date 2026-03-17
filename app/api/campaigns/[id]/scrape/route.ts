import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import pool from '@/lib/db';

export async function POST(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    const campaignId = params.id;

    try {
        const { query, maxResults = 20 } = await request.json();

        if (!query) {
            return NextResponse.json({ success: false, error: 'query is required' }, { status: 400 });
        }

        const scraperPath = path.join(process.cwd(), 'scrapers', 'scraper_api.py');
        const pythonPath = path.join(process.cwd(), 'scrapers', 'venv', 'Scripts', 'python.exe');

        const leads: any[] = await new Promise((resolve, reject) => {
            const proc = spawn(pythonPath, [scraperPath, query, String(maxResults)]);
            let output = '';
            let errOutput = '';

            proc.stdout.on('data', (d) => output += d.toString());
            proc.stderr.on('data', (d) => {
                const line = d.toString();
                errOutput += line;
                // Log de progreso visible en la consola del servidor
                if (line.includes('[PROGRESS]')) {
                    console.log(`Scraper: ${line.trim()}`);
                }
            });

            proc.on('close', (code) => {
                if (code !== 0) {
                    reject(new Error(`Scraper exited with code ${code}: ${errOutput}`));
                    return;
                }
                try {
                    const lines = output.trim().split('\n');
                    const jsonLine = lines.filter(l => l.trim().startsWith('[') || l.trim().startsWith('{')).pop() || '[]';
                    resolve(JSON.parse(jsonLine));
                } catch (e) {
                    reject(new Error(`Failed to parse scraper output: ${output.substring(0, 500)}`));
                }
            });

            // Timeout de 5 minutos para scraping largo
            setTimeout(() => {
                proc.kill();
                reject(new Error('Scraper timeout after 5 minutes'));
            }, 5 * 60 * 1000);
        });

        if (!leads.length) {
            return NextResponse.json({ success: false, error: 'No leads found for this query.' });
        }

        // Insertar leads en la BD vinculados a la campaña
        const client = await pool.connect();
        let inserted = 0;
        let skipped = 0;
        let hotLeads = 0;

        try {
            await client.query('BEGIN');

            for (const lead of leads) {
                const phone = lead.phone || lead.telefono;
                const name = lead.nombre || lead.name || 'Sin nombre';
                const website = lead.website || '';
                const address = lead.address || '';
                const category = lead.category || '';
                const rating = lead.rating || '';
                const reviews = lead.reviews || '';
                const opportunityScore = lead.opportunity_score || 0;
                const whatsappLink = lead.whatsapp_link || '';
                const mapsUrl = lead.maps_url || '';

                // Si no tiene ni teléfono ni nombre real, saltar
                if (!name || name === 'Sin nombre') { skipped++; continue; }

                const metadata = JSON.stringify({
                    website,
                    address,
                    category,
                    rating,
                    reviews,
                    opportunity_score: opportunityScore,
                    whatsapp_link: whatsappLink,
                    maps_url: mapsUrl,
                    query
                });

                const result = await client.query(`
                    INSERT INTO leads (phone, name, source, stage, metadata, campaign_id)
                    VALUES ($1, $2, 'google_maps_scraper', 'new', $3, $4)
                    ON CONFLICT (phone) DO UPDATE SET
                      name = COALESCE(EXCLUDED.name, leads.name),
                      metadata = EXCLUDED.metadata,
                      campaign_id = EXCLUDED.campaign_id,
                      updated_at = NOW()
                    RETURNING (xmax = 0) AS is_new
                `, [phone || null, name, metadata, campaignId]);

                const isNew = result.rows[0]?.is_new;
                if (isNew) {
                    inserted++;
                } else {
                    skipped++;
                }

                if (opportunityScore >= 70) hotLeads++;
            }

            await client.query(`UPDATE campaigns SET status = 'active' WHERE id = $1`, [campaignId]);
            await client.query('COMMIT');
        } catch (e) {
            await client.query('ROLLBACK');
            throw e;
        } finally {
            client.release();
        }

        return NextResponse.json({
            success: true,
            inserted,
            skipped,
            hot_leads: hotLeads,
            total: leads.length
        });

    } catch (error: any) {
        console.error('Scrape error:', error.message);
        return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }
}
