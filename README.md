# AI CRM - Sistema de Prospección con IA

Sistema completo de CRM con inteligencia artificial para prospección multi-canal (Instagram, LinkedIn, WhatsApp), automatización de seguimiento y gestión centralizada de leads.

## 🚀 Características

- ✅ **Dashboard Web** con Next.js + TypeScript + TailwindCSS
- ✅ **Base de Datos PostgreSQL** con schema completo
- ✅ **API REST** para gestión de leads y conversaciones
- ✅ **Lead Scoring Automático** basado en roadmap OnePercent
- ✅ **Integración con n8n** para automatización
- ✅ **4 Vistas Principales**: Pipeline, Conversaciones, Métricas, Bases de Datos
- 🔄 **Prospección Multi-Canal**: Instagram, LinkedIn, WhatsApp
- 🤖 **Sistema "Levanta Muertos"**: 7 mensajes automáticos de seguimiento
- 📊 **Analytics en Tiempo Real**: KPIs y métricas de performance

## 📁 Estructura del Proyecto

```
ai-crm/
├── app/                    # Next.js App Router
│   ├── api/               # API Routes
│   │   ├── leads/        # CRUD de leads
│   │   └── n8n-webhook/  # Webhook para n8n
│   ├── pipeline/         # Vista Kanban
│   ├── conversations/    # Vista de conversaciones
│   ├── metrics/          # Dashboard de métricas
│   └── databases/        # Importación de CSV
├── lib/                   # Utilidades
│   ├── db.ts             # Conexión PostgreSQL
│   └── scoring.ts        # Lógica de lead scoring
├── database/             # Schemas SQL
│   └── schema.sql        # Estructura de BD
└── scripts/              # Scripts de scraping (próximamente)
```

## 🛠️ Instalación

Ver [QUICKSTART.md](./QUICKSTART.md) para empezar rápidamente.

Ver [SETUP.md](./SETUP.md) para instalación completa paso a paso.

## 📊 Base de Datos

### Tablas Principales

- **leads**: Información de contactos y scoring
- **conversations**: Conversaciones por canal
- **messages**: Historial de mensajes
- **campaigns**: Campañas de prospección
- **follow_ups**: Sistema de seguimiento automático

## 🔗 Integraciones

### n8n
El sistema se integra con n8n para:
- Recibir mensajes de WhatsApp
- Procesar respuestas del agente IA
- Calcular lead scoring automático
- Sincronizar conversaciones

### Firebase (Opcional)
- Autenticación de usuarios
- Storage para archivos

## 📈 Lead Scoring

El sistema calcula automáticamente un score para cada lead basado en:

- **Capital >= 300**: +3 puntos
- **Intent "automatizado"**: +3 puntos
- **Respuesta rápida**: +1 punto
- **Entiende riesgo**: +2 puntos
- **Pide garantías**: -3 puntos

### Acciones Automáticas

- **Score >= 6**: Notificar para llamada
- **Score 3-5**: Entrar a nurture (7 mensajes)
- **Score <= 2**: Ofrecer Live gratis

## 🎯 Roadmap

- [x] Phase 1: Foundation & MVP
- [ ] Phase 2: Prospección Multi-Canal
- [ ] Phase 3: Dashboard Completo
- [ ] Phase 4: Sistema "Levanta Muertos"
- [ ] Phase 5: Optimizaciones

Ver [task.md](../brain/5709cd5b-efb7-4249-839e-9f47f19fa891/task.md) para detalles.

## 📝 Licencia

Proyecto privado - OnePercent

---

**Desarrollado con ❤️ para OnePercent**
