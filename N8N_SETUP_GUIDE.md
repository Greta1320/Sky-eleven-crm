# Guía de Configuración: n8n + CRM Integration

## 🎯 Objetivo
Conectar tu workflow de WhatsApp con el CRM para que los mensajes se guarden automáticamente y el agente IA use el roadmap OnePercent.

---

## 📋 Paso 1: Importar el Workflow a n8n

1. **Abrí n8n** en tu navegador
2. **Click en "+" → "Import from File"**
3. **Seleccioná:** `C:\Users\Usuario\.gemini\antigravity\scratch\ai-crm\n8n-workflows\whatsapp-crm-integrated.json`
4. **Click en "Import"**

---

## 🔧 Paso 2: Configurar Credenciales

### OpenAI API

1. **Click en cualquier nodo "P1 - Intent Classifier"**
2. **En "Credentials" → Click en "Create New"**
3. **Nombre:** `OpenAI Account`
4. **API Key:** Tu API key de OpenAI
5. **Save**

**Aplicar la misma credencial a todos los nodos de OpenAI:**
- P1 - Intent Classifier
- P3 - Objection Skeptical
- P4 - Call Invite
- P5 - Live Offer
- P6 - OnePercent Explain

---

## 🔗 Paso 3: Configurar URLs

### Nodo "Send to CRM"

**URL actual:** `http://localhost:3001/api/n8n-webhook`

**Si tu CRM está en otro servidor:**
- Cambiar a: `https://tu-dominio.com/api/n8n-webhook`

### Nodos "Send WhatsApp Response" y "Send Call Invite"

**Reemplazar:**
- `YOUR_EVOLUTION_API_URL` → URL de tu Evolution API (ej: `https://evolution.example.com`)
- `YOUR_INSTANCE` → Nombre de tu instancia (ej: `onepercent`)
- `YOUR_EVOLUTION_API_KEY` → Tu API key de Evolution

**Ejemplo final:**
```
URL: https://evolution.example.com/message/sendText/onepercent
Header: apikey: tu-api-key-aqui
```

---

## 📡 Paso 4: Configurar Webhook de Evolution API

Tu Evolution API debe enviar los mensajes entrantes al webhook de n8n.

**URL del webhook n8n:**
```
https://tu-n8n-url.com/webhook/whatsapp-incoming
```

**En Evolution API, configurar:**
1. Ir a configuración de webhooks
2. Agregar webhook para "message.upsert"
3. URL: La URL del webhook de n8n
4. Eventos: `message.upsert`

---

## 🧪 Paso 5: Probar el Flujo Completo

### Test 1: Mensaje de aprendizaje

**Enviar por WhatsApp:**
```
Quiero aprender a hacer trading
```

**Resultado esperado:**
1. ✅ n8n recibe el mensaje
2. ✅ OpenAI clasifica intent: `learn_trading_live`
3. ✅ Se guarda en CRM con stage `S1A_LIVE`
4. ✅ Responde con oferta de Live (Nivel 1-2 gratis)
5. ✅ Lead aparece en dashboard: http://localhost:3001/pipeline

### Test 2: Mensaje de automatización

**Enviar por WhatsApp:**
```
Tengo 500 USD y quiero algo automatizado, no tengo tiempo
```

**Resultado esperado:**
1. ✅ Intent: `automated_onepercent`
2. ✅ Score: 6 (capital +3, intent +3)
3. ✅ Stage: `S1B_ONEPERCENT`
4. ✅ Responde con explicación de OnePercent
5. ✅ **Segundo mensaje automático:** Invitación a llamada (porque score >= 6)

### Test 3: Mensaje escéptico

**Enviar por WhatsApp:**
```
Me estafaron con otro sistema, no confío
```

**Resultado esperado:**
1. ✅ Intent: `skeptical`
2. ✅ Stage: `S1D_SKEPTICAL`
3. ✅ Responde con empatía + explicación de control de capital

---

## 📊 Paso 6: Verificar en el Dashboard

**Abrí:** http://localhost:3001/pipeline

Deberías ver los leads creados en las columnas correspondientes:
- **Nuevo:** Leads sin clasificar
- **Contactado:** Score <= 2
- **Calificado:** Score 3-5
- **Llamada:** Score >= 6
- **Cerrado:** Leads convertidos

---

## 🔍 Debugging

### Si no llegan mensajes al CRM:

1. **Verificar que el servidor Next.js esté corriendo:**
   ```powershell
   cd C:\Users\Usuario\.gemini\antigravity\scratch\ai-crm
   npm run dev
   ```

2. **Verificar logs de n8n:**
   - Click en "Executions" en n8n
   - Ver el último execution
   - Revisar cada nodo para ver dónde falló

3. **Verificar conexión a PostgreSQL:**
   - Abrir pgAdmin
   - Verificar que la base de datos `ai_crm` existe
   - Verificar que hay tablas creadas

### Si OpenAI no responde:

1. **Verificar API Key:**
   - Ir a https://platform.openai.com/api-keys
   - Verificar que la key es válida
   - Verificar que tenés créditos

2. **Verificar modelo:**
   - El workflow usa `gpt-4o`
   - Si no tenés acceso, cambiar a `gpt-4` o `gpt-3.5-turbo`

---

## 🚀 Próximos Pasos

Una vez que el flujo básico funcione:

1. **Agregar Guardian API** para rate limiting (opcional)
2. **Crear workflow de Nurture** (24/48/72h)
3. **Agregar prospecting automático** desde Instagram/LinkedIn
4. **Configurar notificaciones** para leads con score >= 6

---

## 📝 Notas Importantes

- **El CRM debe estar corriendo** en http://localhost:3001 para que funcione
- **PostgreSQL debe estar activo** (servicio corriendo)
- **Evolution API debe estar configurada** para enviar webhooks a n8n
- **OpenAI API debe tener créditos** disponibles

---

**¿Tenés algún error o duda?** Revisá los logs de n8n y el terminal de Next.js para ver mensajes de error específicos.
