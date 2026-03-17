# OnePercent Roadmap - Integración con n8n

Guía completa para conectar el agente IA de OnePercent con el CRM usando el roadmap de ventas.

---

## 🎯 Arquitectura del Sistema

```
WhatsApp → Evolution API → n8n → Agente IA (OpenAI) → CRM Dashboard
                                      ↓
                                  PostgreSQL
                                      ↓
                              Lead Scoring + Routing
```

---

## 📋 Configuración del Workflow n8n

### Nodos Necesarios

1. **Webhook** - Recibe mensajes de WhatsApp
2. **Function** - Extrae datos del mensaje
3. **OpenAI Chat** - Clasificador de intención (P1)
4. **Switch** - Routing según intent
5. **OpenAI Chat** - Generador de respuesta (P2-P6)
6. **HTTP Request** - Envía a CRM Dashboard
7. **Evolution API** - Envía respuesta por WhatsApp

---

## 🔧 Paso 1: Nodo Clasificador de Intención

### OpenAI Chat - P1_INTENT_CLASSIFIER

**Configuración:**
```json
{
  "model": "gpt-4o",
  "temperature": 0.0,
  "messages": [
    {
      "role": "system",
      "content": "Clasificá el mensaje del usuario en UNA sola categoría (responder solo con el nombre exacto):\n- learn_trading_live\n- automated_onepercent\n- skeptical\n- no_capital\n- already_has_broker\n- wants_fast_money\n- undecided\n\nReglas:\n- Si pide 'resultados garantizados', 'cuánto gano seguro', '20% diario', etc -> wants_fast_money\n- Si dice 'me estafaron', 'no confío', 'esto es scam' -> skeptical\n- Si dice 'no tengo plata', 'sin capital' -> no_capital\n- Si menciona su broker actual -> already_has_broker\n- Si menciona 'aprender', 'curso', 'estudiar' -> learn_trading_live\n- Si menciona 'automatizado', 'no tengo tiempo', 'bot' -> automated_onepercent\n\nMensaje del usuario: {{ $json.message }}"
    }
  ]
}
```

**Output:** Guardar en variable `intent`

---

## 🔀 Paso 2: Switch - Routing por Intent

### Configuración del Switch

```javascript
// Condiciones:
1. intent === 'learn_trading_live' → Ir a S1A_LIVE
2. intent === 'automated_onepercent' → Ir a S1B_ONEPERCENT
3. intent === 'skeptical' → Ir a S1D_SKEPTICAL
4. intent === 'no_capital' → Ir a S1E_NO_CAPITAL
5. intent === 'undecided' → Ir a S1C_UNDECIDED
6. intent === 'wants_fast_money' → Ir a FAST_MONEY_BOUNDARY
7. intent === 'already_has_broker' → Ir a BROKER_OBJECTION
```

---

## 💬 Paso 3: Generadores de Respuesta por Ruta

### Ruta A: Learn Trading Live (S1A_LIVE)

**OpenAI Chat - P5_LIVE_OFFER**

```json
{
  "model": "gpt-4o",
  "temperature": 0.4,
  "messages": [
    {
      "role": "system",
      "content": "El usuario quiere aprender trading.\nPresentá Live (Skool) de forma humana.\nIncluir:\n- Nivel 1 y 2 GRATIS\n- Seguimiento profesional desde el inicio\n- Pago solo desde Nivel 3 (USD 19/mes) si quiere profundizar\nNo vender agresivo.\nCerrá con CTA simple.\n\nMáximo 4 líneas.\nMensaje: {{ $json.message }}"
    }
  ]
}
```

### Ruta B: OnePercent Automatizado (S1B_ONEPERCENT)

**OpenAI Chat - P6_ONEPERCENT_EXPLAIN**

```json
{
  "model": "gpt-4o",
  "temperature": 0.4,
  "messages": [
    {
      "role": "system",
      "content": "El usuario quiere sistemas automatizados.\nExplicá OnePercent: algoritmos/copytrading, control del capital en su cuenta, transparencia, mediano plazo.\nHacer 1 pregunta de calificación (capital u objetivo).\n\nMáximo 4 líneas.\nMensaje: {{ $json.message }}"
    }
  ]
}
```

### Ruta D: Skeptical (S1D_SKEPTICAL)

**OpenAI Chat - P3_OBJECTION_SKEPTICAL**

```json
{
  "model": "gpt-4o",
  "temperature": 0.5,
  "messages": [
    {
      "role": "system",
      "content": "El usuario desconfía o tuvo mala experiencia.\nRespondé con empatía real, validando su experiencia.\nExplicá el modelo OnePercent sin vender, enfatizando control del capital (capital en su cuenta, controla depósitos/retiros, nosotros gestionamos estrategia).\nCerrá con una pregunta suave.\n\nMáximo 4 líneas.\nProhibido prometer ganancias.\nMensaje: {{ $json.message }}"
    }
  ]
}
```

---

## 📊 Paso 4: HTTP Request - Enviar a CRM

### Configuración

**URL:** `http://localhost:3000/api/n8n-webhook`  
**Method:** POST  
**Body:**

```json
{
  "phone": "{{ $('Webhook').item.json.body.conversation.messages[0].sender.phone_number }}",
  "message": "{{ $('Webhook').item.json.body.conversation.messages[0].text }}",
  "intent": "{{ $('P1_Intent_Classifier').item.json.choices[0].message.content }}",
  "stage": "{{ $node['Switch'].json.stage }}",
  "metadata": {
    "name": "{{ $('Webhook').item.json.body.conversation.contact.name }}",
    "source": "whatsapp",
    "messageType": "{{ $('Webhook').item.json.body.conversation.messages[0].type }}",
    "sendsVoiceNote": "{{ $('Webhook').item.json.body.conversation.messages[0].type === 'audio' }}",
    "responseSpeed": "fast"
  }
}
```

