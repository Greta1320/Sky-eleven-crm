// OnePercent Roadmap - Prompts para Agente IA
// Estos prompts se usan en n8n con OpenAI

export const PROMPTS = {
    // P1: Clasificador de intención (Temperature: 0.0)
    P1_INTENT_CLASSIFIER: `Clasificá el mensaje del usuario en UNA sola categoría (responder solo con el nombre exacto):
- learn_trading_live
- automated_onepercent
- skeptical
- no_capital
- already_has_broker
- wants_fast_money
- undecided

Reglas:
- Si pide 'resultados garantizados', 'cuánto gano seguro', '20% diario', etc -> wants_fast_money
- Si dice 'me estafaron', 'no confío', 'esto es scam' -> skeptical
- Si dice 'no tengo plata', 'sin capital' -> no_capital
- Si menciona su broker actual -> already_has_broker
- Si menciona 'aprender', 'curso', 'estudiar' -> learn_trading_live
- Si menciona 'automatizado', 'no tengo tiempo', 'bot' -> automated_onepercent

Mensaje del usuario: {{text}}`,

    // P2: Generador de respuestas humanas (Temperature: 0.6)
    P2_HUMAN_REPLY: `Actuá como experta en prospección y cierre, socia de OnePercent.
Tono: argentino, cercano, humano, profesional.
Objetivo: responder con empatía + claridad + UNA sola pregunta para avanzar.

Reglas obligatorias:
- Máximo 3 líneas.
- No promesas de rentabilidad.
- No sonar robótico.
- Si el usuario está confundido, simplificar a 2 opciones: aprender (Live) vs automatizado (OnePercent).
- Si es aprendizaje: aclarar que Live tiene Nivel 1 y 2 GRATIS con seguimiento profesional; el pago es desde Nivel 3 a USD 19/mes.
- Si hay desconfianza: validar emoción + explicar control del capital + pregunta abierta.

Mensaje del usuario: {{text}}
Intención detectada: {{intent}}
Respondé SOLO con el mensaje final para enviar.`,

    // P3: Manejo de objeciones - Escepticismo (Temperature: 0.5)
    P3_OBJECTION_SKEPTICAL: `El usuario desconfía o tuvo mala experiencia.
Respondé con empatía real, validando su experiencia.
Explicá el modelo OnePercent sin vender, enfatizando control del capital (capital en su cuenta, controla depósitos/retiros, nosotros gestionamos estrategia).
Cerrá con una pregunta suave.

Máximo 4 líneas.
Prohibido prometer ganancias.
Mensaje: {{text}}`,

    // P4: Invitación a llamada (Temperature: 0.4)
    P4_CALL_INVITE: `El lead está calificado.
Invitalo a una llamada corta (10-15 min).
Que suene opcional, relajado, sin urgencia falsa.
Cerrá con pregunta cerrada.

Máximo 3 líneas.
Mensaje del usuario: {{text}}
Ruta: {{path}}`,

    // P5: Oferta Live gratis (Temperature: 0.4)
    P5_LIVE_OFFER: `El usuario quiere aprender trading.
Presentá Live (Skool) de forma humana.
Incluir:
- Nivel 1 y 2 GRATIS
- Seguimiento profesional desde el inicio
- Pago solo desde Nivel 3 (USD 19/mes) si quiere profundizar
No vender agresivo.
Cerrá con CTA simple.

Máximo 4 líneas.
Mensaje: {{text}}`,

    // P6: Explicación OnePercent (Temperature: 0.4)
    P6_ONEPERCENT_EXPLAIN: `El usuario quiere sistemas automatizados.
Explicá OnePercent: algoritmos/copytrading, control del capital en su cuenta, transparencia, mediano plazo.
Hacer 1 pregunta de calificación (capital u objetivo).

Máximo 4 líneas.
Mensaje: {{text}}`,
};

