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

    # ── ESTRATEGIA 3: Seguidores de cuentas directorio ───────────────────────
    def buscar_en_seguidores(self, cuentas_directorio: List[str], max_por_cuenta=100) -> List[Dict]:
        """
        Analiza los seguidores de cuentas tipo directorio o guías locales.
        Ejemplos: @timeout_buenosaires, @donde_ir_bsas, @guiagastronomicaarg
        
        Los negocios que siguen estas cuentas son prospectos perfectos:
        ya buscan visibilidad pero no tienen web propia.
        """
        if not self._conectado:
            if not self.conectar():
                return []

        resultados = []
        vistos = set()

        for cuenta in cuentas_directorio:
            try:
                log.info(f"👥 Instagram: analizando seguidores de @{cuenta}...")
                user_id = self.client.user_id_from_username(cuenta)
                seguidores = self.client.user_followers(user_id, amount=max_por_cuenta)

                for follower_id, follower in seguidores.items():
                    if follower.username in vistos:
                        continue
                    vistos.add(follower.username)

                    try:
                        self._delay()
                        user_info = self.client.user_info(follower_id)

                        if self._es_negocio_sin_web(user_info):
                            dato = self._extraer_datos(user_info, f"seguidores @{cuenta}")
                            resultados.append(dato)
                            log.info(f"   ✅ {user_info.full_name or follower.username}")

                    except Exception as e:
                        log.debug(f"Error {follower.username}: {e}")
                        continue

                self._delay()

            except Exception as e:
                log.warning(f"Error con @{cuenta}: {e}")
                continue

        log.info(f"Instagram seguidores: {len(resultados)} negocios encontrados")
        return resultados

    def buscar_todo(self, rubros: List[str], ciudades: List[str],
                    cuentas_directorio: List[str] = None) -> List[Dict]:
        """Corre las 3 estrategias y deduplica"""
        todos = []
        vistos = set()

        # Estrategia 1: Hashtags
        por_hashtag = self.buscar_por_hashtag(rubros, ciudades)
        for r in por_hashtag:
            key = r.get("perfil_url", r.get("nombre_negocio", ""))
            if key not in vistos:
                vistos.add(key)
                todos.append(r)

        # Estrategia 2: Geo
        por_geo = self.buscar_por_geo(ciudades)
        for r in por_geo:
            key = r.get("perfil_url", r.get("nombre_negocio", ""))
            if key not in vistos:
                vistos.add(key)
                todos.append(r)

        # Estrategia 3: Directorios (si se especificaron)
        if cuentas_directorio:
            por_directorio = self.buscar_en_seguidores(cuentas_directorio)
            for r in por_directorio:
                key = r.get("perfil_url", r.get("nombre_negocio", ""))
                if key not in vistos:
                    vistos.add(key)
                    todos.append(r)

        log.info(f"✅ Instagram total: {len(todos)} negocios únicos sin web")
        return todos