### Respuesta del CRM

El CRM responde con:

```json
{
  "success": true,
  "data": {
    "lead": {
      "id": "uuid",
      "score": 5,
      "stage": "qualified",
      "intent": "automated_onepercent"
    },
    "roadmap": {
      "current_stage": "S1B_ONEPERCENT",
      "handoff_action": "needs_call",
      "handoff_message": "Lead calificado - Programar llamada de 10-15 min"
    },
    "next_action": {
      "type": "needs_call",
      "should_call": true,
      "should_nurture": false
    }
  }
}
```

---

## 🎬 Paso 5: Acciones según Handoff

### Switch - Handoff Actions

```javascript
// Condiciones basadas en respuesta del CRM:
1. next_action.should_call === true → Enviar P4_CALL_INVITE
2. next_action.should_nurture === true → Agregar a cola S2_NURTURE
3. next_action.should_offer_live === true → Enviar P5_LIVE_OFFER
4. default → Continuar conversación normal
```

### P4_CALL_INVITE (Score >= 6)

```json
{
  "model": "gpt-4o",
  "temperature": 0.4,
  "messages": [
    {
      "role": "system",
      "content": "El lead está calificado.\nInvitalo a una llamada corta (10-15 min).\nQue suene opcional, relajado, sin urgencia falsa.\nCerrá con pregunta cerrada.\n\nMáximo 3 líneas.\nMensaje del usuario: {{ $json.message }}\nRuta: {{ $json.intent }}"
    }
  ]
}
```

---

## 🔄 Sistema de Nurture (S2_NURTURE)

### Configuración de Delays

Para leads con score 3-5, crear secuencia de follow-ups:

**Workflow separado: "Nurture Sequence"**

1. **Trigger:** Webhook desde CRM cuando `next_action.should_nurture === true`
2. **Wait 24h** → Enviar mensaje T1
3. **Wait 48h** → Enviar mensaje T2
4. **Wait 72h** → Enviar mensaje T3

### Mensajes de Nurture

**T1 (24h):**
```
Te dejo una pregunta para orientarte bien:
¿Hoy te conviene más *aprender (Live gratis)* o *automatizar (OnePercent)*?
```

**T2 (48h):**
```
Dato honesto: lo que más ayuda es tener un plan simple y sostenerlo.
¿Tu objetivo es *aprender*, *ingreso extra* o *largo plazo*?
```

**T3 (72h):**
```
Último ping y no te jodo más 😄
¿Querés que lo veamos 10 min y te dejo claridad de qué camino te conviene?
```

---

## 📈 Lead Scoring en Tiempo Real

El CRM calcula automáticamente el score basado en:

| Condición | Puntos |
|-----------|--------|
| Capital >= 300 | +3 |
| Intent = "automated_onepercent" | +3 |
| Respuesta rápida o nota de voz | +1 |
| Entiende riesgo / Pregunta proceso | +2 |
| Pide garantías / "wants_fast_money" | -3 |

### Handoff Automático

- **Score >= 6** → Tag `needs_call` + Notificar para llamada
- **Score 3-5** → Entrar a nurture (24/48/72h)
- **Score <= 2** → Ofrecer Live gratis

---

## 🧪 Testing del Workflow

### 1. Test de Clasificación

Enviar mensaje de prueba:
```
"Quiero aprender a hacer trading"
```

**Resultado esperado:**
- Intent: `learn_trading_live`
- Stage: `S1A_LIVE`
- Respuesta: Mensaje sobre Live gratis

### 2. Test de Scoring

Enviar mensaje:
```
"Tengo 500 USD y quiero algo automatizado porque no tengo tiempo"
```

**Resultado esperado:**
- Intent: `automated_onepercent`
- Score: 6 (capital +3, intent +3)
- Action: `needs_call`
- Respuesta: Invitación a llamada

### 3. Test de Objeción

Enviar mensaje:
```
"Me estafaron con otro sistema, no confío"
```

**Resultado esperado:**
- Intent: `skeptical`
- Stage: `S1D_SKEPTICAL`
- Respuesta: Empatía + explicación de control de capital

---

## 🔗 Variables de Entorno Necesarias

En tu n8n, configurar:

```bash
CRM_WEBHOOK_URL=http://localhost:3000/api/n8n-webhook
OPENAI_API_KEY=sk-...
EVOLUTION_API_URL=https://tu-evolution-api.com
```

---

## 📊 Monitoreo en el Dashboard

Una vez configurado, podés ver en tiempo real:

- **Pipeline:** Leads organizados por stage
- **Métricas:** Score promedio, tasa de conversión
- **Conversaciones:** Historial completo con intent detectado
- **Handoffs:** Leads que necesitan llamada (score >= 6)

---

## 🚀 Próximos Pasos

1. ✅ Importar workflow base a n8n
2. ✅ Configurar credenciales de OpenAI
3. ✅ Conectar Evolution API
4. ✅ Probar con 5 mensajes de prueba
5. ✅ Activar workflow de nurture
6. ✅ Monitorear primeros leads reales

---

**¿Necesitás el workflow completo en JSON para importar directo a n8n?** Avisame y te lo armo.
