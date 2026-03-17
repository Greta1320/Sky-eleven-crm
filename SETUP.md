# 🚀 AI CRM - Guía de Instalación

Esta guía te llevará paso a paso para montar el sistema completo.

---

## 📋 Requisitos Previos

Antes de empezar, asegurate de tener instalado:

- ✅ **Node.js 18+** ([descargar](https://nodejs.org/))
- ✅ **PostgreSQL 14+** ([descargar](https://www.postgresql.org/download/))
- ✅ **Python 3.10+** ([descargar](https://www.python.org/downloads/))
- ✅ **Git** ([descargar](https://git-scm.com/))

---

## Paso 1: Configurar PostgreSQL

### 1.1 Crear la base de datos

Abrí una terminal y ejecutá:

```bash
# Conectarse a PostgreSQL
psql -U postgres

# Crear la base de datos
CREATE DATABASE ai_crm;

# Salir
\q
```

### 1.2 Ejecutar el schema

```bash
# Desde la carpeta del proyecto
cd C:\Users\Usuario\.gemini\antigravity\scratch\ai-crm

# Ejecutar el schema
psql -U postgres -d ai_crm -f database/schema.sql
```

### 1.3 Verificar que se crearon las tablas

```bash
psql -U postgres -d ai_crm -c "\dt"
```

Deberías ver: `leads`, `conversations`, `messages`, `campaigns`, `follow_ups`

---

## Paso 2: Configurar Next.js Dashboard

### 2.1 Instalar dependencias

```bash
cd C:\Users\Usuario\.gemini\antigravity\scratch\ai-crm
npm install
```

### 2.2 Configurar variables de entorno

Creá un archivo `.env.local` en la raíz del proyecto:

```bash
# Database
DATABASE_URL=postgresql://postgres:tu_password@localhost:5432/ai_crm

# Firebase (lo configuraremos después)
NEXT_PUBLIC_FIREBASE_API_KEY=
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=
NEXT_PUBLIC_FIREBASE_PROJECT_ID=

# n8n Webhook
N8N_WEBHOOK_URL=https://tu-n8n-url.railway.app/webhook/ai-crm
```

### 2.3 Ejecutar el servidor de desarrollo

```bash
npm run dev
```

Abrí tu navegador en: `http://localhost:3000`

---

## Paso 3: Configurar Firebase (Autenticación)

### 3.1 Crear proyecto en Firebase

1. Andá a [Firebase Console](https://console.firebase.google.com/)
2. Click en "Agregar proyecto"
3. Nombre: `ai-crm`
4. Desactivar Google Analytics (opcional)

### 3.2 Habilitar autenticación

1. En el menú lateral → **Authentication**
2. Click en "Comenzar"
3. Habilitar **Email/Password**

### 3.3 Obtener credenciales

1. En el menú lateral → **Configuración del proyecto** (ícono de engranaje)
2. En "Tus apps" → Click en el ícono `</>`
3. Nombre de la app: `ai-crm-dashboard`
4. Copiar las credenciales y pegarlas en `.env.local`

---

## Paso 4: Configurar Scraping de Instagram

### 4.1 Verificar cuenta de Instagram Business

1. Abrí Instagram en tu celular
2. Andá a **Configuración** → **Cuenta**
3. Si dice "Cuenta personal", cambiala a **Cuenta profesional**
4. Elegí categoría: "Servicios financieros" o "Educación"

### 4.2 Conectar con Facebook Page

1. Abrí Facebook en tu navegador
2. Andá a **Configuración** → **Instagram**
3. Click en "Conectar cuenta"
4. Seguí los pasos para vincular

### 4.3 Configurar Apify (free tier)

1. Andá a [Apify](https://apify.com/)
2. Crear cuenta gratuita
3. Ir a **Settings** → **Integrations**
4. Copiar tu **API Token**
5. Guardalo en `.env.local`:

```bash
APIFY_API_TOKEN=tu_token_aqui
```

### 4.4 Instalar dependencias de Python

```bash
cd C:\Users\Usuario\.gemini\antigravity\scratch\ai-crm
pip install apify-client psycopg2-binary python-dotenv
```

---

## Paso 5: Configurar Scraping de LinkedIn

### 5.1 Instalar librería de scraping

```bash
pip install linkedin-scraper selenium webdriver-manager
```

### 5.2 Configurar Skrapp.io (50 emails gratis/mes)

1. Andá a [Skrapp.io](https://www.skrapp.io/)
2. Crear cuenta gratuita
3. Instalar extensión de Chrome
4. Login en la extensión

---

## Paso 6: Conectar con n8n

### 6.1 Modificar workflow existente

Tu workflow actual de WhatsApp ya está funcionando. Ahora vamos a agregar un nodo para sincronizar con el CRM:

1. Abrí n8n
2. Abrí tu workflow de WhatsApp
3. Agregá un nodo **HTTP Request** después del nodo "Agente IA"
4. Configuralo así:

```
Method: POST
URL: http://localhost:3000/api/n8n-webhook
Body:
{
  "phone": "{{ $('Webhook').item.json.body.conversation.messages[0].sender.phone_number }}",
  "message": "{{ $('Agente IA').item.json.output }}",
  "intent": "{{ $('Agente IA').item.json.intent }}",
  "score": "{{ $('Agente IA').item.json.score }}"
}
```

---

## Paso 7: Verificar que todo funciona

### 7.1 Test de base de datos

```bash
psql -U postgres -d ai_crm -c "SELECT * FROM leads;"
```

### 7.2 Test de dashboard

1. Abrí `http://localhost:3000`
2. Deberías ver la pantalla de login
3. Creá una cuenta de prueba

### 7.3 Test de integración n8n

1. Enviá un mensaje de WhatsApp a tu número de prueba
2. Verificá que aparece en el dashboard en **Conversaciones**

---

## 🎯 Próximos Pasos

Una vez que todo esté funcionando:

1. ✅ Ejecutar primer scraping de Instagram (10 leads de prueba)
2. ✅ Ejecutar primer scraping de LinkedIn (5 leads de prueba)
3. ✅ Configurar sistema "Levanta Muertos"
4. ✅ Probar flujo completo: Lead → Conversación → Cierre

---

## 🆘 Problemas Comunes

### Error: "Cannot connect to PostgreSQL"
- Verificá que PostgreSQL esté corriendo: `pg_ctl status`
- Verificá la password en `.env.local`

### Error: "Module not found"
- Ejecutá `npm install` de nuevo
- Verificá que estás en la carpeta correcta

### Error: "Firebase not initialized"
- Verificá que copiaste bien las credenciales en `.env.local`
- Reiniciá el servidor: `npm run dev`

---

## 📞 Soporte

Si tenés algún problema, avisame y lo resolvemos juntos.
