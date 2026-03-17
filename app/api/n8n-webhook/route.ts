import { NextRequest, NextResponse } from 'next/server';
import pool from '@/lib/db';
import {
    calculateLeadScore,
    getHandoffAction,
    classifyIntent,
    getNextStage,
    type Intent,
    type Stage
} from '@/lib/scoring';

// Webhook para recibir datos desde n8n (OnePercent Roadmap)
export async function POST(request: NextRequest) {
    try {
        const body = await request.json();
        const {
            phone,
            message,
            intent: providedIntent,
            stage: currentStage,
            metadata
        } = body;

        if (!phone) {
            return NextResponse.json(
                { success: false, error: 'Phone is required' },
                { status: 400 }
            );
        }

        // Clasificar intent si no viene del agente IA
        let intent: Intent = providedIntent;
        if (!intent && message) {
            intent = classifyIntent(message);
        }

        // Calcular score automático basado en roadmap OnePercent
        const score = calculateLeadScore({
            capital: metadata?.capital,
            intent: intent,
            responseSpeed: metadata?.responseSpeed,
            understandsRisk: metadata?.understandsRisk,
            asksProcessQuestions: metadata?.asksProcessQuestions,
            wantsGuarantees: metadata?.wantsGuarantees,
            sendsVoiceNote: metadata?.sendsVoiceNote,
        });

        // Determinar siguiente stage según roadmap
        const nextStage: Stage = currentStage
            ? getNextStage(currentStage as Stage, intent)
            : 'S0_ENTRY';

        // Obtener acción de handoff
        const handoff = getHandoffAction(score, intent);

        // Preparar tags
        const tags: string[] = [];
        if (intent) tags.push(intent);
        if (metadata?.tags) tags.push(...metadata.tags);
        if (handoff.action === 'needs_call') tags.push('needs_call');

        // Crear o actualizar lead
        const leadResult = await pool.query(
            `INSERT INTO leads (phone, name, source, intent, score, stage, tags, metadata)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
       ON CONFLICT (phone) DO UPDATE SET
         name = COALESCE(EXCLUDED.name, leads.name),
         intent = COALESCE(EXCLUDED.intent, leads.intent),
         score = GREATEST(leads.score, EXCLUDED.score),
         stage = CASE 
           WHEN EXCLUDED.score > leads.score THEN EXCLUDED.stage
           ELSE leads.stage
         END,
         tags = array_cat(leads.tags, EXCLUDED.tags),
         metadata = leads.metadata || EXCLUDED.metadata,
         updated_at = NOW()
       RETURNING *`,
            [
                phone,
                metadata?.name || null,
                metadata?.source || 'whatsapp',
                intent,
                score,
                handoff.stage,
                tags,
                {
                    ...metadata,
                    roadmap_stage: nextStage,
                    last_intent: intent,
                    handoff_action: handoff.action,
                }
            ]
        );

        const lead = leadResult.rows[0];

        // Buscar o crear conversación
        let conversationResult = await pool.query(
            'SELECT * FROM conversations WHERE lead_id = $1 AND channel = $2',
            [lead.id, 'whatsapp']
        );

        let conversation;
        if (conversationResult.rows.length === 0) {
            conversationResult = await pool.query(
                `INSERT INTO conversations (lead_id, channel, last_message_at)
         VALUES ($1, $2, NOW())
         RETURNING *`,
                [lead.id, 'whatsapp']
            );
            conversation = conversationResult.rows[0];
        } else {
            conversation = conversationResult.rows[0];
            await pool.query(
                'UPDATE conversations SET last_message_at = NOW(), unread_count = unread_count + 1 WHERE id = $1',
                [conversation.id]
            );
        }

        // Guardar mensaje
        if (message) {
            await pool.query(
                `INSERT INTO messages (conversation_id, content, direction, message_type, metadata)
         VALUES ($1, $2, $3, $4, $5)`,
                [
                    conversation.id,
                    message,
                    'inbound',
                    metadata?.messageType || 'text',
                    { intent, stage: nextStage }
                ]
            );
        }

        // Respuesta para n8n
        return NextResponse.json({
            success: true,
            data: {
                lead: {
                    id: lead.id,
                    phone: lead.phone,
                    score: lead.score,
                    stage: lead.stage,
                    intent: lead.intent,
                },
                conversation: {
                    id: conversation.id,
                },
                roadmap: {
                    current_stage: nextStage,
                    intent: intent,
                    handoff_action: handoff.action,
                    handoff_message: handoff.message,
                    score: score,
                },
                // Instrucciones para n8n
                next_action: {
                    type: handoff.action,
                    message: handoff.message,
                    should_call: handoff.action === 'needs_call',
                    should_nurture: handoff.action === 'enter_nurture',
                    should_offer_live: handoff.action === 'offer_live_free',
                }
            },
        });
    } catch (error: any) {
        console.error('Error processing n8n webhook:', error);
        return NextResponse.json(
            { success: false, error: error.message },
            { status: 500 }
        );
    }
}
