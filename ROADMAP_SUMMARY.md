# OnePercent Roadmap - Resumen de Integración

## ✅ Lo que se integró

### 1. Sistema de Clasificación de Intención (Intent Classifier)

**Archivo:** `lib/scoring.ts`

**7 Intents detectados automáticamente:**
- `learn_trading_live` - Quiere aprender trading
- `automated_onepercent` - Quiere sistemas automatizados
- `skeptical` - Desconfianza / mala experiencia
- `no_capital` - No tiene capital para invertir
- `already_has_broker` - Ya tiene broker
- `wants_fast_money` - Busca ganancias garantizadas
- `undecided` - No sabe qué quiere

### 2. Stages del Roadmap

- `S0_ENTRY` - Primera interacción
- `S1A_LIVE` - Camino aprendizaje (Live/Skool)
- `S1B_ONEPERCENT` - Camino automatizado
- `S1C_UNDECIDED` - Indeciso
- `S1D_SKEPTICAL` - Desconfianza
- `S1E_NO_CAPITAL` - Sin capital
- `S2_NURTURE` - Seguimiento 24/48/72h

### 3. Scoring Rules (exactas del roadmap)

| Condición | Puntos |
|-----------|--------|
| Capital >= 300 | +3 |
| Intent = "automated_onepercent" | +3 |
| Responde rápido o nota de voz | +1 |
| Entiende riesgo / Pregunta proceso | +2 |
| Pide garantías / "wants_fast_money" | -3 |

### 4. Handoff Automático

- **Score >= 6** → `needs_call` → Programar llamada 10-15 min
- **Score 3-5** → `enter_nurture` → Secuencia 24/48/72h
- **Score <= 2** → `offer_live_free` → Live Nivel 1-2 gratis

### 5. Prompts para n8n (OpenAI)

**Archivo:** `lib/prompts.ts`

- **P1_INTENT_CLASSIFIER** (temp: 0.0) - Clasificar mensaje
- **P2_HUMAN_REPLY** (temp: 0.6) - Respuesta humana general
- **P3_OBJECTION_SKEPTICAL** (temp: 0.5) - Manejo de objeciones
- **P4_CALL_INVITE** (temp: 0.4) - Invitación a llamada
- **P5_LIVE_OFFER** (temp: 0.4) - Oferta Live gratis
- **P6_ONEPERCENT_EXPLAIN** (temp: 0.4) - Explicación OnePercent

### 6. Webhook n8n Actualizado

**Archivo:** `app/api/n8n-webhook/route.ts`

**Ahora procesa:**
- Clasificación automática de intent (si no viene de n8n)
- Cálculo de score según roadmap
- Progresión de stages (S0 → S1A/S1B/etc)
- Handoff actions (call/nurture/offer_live)
- Tags automáticos (`needs_call`, intent, etc)

**Respuesta a n8n incluye:**
```json
{
  "roadmap": {
    "current_stage": "S1B_ONEPERCENT",
    "intent": "automated_onepercent",
    "handoff_action": "needs_call",
    "score": 6
  },
  "next_action": {
    "should_call": true,
    "should_nurture": false,
    "should_offer_live": false
  }
}
```

---

## 📋 Cómo Usarlo

### En n8n:

1. **Agregar nodo OpenAI** con P1_INTENT_CLASSIFIER
2. **Agregar Switch** para routing por intent
3. **Agregar nodos OpenAI** para cada ruta (P2-P6)
4. **HTTP Request** a `/api/n8n-webhook` con intent + metadata
5. **Switch** según `next_action` del CRM
6. **Enviar respuesta** por WhatsApp

### Ejemplo de llamada al webhook:

```bash
curl -X POST http://localhost:3000/api/n8n-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+5491112345678",
    "message": "Quiero algo automatizado, no tengo tiempo",
    "metadata": {
      "name": "Juan",
      "capital": 500,
      "sendsVoiceNote": false,
      "responseSpeed": "fast"
    }
  }'
```

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "lead": {
      "score": 6,
      "intent": "automated_onepercent",
      "stage": "qualified"
    },
    "roadmap": {
      "current_stage": "S1B_ONEPERCENT",
      "handoff_action": "needs_call"
    },
    "next_action": {
      "should_call": true
    }
  }
}
```

---

## 🎯 Próximos Pasos

1. **Importar workflow a n8n** con los prompts
2. **Probar clasificación** con mensajes de prueba
3. **Activar nurture sequence** (24/48/72h)
4. **Monitorear handoffs** en el dashboard

---

**Ver guía completa:** `N8N_ROADMAP_INTEGRATION.md`
