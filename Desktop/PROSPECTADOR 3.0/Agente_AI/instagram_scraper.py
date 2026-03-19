"""
Instagram Scraper — SKY Eleven
================================
Busca negocios en Instagram que NO tienen web (link en bio vacío).

Estrategias:
  1. Hashtags de rubro + ciudad (#restaurantecaba, #dentalcaba...)
  2. Geolocalización — posts recientes desde una ciudad
  3. Seguidores de cuentas masivas del rubro (guías, directorios locales)

Instalar: pip install instagrapi
"""

import time
import random
import logging
import re
from typing import List, Dict, Any

log = logging.getLogger("InstagramScraper")

# Rubros → hashtags específicos
HASHTAGS_POR_RUBRO = {
    "restaurantes":      ["restaurantecaba", "restaurantepalermo", "comidacaba", "gastronomiacaba", "restauranteargentina"],
    "clínicas dentales": ["dentistacaba", "odontologiacaba", "clinicadental", "dentistargentina", "odontologaargentina"],
    "spas / estéticas":  ["spacaba", "esteticacaba", "bellezacaba", "centrodeestetica", "esteticaargentina"],
    "abogados":          ["abogadocaba", "estudiojuridico", "abogadoargentina", "derechoargentina"],
    "academias":         ["academiacaba", "cursoscaba", "capacitacionargentina", "escuelacaba"],
    "gimnasios":         ["gimnasiocaba", "fitnesscaba", "gymargentina", "entrenamiento"],
    "médicos":           ["medicoscaba", "saludargentina", "clinicacaba", "medicocaba"],
    "inmobiliarias":     ["inmobiliariacaba", "propiedadescaba", "alquilercaba", "ventacasacaba"],
    "contadores":        ["contadorcaba", "estudiocountable", "contabilidadargentina"],
    "arquitectos":       ["arquitectocaba", "arquitecturaargentina", "diseñointerior"],
}

# Ciudades → IDs de ubicación de Instagram (location IDs)
CIUDADES_LOCATION_IDS = {
    "CABA":      "213144685",
    "Palermo":   "1215143",
    "Belgrano":  "213917625",
    "Recoleta":  "326697",
    "GBA Norte": "110740",
    "Rosario":   "1055440",
    "Córdoba":   "107594",
    "Mendoza":   "107540",
}

