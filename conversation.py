"""
Máquina de estados conversacional — SKY Eleven Bot
====================================================
Maneja el flujo completo de la conversación desde que el prospecto
responde hasta que queda agendada la reunión con Gerardo.
"""

import random
import logging
import sqlite3
import re
from datetime import datetime
from typing import Optional, Tuple
from templates import ESTADOS, INTENT_KEYWORDS

log = logging.getLogger("Conversation")

# Estados posibles de la conversación
class Estado:
    NUEVO            = "nuevo"           # Nunca habló con el bot
    ESPERANDO_AGENDA = "esperando_agenda" # Bot preguntó cuándo, espera día/hora
    AGENDA_DADA      = "agenda_dada"     # Dio disponibilidad, bot explora problema
    EXPLORANDO       = "explorando"      # Bot está entendiendo el problema
    AGENDADO         = "agendado"        # Reunión confirmada ✅
    NO_INTERESADO    = "no_interesado"   # Dijo que no
    MUERTO           = "muerto"          # 2+ seguimientos sin respuesta


class ConversationManager:
    def __init__(self, db_path: str = "crm.db"):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._crear_tabla()

    def _crear_tabla(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS sky_conversaciones (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                telefono        TEXT UNIQUE,
                prospecto_id    INTEGER,
                nombre          TEXT,
                negocio         TEXT,
                estado          TEXT DEFAULT 'nuevo',
                dia_reunion     TEXT,
                hora_reunion    TEXT,
                resumen         TEXT,
                ultimo_mensaje  TEXT,
                seguimientos    INTEGER DEFAULT 0,
                fecha_inicio    TEXT,
                fecha_update    TEXT
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS sky_mensajes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                telefono    TEXT,
                direccion   TEXT,   -- 'entrante' | 'saliente'
                mensaje     TEXT,
                fecha       TEXT
            )
        """)
        self.db.commit()

    # ─────────────────────────────────────────────────────────────────────────
    # PROCESO PRINCIPAL: recibe mensaje → devuelve respuesta
    # ─────────────────────────────────────────────────────────────────────────

    def procesar(self, telefono: str, mensaje: str) -> Optional[str]:
        """
        Recibe un mensaje entrante y devuelve la respuesta del bot.
        Retorna None si no debe responder.
        """
        mensaje_limpio = mensaje.strip().lower()

        # Cargar o crear conversación
        conv = self._obtener_conversacion(telefono)
        estado_actual = conv["estado"] if conv else Estado.NUEVO

        # Guardar mensaje entrante
        self._guardar_mensaje(telefono, "entrante", mensaje)

        # Detectar intención
        intent = self._detectar_intent(mensaje_limpio)
        log.info(f"[{telefono}] Estado: {estado_actual} | Intent: {intent} | Msg: {mensaje[:50]}")

        # ─── MÁQUINA DE ESTADOS ───────────────────────────────────────────
        respuesta = None

        # Si ya está agendado, solo confirma
        if estado_actual == Estado.AGENDADO:
            if "cancel" in mensaje_limpio or "no puedo" in mensaje_limpio or "reprograma" in mensaje_limpio:
                respuesta = self._elegir(ESTADOS["REPROGRAMAR"])
                self._actualizar_estado(telefono, Estado.ESPERANDO_AGENDA)
            elif any(w in mensaje_limpio for w in ["sí", "si", "dale", "ahí", "ahi", "confirmado"]):
                respuesta = self._elegir(ESTADOS["CONFIRMA_RECORDATORIO"])
            else:
                respuesta = None  # No interrumpir si manda algo random estando agendado

        # Si dijo que no le interesa
        elif intent == "no_interesa":
            nombre = conv["nombre"] if conv else ""
            respuesta = self._elegir(ESTADOS["NO_INTERESADO"]).format(contacto=nombre)
            self._actualizar_estado(telefono, Estado.NO_INTERESADO)

        # Si pregunta precio
        elif intent == "precio":
            dia = conv["dia_reunion"] if conv else "la reunión"
            respuesta = self._elegir(ESTADOS["PRECIO"]).format(dia=dia)
            # Si estaba en nuevo, pasar a esperando_agenda para que el próximo mensaje se procese bien
            if estado_actual == Estado.NUEVO:
                self._actualizar_estado(telefono, Estado.ESPERANDO_AGENDA)

        # Si dice que no tiene tiempo
        elif intent == "no_tiempo":
            respuesta = self._elegir(ESTADOS["OBJECION_TIEMPO"])

        # Si da un día/hora (está agendando)
        elif estado_actual == Estado.ESPERANDO_AGENDA and intent == "dia_hora":
            dia, hora = self._extraer_dia_hora(mensaje)
            nombre = conv["nombre"] if conv else "ahí"
            respuesta = self._elegir(ESTADOS["CONFIRMAR_HORARIO"]).format(
                dia=dia, hora=hora
            )
            self._actualizar_estado(telefono, Estado.AGENDA_DADA, dia=dia, hora=hora)

        # Si responde positivo y está en estado nuevo → preguntar agenda
        elif estado_actual == Estado.NUEVO and intent == "positivo":
            nombre = conv["nombre"] if conv else ""
            respuesta = self._elegir(ESTADOS["BIENVENIDA"]).format(contacto=nombre)
            self._actualizar_estado(telefono, Estado.ESPERANDO_AGENDA)

        # Si ya dio la agenda y está contando su problema
        elif estado_actual == Estado.AGENDA_DADA:
            if intent == "problema_web" or intent == "problema_clientes":
                respuesta = self._elegir(ESTADOS["PROFUNDIZAR"])
                self._actualizar_estado(telefono, Estado.EXPLORANDO,
                    resumen=f"Problema: {mensaje[:100]}")
            else:
                respuesta = self._elegir(ESTADOS["EXPLORAR_PROBLEMA"])
                self._actualizar_estado(telefono, Estado.EXPLORANDO)

        # Si está explorando y da más info
        elif estado_actual == Estado.EXPLORANDO:
            # Suficiente info → confirmar reunión definitiva
            conv_actualizada = self._obtener_conversacion(telefono)
            if conv_actualizada and conv_actualizada["dia_reunion"]:
                respuesta = self._construir_confirmacion_final(conv_actualizada, mensaje)
                self._actualizar_estado(telefono, Estado.AGENDADO,
                    resumen=f"{conv_actualizada.get('resumen','')} | {mensaje[:100]}")
            else:
                respuesta = self._elegir(ESTADOS["EXPLORAR_PROBLEMA"])

        # Primer mensaje: el prospecto mandó algo pero no tenemos contexto
        elif estado_actual == Estado.NUEVO:
            if intent == "positivo":
                nombre = conv["nombre"] if conv else ""
                respuesta = self._elegir(ESTADOS["BIENVENIDA"]).format(contacto=nombre)
                self._actualizar_estado(telefono, Estado.ESPERANDO_AGENDA)
            else:
                # Respuesta inesperada, igual enganchamos
                respuesta = self._elegir(ESTADOS["BIENVENIDA"]).format(contacto="")
                self._actualizar_estado(telefono, Estado.ESPERANDO_AGENDA)

        # Guardar respuesta saliente
        if respuesta:
            self._guardar_mensaje(telefono, "saliente", respuesta)

        return respuesta

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _detectar_intent(self, mensaje: str) -> str:
        """Detecta la intención del mensaje por palabras clave"""
        import re

        def match(kw: str, texto: str) -> bool:
            # Busca palabra completa, no substring dentro de otra palabra
            return bool(re.search(r'(?<!\w)' + re.escape(kw) + r'(?!\w)', texto))

        # ORDEN IMPORTA: los más específicos/negativos van primero
        PRIORIDAD = [
            "no_interesa",   # "no me interesa" antes que "me interesa"
            "no_tiempo",     # "no tengo tiempo" antes que otro
            "precio",        # "cuánto sale" puede ir con "sí dale"
            "dia_hora",
            "problema_web",
            "problema_clientes",
            "positivo",      # lo más genérico al final
        ]

        # Detectar negaciones explícitas primero
        negaciones = ["no me interesa", "no gracias", "no necesito",
                      "no quiero", "paso", "no es para mí", "no tengo tiempo",
                      "ahora no", "más adelante", "no puedo"]
        for neg in negaciones:
            if neg in mensaje:
                if "tiempo" in neg or "adelante" in neg or "ahora no" in neg or "no puedo" in neg:
                    return "no_tiempo"
                return "no_interesa"

        for intent in PRIORIDAD:
            keywords = INTENT_KEYWORDS.get(intent, [])
            if any(match(kw, mensaje) for kw in keywords):
                return intent

        return "otro"

    def _extraer_dia_hora(self, mensaje: str) -> Tuple[str, str]:
        """Extrae día y hora del mensaje del prospecto"""
        dias = ["lunes", "martes", "miércoles", "miercoles", "jueves",
                "viernes", "mañana", "pasado", "hoy"]
        dia = next((d for d in dias if d in mensaje.lower()), "el día que dijiste")

        # Buscar patrón de hora: 10hs, 15:00, a las 10, etc.
        hora_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(?:hs?|hrs?|horas?)?', mensaje)
        hora = f"{hora_match.group(1)}:00hs" if hora_match else "el horario que mencionaste"

        return dia.capitalize(), hora

    def _construir_confirmacion_final(self, conv: dict, ultimo_msg: str) -> str:
        """Construye el mensaje de confirmación final con resumen"""
        dia   = conv.get("dia_reunion", "el día acordado")
        hora  = conv.get("hora_reunion", "el horario acordado")
        return (
            f"Perfecto, queda confirmado entonces — {dia} a las {hora} hablamos.\n"
            f"Te mando recordatorio el día anterior. Cualquier cosa me escribís acá 🙌"
        )

    def _elegir(self, opciones) -> str:
        """Elige aleatoriamente entre varias opciones de respuesta"""
        if isinstance(opciones, list):
            return random.choice(opciones)
        return opciones

    # ─────────────────────────────────────────────────────────────────────────
    # BASE DE DATOS
    # ─────────────────────────────────────────────────────────────────────────

    def _obtener_conversacion(self, telefono: str) -> Optional[dict]:
        cur = self.db.execute(
            "SELECT * FROM sky_conversaciones WHERE telefono = ?", (telefono,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def inicializar_conversacion(self, telefono: str, nombre: str,
                                  negocio: str, prospecto_id: int = None):
        """Crea la conversación cuando Gerardo manda el primer mensaje"""
        self.db.execute("""
            INSERT OR IGNORE INTO sky_conversaciones
                (telefono, prospecto_id, nombre, negocio, estado, fecha_inicio, fecha_update)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (telefono, prospecto_id, nombre, negocio, Estado.NUEVO,
              datetime.now().isoformat(), datetime.now().isoformat()))
        self.db.commit()

    def _actualizar_estado(self, telefono: str, nuevo_estado: str,
                            dia: str = None, hora: str = None, resumen: str = None):
        updates = ["estado = ?", "fecha_update = ?"]
        valores = [nuevo_estado, datetime.now().isoformat()]

        if dia:
            updates.append("dia_reunion = ?")
            valores.append(dia)
        if hora:
            updates.append("hora_reunion = ?")
            valores.append(hora)
        if resumen:
            updates.append("resumen = ?")
            valores.append(resumen)

        valores.append(telefono)
        self.db.execute(
            f"UPDATE sky_conversaciones SET {', '.join(updates)} WHERE telefono = ?",
            valores
        )
        self.db.commit()

    def _guardar_mensaje(self, telefono: str, direccion: str, mensaje: str):
        self.db.execute("""
            INSERT INTO sky_mensajes (telefono, direccion, mensaje, fecha)
            VALUES (?, ?, ?, ?)
        """, (telefono, direccion, mensaje, datetime.now().isoformat()))
        self.db.commit()

    def obtener_para_recordatorio(self) -> list:
        """Reuniones de mañana que necesitan recordatorio"""
        cur = self.db.execute("""
            SELECT * FROM sky_conversaciones
            WHERE estado = 'agendado'
              AND dia_reunion IS NOT NULL
        """)
        return [dict(r) for r in cur.fetchall()]

    def obtener_sin_respuesta(self, dias: int) -> list:
        """Conversaciones sin actividad hace X días para seguimiento"""
        from datetime import timedelta
        limite = (datetime.now() - timedelta(days=dias)).isoformat()
        cur = self.db.execute("""
            SELECT * FROM sky_conversaciones
            WHERE estado NOT IN ('agendado', 'no_interesado', 'muerto')
              AND fecha_update < ?
              AND seguimientos < 2
        """, (limite,))
        return [dict(r) for r in cur.fetchall()]

    def incrementar_seguimiento(self, telefono: str):
        self.db.execute("""
            UPDATE sky_conversaciones
            SET seguimientos = seguimientos + 1, fecha_update = ?
            WHERE telefono = ?
        """, (datetime.now().isoformat(), telefono))
        self.db.commit()
