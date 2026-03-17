# 🚀 Quick Start - AI CRM

Guía rápida para levantar el sistema y empezar a usarlo.

---

## ✅ Paso 1: Configurar PostgreSQL

```bash
# Crear la base de datos
psql -U postgres -c "CREATE DATABASE ai_crm;"

# Ejecutar el schema
cd C:\Users\Usuario\.gemini\antigravity\scratch\ai-crm
psql -U postgres -d ai_crm -f database/schema.sql
```

---

## ✅ Paso 2: Configurar Variables de Entorno

Creá un archivo `.env.local` en la raíz del proyecto:

```bash
# Copiar el ejemplo
copy .env.example .env.local
```

Editá `.env.local` y configurá:

```bash
DATABASE_URL=postgresql://postgres:TU_PASSWORD@localhost:5432/ai_crm
```

---

## ✅ Paso 3: Levantar el Dashboard

```bash
# Ya instalamos las dependencias, solo ejecutar:
npm run dev
```

Abrí tu navegador en: **http://localhost:3000**

---

## ✅ Paso 4: Probar el Sistema

### Crear un lead de prueba

Abrí otra terminal y ejecutá:

```bash
curl -X POST http://localhost:3000/api/leads ^
  -H "Content-Type: application/json" ^
  -d "{\"phone\":\"+5491112345678\",\"name\":\"Juan Test\",\"source\":\"whatsapp\",\"intent\":\"automated_onepercent\",\"score\":5}"
```

Refrescá el dashboard y deberías ver el lead en **Pipeline**.

---

## ✅ Paso 5: Conectar con n8n

En tu workflow de WhatsApp existente, agregá un nodo **HTTP Request** después del agente IA:

**Configuración:**
- Method: `POST`
- URL: `http://localhost:3000/api/n8n-webhook`
- Body (JSON):

```json
{
  "phone": "{{ $('Webhook').item.json.body.conversation.messages[0].sender.phone_number }}",
  "message": "{{ $('Agente IA').item.json.output }}",
  "intent": "{{ $('Agente IA').item.json.intent }}",
  "metadata": {
    "responseSpeed": "fast"
  }
}
```

---

## 🎯 Próximos Pasos

1. **Firebase Auth** (opcional por ahora)
2. **Scraping de Instagram** → Ver `SETUP.md` para configurar Apify
3. **Scraping de LinkedIn** → Ver `SETUP.md` para instalar Python scripts
4. **Sistema "Levanta Muertos"** → Crear workflow en n8n

---

## 🆘 Problemas?

### El dashboard no carga
- Verificá que `npm run dev` esté corriendo
- Revisá la consola por errores

### Error de conexión a PostgreSQL
- Verificá que PostgreSQL esté corriendo: `pg_ctl status`
- Verificá la password en `.env.local`

### Los leads no aparecen
- Verificá que el schema se haya ejecutado correctamente
- Revisá la consola del navegador (F12) por errores

---

**Todo listo!** 🎉 Ahora tenés el CRM funcionando localmente.
