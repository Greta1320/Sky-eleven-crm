import { NextRequest, NextResponse } from 'next/server';
import pool from '@/lib/db';

export async function PUT(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    try {
        const leadId = parseInt(params.id);
        const { stage, notes } = await request.json();

        if (!stage) {
            return NextResponse.json({ success: false, error: 'Stage is required' }, { status: 400 });
        }

        // Validate allowed stages to match kanban
        const allowedStages = ['new', 'contacted', 'responded', 'meeting_booked', 'lost'];
        if (!allowedStages.includes(stage)) {
            return NextResponse.json({ success: false, error: 'Invalid stage' }, { status: 400 });
        }

        let query = 'UPDATE leads SET stage = $1, updated_at = NOW()';
        const values: any[] = [stage];

        // Se usa metadata para guardar notas o resumen del agente si las hay
        if (notes) {
            query += `, metadata = jsonb_set(metadata::jsonb, '{agent_notes}', $2::jsonb, true)`;
            values.push(JSON.stringify(notes));
            values.push(leadId);
            query += ' WHERE id = $3 RETURNING *';
        } else {
            values.push(leadId);
            query += ' WHERE id = $2 RETURNING *';
        }

        const result = await pool.query(query, values);

        if (result.rows.length === 0) {
            return NextResponse.json({ success: false, error: 'Lead not found' }, { status: 404 });
        }

        return NextResponse.json({ success: true, data: result.rows[0] });

    } catch (error: any) {
        console.error('Error updating lead stage:', error);
        return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }
}
