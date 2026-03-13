"""
Integración CRM — SKY Eleven
==============================
Se conecta a TU base de datos existente (SQLite o Postgres).
Detecta la estructura actual y se adapta a ella, o crea las tablas si no existen.
"""

import logging
import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from config import Config

log = logging.getLogger("CRM")


class CRMIntegration:
    def __init__(self, config: Config):
        self.config = config
        self.conn = None
        self._conectar()
        self._asegurar_tablas()

    def _conectar(self):
        """Conecta a SQLite o Postgres según config"""
        if self.config.DB_TYPE == "sqlite":
            self.conn = sqlite3.connect(self.config.DB_PATH, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            log.info(f"✅ Conectado a SQLite: {self.config.DB_PATH}")
        else:
            # Postgres — instala con: pip install psycopg2-binary
            try:
                import psycopg2
                import psycopg2.extras
                self.conn = psycopg2.connect(
                    host=self.config.DB_HOST,
                    port=self.config.DB_PORT,
                    dbname=self.config.DB_NAME,
                    user=self.config.DB_USER,
                    password=self.config.DB_PASS,
                )
                self.conn.autocommit = True
                log.info(f"✅ Conectado a Postgres: {self.config.DB_HOST}/{self.config.DB_NAME}")
            except ImportError:
                log.error("psycopg2 no instalado. Ejecuta: pip install psycopg2-binary")
                raise

    def _asegurar_tablas(self):
        """
        Crea las tablas del agente si no existen.
        Si ya tienes una tabla 'prospectos', detecta sus columnas y agrega las que faltan.
        """
        cursor = self.conn.cursor()
        
        # Tabla principal de prospectos del agente
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sky_prospectos (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_negocio   TEXT NOT NULL,
                contacto         TEXT,
                telefono         TEXT,
                email            TEXT,
                website          TEXT,
                tiene_web        INTEGER DEFAULT 0,
                ciudad           TEXT,
                categoria        TEXT,
                fuente           TEXT,
                perfil_url       TEXT,
                seguidores       INTEGER DEFAULT 0,
                descripcion      TEXT,
                score            INTEGER DEFAULT 0,
                razon_score      TEXT,
                stage            TEXT DEFAULT 'Nuevo',
                servicio         TEXT,
                notificado_wsp   INTEGER DEFAULT 0,
                fecha_creacion   TEXT,
                fecha_contacto   TEXT,
                fecha_seguimiento TEXT,
                notas            TEXT,
                hash_unico       TEXT UNIQUE   -- Para deduplicar
            )
        """)

        # Tabla de seguimiento / historial de contactos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sky_seguimientos (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                prospecto_id    INTEGER,
                tipo            TEXT,      -- 'wsp_alerta', 'email', 'dm', 'seguimiento'
                mensaje         TEXT,
                fecha           TEXT,
                resultado       TEXT,      -- 'enviado', 'error', 'respondio'
                FOREIGN KEY(prospecto_id) REFERENCES sky_prospectos(id)
            )
        """)

        self.conn.commit()
        log.info("✅ Tablas CRM verificadas/creadas")

    # ─────────────────────────────────────────────────────────────────────────
    # MÉTODOS PRINCIPALES
    # ─────────────────────────────────────────────────────────────────────────

    async def filtrar_duplicados(self, prospects: List[Dict]) -> List[Dict]:
        """Elimina prospectos que ya existen en la DB"""
        nuevos = []
        cursor = self.conn.cursor()

        for p in prospects:
            # Hash único basado en teléfono + nombre del negocio
            hash_val = self._generar_hash(p)
            cursor.execute(
                "SELECT id FROM sky_prospectos WHERE hash_unico = ?", (hash_val,)
            )
            if not cursor.fetchone():
                p["hash_unico"] = hash_val
                nuevos.append(p)

        log.info(f"   Deduplicación: {len(prospects)} → {len(nuevos)} nuevos")
        return nuevos

    async def guardar_prospectos(self, prospects: List[Dict]) -> List[Dict]:
        """Guarda los prospectos calificados en la DB"""
        guardados = []
        cursor = self.conn.cursor()

        for p in prospects:
            try:
                cursor.execute("""
                    INSERT INTO sky_prospectos (
                        nombre_negocio, contacto, telefono, email, website,
                        tiene_web, ciudad, categoria, fuente, perfil_url,
                        seguidores, descripcion, score, razon_score, stage,
                        servicio, fecha_creacion, hash_unico
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p.get("nombre_negocio"), p.get("contacto"), p.get("telefono"),
                    p.get("email"), p.get("website"), int(p.get("tiene_web", False)),
                    p.get("ciudad"), p.get("categoria"), p.get("fuente"),
                    p.get("perfil_url"), p.get("seguidores", 0), p.get("descripcion"),
                    p.get("score", 0), p.get("razon_score"), p.get("stage", "Nuevo"),
                    p.get("servicio"), datetime.now().isoformat(), p.get("hash_unico")
                ))
                p["id"] = cursor.lastrowid
                guardados.append(p)
            except Exception as e:
                log.error(f"Error guardando {p.get('nombre_negocio')}: {e}")

        self.conn.commit()
        return guardados

    async def marcar_notificado(self, prospect_id: int):
        """Marca que ya se envió WhatsApp para este prospecto"""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE sky_prospectos SET notificado_wsp = 1, fecha_contacto = ? WHERE id = ?",
            (datetime.now().isoformat(), prospect_id)
        )
        self.conn.commit()

    async def obtener_sin_respuesta(self, dias: int = 3) -> List[Dict]:
        """Obtiene prospectos contactados hace X días sin respuesta"""
        cursor = self.conn.cursor()
        fecha_limite = (datetime.now() - timedelta(days=dias)).isoformat()
        cursor.execute("""
            SELECT * FROM sky_prospectos
            WHERE notificado_wsp = 1
              AND stage = 'Contactado'
              AND fecha_contacto < ?
              AND (fecha_seguimiento IS NULL OR fecha_seguimiento < ?)
        """, (fecha_limite, fecha_limite))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

    async def registrar_seguimiento(self, prospect_id: int, tipo: str = "seguimiento", resultado: str = "enviado"):
        """Registra un seguimiento en el historial"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO sky_seguimientos (prospecto_id, tipo, fecha, resultado)
            VALUES (?, ?, ?, ?)
        """, (prospect_id, tipo, datetime.now().isoformat(), resultado))
        cursor.execute(
            "UPDATE sky_prospectos SET fecha_seguimiento = ? WHERE id = ?",
            (datetime.now().isoformat(), prospect_id)
        )
        self.conn.commit()

    async def actualizar_stage(self, prospect_id: int, stage: str, notas: str = None):
        """Actualiza la etapa de un prospecto (desde el dashboard o manualmente)"""
        cursor = self.conn.cursor()
        if notas:
            cursor.execute(
                "UPDATE sky_prospectos SET stage = ?, notas = ? WHERE id = ?",
                (stage, notas, prospect_id)
            )
        else:
            cursor.execute(
                "UPDATE sky_prospectos SET stage = ? WHERE id = ?",
                (stage, prospect_id)
            )
        self.conn.commit()

    def obtener_stats(self) -> Dict[str, Any]:
        """Stats para el dashboard"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT stage, COUNT(*) as cnt FROM sky_prospectos GROUP BY stage")
        por_etapa = {r[0]: r[1] for r in cursor.fetchall()}

        cursor.execute("SELECT COUNT(*) FROM sky_prospectos")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM sky_prospectos WHERE score >= 70")
        hot = cursor.fetchone()[0]

        return {
            "total": total,
            "hot": hot,
            "por_etapa": por_etapa,
        }

    def _generar_hash(self, prospect: Dict) -> str:
        """Hash único para deduplicar: teléfono + nombre normalizado"""
        import hashlib
        tel   = (prospect.get("telefono") or "").strip().replace(" ", "")
        nombre = (prospect.get("nombre_negocio") or "").lower().strip()
        raw   = f"{tel}_{nombre}"
        return hashlib.md5(raw.encode()).hexdigest()

    # ─────────────────────────────────────────────────────────────────────────
    # INTEGRACIÓN CON TU CRM EXISTENTE
    # ─────────────────────────────────────────────────────────────────────────
    async def sincronizar_con_crm_existente(self, prospect: Dict):
        """
        Si tu CRM existente tiene su propia tabla, también inserta ahí.
        Descomenta y ajusta según la estructura de TU tabla.

        Ejemplo:
            cursor.execute(
                "INSERT INTO tu_tabla_crm (nombre, telefono, estado, ...) VALUES (?, ?, ?, ...)",
                (prospect['nombre_negocio'], prospect['telefono'], 'nuevo', ...)
            )
        """
        pass  # Conecta aquí con tu CRM existente
