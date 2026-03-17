// OnePercent Roadmap - Intent Classification & Routing
export type Intent =
    | 'learn_trading_live'
    | 'automated_onepercent'
    | 'skeptical'
    | 'no_capital'
    | 'already_has_broker'
    | 'wants_fast_money'
    | 'undecided';

export type Stage =
    | 'S0_ENTRY'
    | 'S1A_LIVE'
    | 'S1B_ONEPERCENT'
    | 'S1C_UNDECIDED'
    | 'S1D_SKEPTICAL'
    | 'S1E_NO_CAPITAL'
    | 'S2_NURTURE';

export type SecondaryTag =
    | 'time_poor'
    | 'needs_call'
    | 'beginner'
    | 'experienced';

export interface ScoringRules {
    capital?: number;
    intent?: Intent;
    responseSpeed?: 'fast' | 'normal' | 'slow';
    understandsRisk?: boolean;
    asksProcessQuestions?: boolean;
    wantsGuarantees?: boolean;
    sendsVoiceNote?: boolean;
}

// Scoring según roadmap OnePercent
export function calculateLeadScore(rules: ScoringRules): number {
    let score = 0;

    // Capital >= 300: +3 puntos
    if (rules.capital && rules.capital >= 300) {
        score += 3;
    }

    // Menciona "automatizado" o "no tengo tiempo": +3 puntos
    if (rules.intent === 'automated_onepercent') {
        score += 3;
    }

    // Responde rápido o envía nota de voz: +1 punto
    if (rules.responseSpeed === 'fast' || rules.sendsVoiceNote) {
        score += 1;
    }

    // Entiende riesgo o pregunta sobre proceso: +2 puntos
    if (rules.understandsRisk || rules.asksProcessQuestions) {
        score += 2;
    }

    // Pide ganancias garantizadas o números extremos: -3 puntos
    if (rules.wantsGuarantees || rules.intent === 'wants_fast_money') {
        score -= 3;
    }

    return Math.max(0, score); // No permitir scores negativos
}

// Handoff rules según roadmap
export function getHandoffAction(score: number, intent?: Intent): {
    action: string;
    stage: string;
    message: string;
} {
    // Score >= 6: Tag needs_call + enviar P4_call_invite
    if (score >= 6) {
        return {
            action: 'needs_call',
            stage: 'qualified',
            message: 'Lead calificado - Programar llamada de 10-15 min'
        };
    }

    // Score 3-5: Enter S2_NURTURE
    if (score >= 3 && score <= 5) {
        return {
            action: 'enter_nurture',
            stage: 'nurture',
            message: 'Entrar a secuencia de nurture (24/48/72h)'
        };
    }

    // Score <= 2: Ofrecer Live Level 1-2 gratis
    if (intent === 'no_capital' || score <= 2) {
        return {
            action: 'offer_live_free',
            stage: 'contacted',
            message: 'Ofrecer Live Nivel 1-2 gratis (P5_live_offer)'
        };
    }

    return {
        action: 'continue_conversation',
        stage: 'contacted',
        message: 'Continuar conversación con agente IA'
    };
}

// Clasificar intent desde mensaje del usuario
export function classifyIntent(message: string): Intent {
    const lowerMessage = message.toLowerCase();

    // Wants fast money
    if (
        lowerMessage.includes('garantizado') ||
        lowerMessage.includes('asegurado') ||
        lowerMessage.includes('cuánto gano seguro') ||
        lowerMessage.includes('20% diario') ||
        lowerMessage.includes('hacete rico') ||
        lowerMessage.includes('sin riesgo')
    ) {
        return 'wants_fast_money';
    }

    // Skeptical
    if (
        lowerMessage.includes('estafaron') ||
        lowerMessage.includes('no confío') ||
        lowerMessage.includes('scam') ||
        lowerMessage.includes('fraude') ||
        lowerMessage.includes('mala experiencia')
    ) {
        return 'skeptical';
    }

    // No capital
    if (
        lowerMessage.includes('no tengo plata') ||
        lowerMessage.includes('sin capital') ||
        lowerMessage.includes('no puedo invertir') ||
        lowerMessage.includes('no tengo dinero')
    ) {
        return 'no_capital';
    }

    // Already has broker
    if (
        lowerMessage.includes('ya tengo broker') ||
        lowerMessage.includes('uso binance') ||
        lowerMessage.includes('tengo cuenta en')
    ) {
        return 'already_has_broker';
    }

    // Learn trading live
    if (
        lowerMessage.includes('aprender') ||
        lowerMessage.includes('curso') ||
        lowerMessage.includes('enseñar') ||
        lowerMessage.includes('capacitación') ||
        lowerMessage.includes('estudiar')
    ) {
        return 'learn_trading_live';
    }

    // Automated OnePercent
    if (
        lowerMessage.includes('automatizado') ||
        lowerMessage.includes('no tengo tiempo') ||
        lowerMessage.includes('sin estar encima') ||
        lowerMessage.includes('copytrading') ||
        lowerMessage.includes('bot')
    ) {
        return 'automated_onepercent';
    }

    return 'undecided';
}

// Obtener siguiente stage según intent
export function getNextStage(currentStage: Stage, intent: Intent): Stage {
    if (currentStage === 'S0_ENTRY') {
        switch (intent) {
            case 'learn_trading_live':
                return 'S1A_LIVE';
            case 'automated_onepercent':
                return 'S1B_ONEPERCENT';
            case 'undecided':
                return 'S1C_UNDECIDED';
            case 'skeptical':
                return 'S1D_SKEPTICAL';
            case 'no_capital':
                return 'S1E_NO_CAPITAL';
            default:
                return 'S1C_UNDECIDED';
        }
    }

    return currentStage;
}