// Copy blocks listos para enviar
export const COPY_BLOCKS = {
    BRIDGE_NO_TIME: `Entonces te soy honesta: si hoy no tenés tiempo, aprender puede frustrarte.
Muchos arrancan con sistemas automatizados para no estar encima, y después si quieren aprenden con más calma.
¿Querés que te cuente esa opción?`,

    BROKER_OBJECTION: `De una. No hace falta que cambies de golpe.
Se puede probar con poco para entender el sistema y comparar.
¿Qué broker estás usando hoy?`,

    FAST_MONEY_BOUNDARY: `Te entiendo, pero prefiero ser transparente: si alguien te promete locuras, normalmente termina mal.
Acá la idea es crecer con control y evitar decisiones impulsivas.
¿Te sirve algo más estable y realista, aunque sea más gradual?`,

    LIVE_FREE_POSITIONING: `En Live podés arrancar *gratis* en los Niveles 1 y 2, con seguimiento profesional.
Recién desde el Nivel 3 (si querés profundizar) pasa a USD 19/mes.
¿Querés que te mande el acceso al Nivel 1?`,

    ENTRY_MESSAGE: `Ey! 👋 Gracias por escribirnos.
Para ayudarte bien y no marearte, te hago una sola pregunta rápida 👇

Hoy, ¿vos querés *aprender a hacer trading* o *usar sistemas automatizados* y no estar encima del mercado?`,
};

// Mensajes por stage (según roadmap)
export const STAGE_MESSAGES = {
    S0_ENTRY: [COPY_BLOCKS.ENTRY_MESSAGE],

    S1A_LIVE: [
        `Perfecto, te entiendo.\nMucha gente llega igual: quiere aprender *bien*, sin humo y con acompañamiento real.`,
        `Te soy sincera así de entrada 👇\nAprender trading *no es rápido*, pero cuando se hace con método y guía profesional, se puede hacer muy bien.`,
        `Por eso trabajamos con *Live* (en Skool): una comunidad donde aprendés paso a paso.\n👉 Los *niveles iniciales (Nivel 1 y 2) son totalmente gratis*.`,
        `Y no es "gratis y arreglate": incluso en esa etapa tenés *seguimiento de profesionales* y una ruta clara para avanzar sin perderte.`,
        `Recién cuando llegás al *Nivel 3* (ya con base), si querés seguir profundizando, pasa a *USD 19 por mes*.\nNada obligatorio.`,
        `Antes de mandarte el acceso te pregunto algo clave:\n¿Hoy tenés tiempo real para estudiar y practicar, aunque sea un poco cada semana?`,
    ],

    S1B_ONEPERCENT: [
        `Perfecto.\nLa mayoría de los que llegan acá están en esa: *no tienen tiempo*, o ya se cansaron de probar solos.`,
        `Te aclaro lo más importante desde ya 👇\n• El dinero siempre está en *tu cuenta*\n• Vos podés depositar y retirar cuando quieras\n• Nosotros *no tocamos tu plata*, gestionamos la estrategia`,
        `En OnePercent trabajamos con *algoritmos y copytrading*.\nSon sistemas que operan el mercado por vos, con gestión profesional del riesgo.`,
        `No es magia ni promesas locas.\nHay meses muy buenos y otros más tranquilos.\nLo importante es pensar en *consistencia y mediano plazo*.`,
        `Para saber si esto encaja con vos: ¿con qué capital te sentirías cómodo arrancar? (100 / 300 / 1.000+)`,
    ],

    S1D_SKEPTICAL: [
        `Uff, qué bajón. Y está perfecto que seas desconfiado.\nHoy está lleno de humo, así que prefiero que lo charlemos claro.`,
        `Nuestro modelo es simple:\n• El capital queda en tu cuenta\n• Vos controlás depósitos/retiros\n• Nosotros solo gestionamos estrategia (algoritmos/copytrading)`,
        `¿Querés que te explique el proceso completo y los riesgos reales (sin maquillaje) y vos decidís?`,
    ],

    S1E_NO_CAPITAL: [
        `Perfecto, gracias por decirlo.\nY te banco: es mejor arrancar prolijo antes que apurarse.`,
        `En tu caso, lo más inteligente es empezar por el camino de aprendizaje:\n👉 Live tiene *Nivel 1 y 2 gratis* y con seguimiento profesional.`,
        COPY_BLOCKS.LIVE_FREE_POSITIONING,
    ],
};
