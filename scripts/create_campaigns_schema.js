const { Pool } = require('pg');
require('dotenv').config({ path: '.env.local' });

// Intentar varias rutas para cargar env si no hay url directa temporalmente
const connectionString = process.env.DATABASE_URL || 'postgres://postgres:postgres@localhost:5432/ai_crm';

const pool = new Pool({
    connectionString,
});

async function runMigration() {
    console.log('Aplicando migración para tabla de Campañas...');

    try {
        // 1. Crear tabla de campañas
        await pool.query(`
            CREATE TABLE IF NOT EXISTS campaigns (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                niche VARCHAR(255),
                location VARCHAR(255),
                status VARCHAR(50) DEFAULT 'draft',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        `);
        console.log('✅ Tabla campaigns verificada/creada.');

        // 2. Modificar tabla leads para añadir campaign_id si no existe
        const checkColumn = await pool.query(`
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='leads' AND column_name='campaign_id';
        `);

        if (checkColumn.rows.length === 0) {
            await pool.query(`
                ALTER TABLE leads 
                ADD COLUMN campaign_id INTEGER REFERENCES campaigns(id) ON DELETE SET NULL;
            `);
            console.log('✅ Columna campaign_id añadida a leads.');
        } else {
            console.log('✅ Columna campaign_id ya existe en leads.');
        }

        console.log('🎉 Migración completada exitosamente.');
    } catch (err) {
        console.error('❌ Error en migración:', err);
    } finally {
        await pool.end();
    }
}

runMigration();