class InstagramScraper:
    def __init__(self, usuario: str, password: str, delay_min=30, delay_max=90):
        """
        usuario/password: credenciales de tu cuenta de Instagram
        delay_min/max: segundos entre acciones (anti-baneo)
        """
        self.usuario   = usuario
        self.password  = password
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.client    = None
        self._conectado = False

    def conectar(self) -> bool:
        """Inicia sesión en Instagram"""
        try:
            from instagrapi import Client
            from instagrapi.exceptions import LoginRequired, TwoFactorRequired

            self.client = Client()
            # Settings para parecer más humano
            self.client.set_settings({
                "user_agent": "Instagram 269.0.0.18.75 Android (26/8.0.0; 480dpi; 1080x1920; Xiaomi; MI 5s; capricorn; qcom; en_US; 314665256)"
            })

            if not self.usuario or not self.password or "tu_usuario" in self.usuario:
                log.warning("⚠️ No hay credenciales de Instagram configuradas. Saltando...")
                return False

            log.info(f"Conectando Instagram como {self.usuario}...")
            self.client.login(self.usuario, self.password)
            self._conectado = True
            log.info("✅ Instagram conectado")
            return True

        except ImportError:
            log.error("❌ Instalar: pip install instagrapi")
            return False
        except Exception as e:
            log.error(f"❌ Error login Instagram: {e}")
            return False

    def _delay(self):
        """Pausa random anti-baneo"""
        t = random.uniform(self.delay_min, self.delay_max)
        log.debug(f"Esperando {t:.0f}s...")
        time.sleep(t)

    def _es_negocio_sin_web(self, user_info) -> bool:
        """Filtra: cuenta de negocio sin web en bio"""
        # Descarta cuentas personales
        if not user_info.is_business:
            return False
        # Sin web en bio = oportunidad
        if user_info.external_url:
            return False
        # Mínimo 500 seguidores (negocio real, no recién creado)
        if user_info.follower_count < 500:
            return False
        # Descarta cuentas con millones (no son PYME)
        if user_info.follower_count > 500_000:
            return False
        return True

    def _extraer_datos(self, user_info, fuente_detalle: str = "") -> Dict[str, Any]:
        """Convierte un perfil de Instagram al formato estándar"""
        bio = user_info.biography or ""

        # Intentar extraer teléfono de la bio
        tel_match = re.search(r'(?:\+?54|0)?(?:9\s*)?(?:11|[2-9]\d{2,3})\s*[\s\-]?\d{4}[\s\-]?\d{4}', bio)
        telefono = tel_match.group(0).strip() if tel_match else (user_info.public_phone_number or "")

        # Email de la bio
        email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', bio)
        email = email_match.group(0) if email_match else (user_info.public_email or "")

        nombre = user_info.full_name or user_info.username

        return {
            "nombre_negocio": nombre,
            "contacto":       nombre,
            "telefono":       telefono,
            "email":          email,
            "website":        "",
            "tiene_web":      False,
            "ciudad":         user_info.city_name or "",
            "categoria":      user_info.category or "",
            "fuente":         "instagram",
            "fuente_detalle": fuente_detalle,
            "perfil_url":     f"https://instagram.com/{user_info.username}",
            "seguidores":     user_info.follower_count,
            "descripcion":    bio,
            "username":       user_info.username,
            "raw_data":       {
                "username":       user_info.username,
                "followers":      user_info.follower_count,
                "following":      user_info.following_count,
                "posts":          user_info.media_count,
                "is_business":    user_info.is_business,
                "category":       user_info.category,
                "city":           user_info.city_name,
                "public_phone":   user_info.public_phone_number,
                "public_email":   user_info.public_email,
            }
        }

    # ── ESTRATEGIA 1: Por hashtag ─────────────────────────────────────────────
    def buscar_por_hashtag(self, rubros: List[str], ciudades: List[str], max_por_hashtag=20) -> List[Dict]:
        """Busca posts recientes con hashtags de rubro+ciudad, filtra cuentas sin web"""
        if not self._conectado:
            if not self.conectar():
                return []

        resultados = []
        vistos = set()

        # Combinar hashtags del rubro con la ciudad
        hashtags = []
        for rubro in rubros:
            rubro_lower = rubro.lower()
            base = HASHTAGS_POR_RUBRO.get(rubro_lower, [rubro_lower.replace(" ", "").replace("/", "")])
            hashtags.extend(base)
            # También agregar ciudad al hashtag
            for ciudad in ciudades:
                ciudad_clean = ciudad.lower().replace(" ", "").replace("á","a").replace("ó","o")
                hashtags.append(f"{rubro_lower.replace(' ','')}{ciudad_clean}")

        log.info(f"🔍 Instagram: buscando {len(hashtags)} hashtags...")

        for hashtag in hashtags[:15]:  # Límite de hashtags por ciclo
            try:
                medias = self.client.hashtag_medias_recent(hashtag, amount=max_por_hashtag)
                log.info(f"   #{hashtag}: {len(medias)} posts")

                for media in medias:
                    username = media.user.username
                    if username in vistos:
                        continue
                    vistos.add(username)

                    try:
                        self._delay()
                        user_info = self.client.user_info(media.user.pk)

                        if self._es_negocio_sin_web(user_info):
                            dato = self._extraer_datos(user_info, f"hashtag #{hashtag}")
                            resultados.append(dato)
                            log.info(f"   ✅ {user_info.full_name or username} ({user_info.follower_count} seguidores)")

                    except Exception as e:
                        log.debug(f"Error obteniendo info de {username}: {e}")
                        continue

                self._delay()

            except Exception as e:
                log.warning(f"Error con hashtag #{hashtag}: {e}")
                self._delay()
                continue

        log.info(f"Instagram hashtags: {len(resultados)} negocios sin web encontrados")
        return resultados

    # ── ESTRATEGIA 2: Por geolocalización ────────────────────────────────────
    def buscar_por_geo(self, ciudades: List[str], max_por_ciudad=30) -> List[Dict]:
        """Busca posts recientes desde ubicaciones específicas"""
        if not self._conectado:
            if not self.conectar():
                return []

        resultados = []
        vistos = set()

        for ciudad in ciudades:
            location_id = CIUDADES_LOCATION_IDS.get(ciudad)
            if not location_id:
                log.warning(f"No hay location ID para {ciudad}")
                continue

            try:
                log.info(f"🗺️ Instagram geo: buscando en {ciudad}...")
                medias = self.client.location_medias_recent(location_id, amount=max_por_ciudad)

                for media in medias:
                    username = media.user.username
                    if username in vistos:
                        continue
                    vistos.add(username)

                    try:
                        self._delay()
                        user_info = self.client.user_info(media.user.pk)

                        if self._es_negocio_sin_web(user_info):
                            dato = self._extraer_datos(user_info, f"geo {ciudad}")
                            dato["ciudad"] = dato["ciudad"] or ciudad
                            resultados.append(dato)
                            log.info(f"   ✅ {user_info.full_name or username} ({ciudad})")

                    except Exception as e:
                        log.debug(f"Error {username}: {e}")
                        continue

                self._delay()

            except Exception as e:
                log.warning(f"Error geo {ciudad}: {e}")
                continue

        log.info(f"Instagram geo: {len(resultados)} negocios encontrados")
        return resultados

    # ── ESTRATEGIA 3: Seguidores de cuentas directorio / competencia ────────
    def buscar_en_seguidores(self, cuentas_objetivo: List[str], max_por_cuenta=50) -> List[Dict]:
        """
        Analiza los seguidores de cuentas tipo directorio, guías locales o COMPETENCIA.
        Ejemplos: @timeout_buenosaires, @agencia_competencia, @guia_gastronomica
        """
        if not self._conectado:
            if not self.conectar():
                return []

        resultados = []
        vistos = set()

        for cuenta in cuentas_objetivo:
            try:
                log.info(f"👥 Instagram: analizando seguidores de @{cuenta}...")
                user_id = self.client.user_id_from_username(cuenta)
                # Obtenemos seguidores (amount limitado para no levantar sospechas)
                seguidores = self.client.user_followers(user_id, amount=max_por_cuenta)

                for follower_id, follower in seguidores.items():
                    if follower.username in vistos:
                        continue
                    vistos.add(follower.username)

                    try:
                        self._delay()
                        user_info = self.client.user_info(follower_id)

                        # Filtro Senior: Es negocio, no tiene web y es "contactable"
                        if self._es_negocio_sin_web(user_info):
                            dato = self._extraer_datos(user_info, f"seguidor de @{cuenta}")
                            resultados.append(dato)
                            log.info(f"   ✅ Lead de competencia encontrado: @{follower.username}")

                    except Exception as e:
                        log.debug(f"Error {follower.username}: {e}")
                        continue

                self._delay()

            except Exception as e:
                log.warning(f"Error con @{cuenta}: {e}")
                continue

        log.info(f"Instagram: {len(resultados)} prospectos encontrados en seguidores")
        return resultados

    # ── ESTRATEGIA 4: Sniper de Comentarios ──────────────────────────────────
    def buscar_en_comentarios(self, post_urls: List[str], max_comentarios=50) -> List[Dict]:
        """
        Analiza quiénes comentan en posts específicos (ej: posts de la competencia).
        Busca palabras clave como 'precio', 'info', 'me interesa'.
        """
        if not self._conectado:
            if not self.conectar():
                return []

        resultados = []
        keywords_interes = ["info", "precio", "cuanto", "interesa", "valor", "costo", "mas informacion"]
        
        for url in post_urls:
            try:
                media_id = self.client.media_id(self.client.media_pk_from_url(url))
                log.info(f"💬 Analizando comentarios de: {url}")
                comments = self.client.media_comments(media_id, amount=max_comentarios)

                for comment in comments:
                    texto = comment.text.lower()
                    if any(key in texto for key in keywords_interes):
                        user_info = self.client.user_info(comment.user.pk)
                        if self._es_negocio_sin_web(user_info):
                            dato = self._extraer_datos(user_info, f"comentario en post")
                            dato["notas"] = f"Comentó: '{comment.text}'"
                            resultados.append(dato)
                            log.info(f"   🎯 Lead caliente por comentario: @{user_info.username}")
                
            except Exception as e:
                log.error(f"Error en sniper de comentarios: {e}")
                continue
                
        return resultados

    def buscar_todo(self, rubros: List[str], ciudades: List[str],
                    cuentas_directorio: List[str] = None,
                    cuentas_competencia: List[str] = None) -> List[Dict]:
        """Corre las estrategias configuradas y deduplica"""
        todos = []
        vistos = set()

        # Unimos directorios y competencia para la misma lógica de seguidores
        objetivos_seguidores = (cuentas_directorio or []) + (cuentas_competencia or [])

        # Estrategias en orden de calidad
        estrategias = [
            ("Hashtags", lambda: self.buscar_por_hashtag(rubros, ciudades)),
            ("Geo",      lambda: self.buscar_por_geo(ciudades)),
            ("Seguidores", lambda: self.buscar_en_seguidores(objetivos_seguidores) if objetivos_seguidores else [])
        ]

        for nombre, func in estrategias:
            log.info(f"🚀 Iniciando estrategia: {nombre}")
            leads = func()
            for r in leads:
                key = r.get("username", r.get("perfil_url", ""))
                if key not in vistos:
                    vistos.add(key)
                    todos.append(r)

        log.info(f"✅ Instagram total: {len(todos)} negocios únicos sin web")
        return todos
