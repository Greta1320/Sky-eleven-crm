import { NextRequest, NextResponse } from 'next/server';
import pool from '@/lib/db';

export async function PATCH(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    try {
        const body = await request.json();
        const { name, email, intent, score, stage, tags, metadata } = body;

        const updates: string[] = [];
        const values: any[] = [];
        let paramIndex = 1;

        if (name !== undefined) {
            updates.push(`name = $${paramIndex}`);
            values.push(name);
            paramIndex++;
        }
        if (email !== undefined) {
            updates.push(`email = $${paramIndex}`);
            values.push(email);
            paramIndex++;
        }
        if (intent !== undefined) {
            updates.push(`intent = $${paramIndex}`);
            values.push(intent);
            paramIndex++;
        }
        if (score !== undefined) {
            updates.push(`score = $${paramIndex}`);
            values.push(score);
            paramIndex++;
        }
        if (stage !== undefined) {
            updates.push(`stage = $${paramIndex}`);
            values.push(stage);
            paramIndex++;
        }
        if (tags !== undefined) {
            updates.push(`tags = $${paramIndex}`);
            values.push(tags);
            paramIndex++;
        }
        if (metadata !== undefined) {
            updates.push(`metadata = $${paramIndex}`);
            values.push(metadata);
            paramIndex++;
        }

        if (updates.length === 0) {
            return NextResponse.json(
                { success: false, error: 'No fields to update' },
                { status: 400 }
            );
        }

        updates.push(`updated_at = NOW()`);
        values.push(params.id);

        const query = `UPDATE leads SET ${updates.join(', ')} WHERE id = $${paramIndex} RETURNING *`;

        const result = await pool.query(query, values);

        if (result.rows.length === 0) {
            return NextResponse.json(
                { success: false, error: 'Lead not found' },
                { status: 404 }
            );
        }

        return NextResponse.json({
            success: true,
            data: result.rows[0],
        });
    } catch (error: any) {
        console.error('Error updating lead:', error);
        return NextResponse.json(
            { success: false, error: error.message },
            { status: 500 }
        );
    }
}

export async function DELETE(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    try {
        const result = await pool.query(
            'DELETE FROM leads WHERE id = $1 RETURNING *',
            [params.id]
        );

        if (result.rows.length === 0) {
            return NextResponse.json(
                { success: false, error: 'Lead not found' },
                { status: 404 }
            );
        }

        return NextResponse.json({
            success: true,
            message: 'Lead deleted successfully',
        });
    } catch (error: any) {
        console.error('Error deleting lead:', error);
        return NextResponse.json(
            { success: false, error: error.message },
            { status: 500 }
        );
    }
}
