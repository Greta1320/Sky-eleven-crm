import { NextRequest, NextResponse } from 'next/server';
import pool from '@/lib/db';

export async function POST(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    try {
        const campaignId = parseInt(params.id);
        const { leadId } = await request.json();

        let query = 'SELECT * FROM leads WHERE campaign_id = $1';
        let queryParams: any[] = [campaignId];

        if (leadId) {
            query += ' AND id = $2';
            queryParams.push(leadId);
        } else {
            query += " AND stage = 'new' LIMIT 1"; // Pick one random uncontacted lead
        }

        const result = await pool.query(query, queryParams);

        if (result.rows.length === 0) {
            return NextResponse.json({ success: false, error: 'No suitable lead found to send' }, { status: 404 });
        }

        const lead = result.rows[0];

        // Send to n8n
        const webhookUrl = process.env.N8N_PROSPECTOR_WEBHOOK_URL || 'http://localhost:5678/webhook-test/prospector';

        const n8nResponse = await fetch(webhookUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'outreach',
                campaign_id: campaignId,
                lead: {
                    id: lead.id,
                    name: lead.name,
                    phone: lead.phone,
                    metadata: typeof lead.metadata === 'string' ? JSON.parse(lead.metadata) : lead.metadata
                }
            })
        });

        if (!n8nResponse.ok) {
            throw new Error(`n8n webhook failed with status ${n8nResponse.status}`);
        }

        // Update lead stage to contacted temporarily
        if (leadId) {
            await pool.query("UPDATE leads SET stage = 'contacted' WHERE id = $1", [lead.id]);
        }

        return NextResponse.json({ success: true, message: 'Webhook sent successfully', lead_sent: lead.id });

    } catch (error: any) {
        console.error('Error sending webhook:', error);
        return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }
}
