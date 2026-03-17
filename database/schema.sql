-- AI CRM Database Schema
-- PostgreSQL 14+

-- Tabla principal de leads
CREATE TABLE IF NOT EXISTS leads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone VARCHAR(20) UNIQUE NOT NULL,
  name VARCHAR(255),
  email VARCHAR(255),
  source VARCHAR(50) NOT NULL, -- 'instagram', 'linkedin', 'whatsapp', 'manual'
  intent VARCHAR(50), -- 'learn_trading_live', 'automated_onepercent', 'skeptical', 'undecided', 'no_capital'
  score INTEGER DEFAULT 0,
  stage VARCHAR(50) DEFAULT 'new', -- 'new', 'contacted', 'qualified', 'call', 'closed', 'lost'
  tags TEXT[], -- ['no_capital', 'wants_fast_money', 'already_has_broker', etc.]
  metadata JSONB DEFAULT '{}', -- Datos adicionales específicos por canal
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabla de conversaciones
CREATE TABLE IF NOT EXISTS conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
  channel VARCHAR(50) NOT NULL, -- 'whatsapp', 'instagram', 'linkedin'
  external_id VARCHAR(255), -- ID de la conversación en el sistema externo (ej: Chatwoot)
  last_message_at TIMESTAMP,
  unread_count INTEGER DEFAULT 0,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Tabla de mensajes
CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  direction VARCHAR(10) NOT NULL, -- 'inbound', 'outbound'
  message_type VARCHAR(20) DEFAULT 'text', -- 'text', 'audio', 'image'
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW()
);

-- Tabla de campañas de prospección
CREATE TABLE IF NOT EXISTS campaigns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  channel VARCHAR(50) NOT NULL,
  status VARCHAR(20) DEFAULT 'active', -- 'active', 'paused', 'completed'
  target_count INTEGER,
  completed_count INTEGER DEFAULT 0,
  config JSONB DEFAULT '{}', -- Configuración específica (delays, mensajes, etc.)
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabla de seguimientos automáticos ("Levanta Muertos")
CREATE TABLE IF NOT EXISTS follow_ups (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
  sequence_step INTEGER NOT NULL, -- 1-7
  scheduled_at TIMESTAMP NOT NULL,
  sent_at TIMESTAMP,
  status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'sent', 'skipped', 'cancelled'
  message_content TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source);
CREATE INDEX IF NOT EXISTS idx_leads_stage ON leads(stage);
CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score DESC);
CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone);
CREATE INDEX IF NOT EXISTS idx_conversations_lead ON conversations(lead_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_follow_ups_scheduled ON follow_ups(scheduled_at) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_follow_ups_lead ON follow_ups(lead_id);

-- Trigger para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_leads_updated_at BEFORE UPDATE ON leads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_campaigns_updated_at BEFORE UPDATE ON campaigns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Datos de ejemplo (opcional, para testing)
-- INSERT INTO leads (phone, name, source, intent, score, stage) VALUES
-- ('+5491112345678', 'Juan Pérez', 'instagram', 'automated_onepercent', 5, 'contacted'),
-- ('+5491187654321', 'María González', 'linkedin', 'learn_trading_live', 3, 'new');
