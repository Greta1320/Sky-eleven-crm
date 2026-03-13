"""
LinkedIn Scraper — SKY Eleven
================================
Busca dueños/gerentes de PYME y extrae email + teléfono al CRM.
Ataca en paralelo: mensaje LinkedIn + email + WhatsApp.

Instalar: pip install linkedin-api
"""

import time
import random
import logging
import re
from typing import List, Dict, Any

log = logging.getLogger("LinkedInScraper")

# Títulos de decisores que nos interesan
TITULOS_DECISOR = [
    "dueño", "owner", "fundador", "founder", "director", "gerente",
    "ceo", "propietario", "socio", "empresario", "emprendedor",
    "presidente", "socio gerente", "director general", "managing",
]

# Rubros → keywords de búsqueda en LinkedIn
KEYWORDS_POR_RUBRO = {
    "restaurantes":      ["restaurante", "gastronomia", "bar", "cafeteria", "comida"],
    "clínicas dentales": ["odontologia", "dental", "clinica dental", "odontologa"],
    "spas / estéticas":  ["spa", "estetica", "salon de belleza", "peluqueria"],
    "abogados":          ["abogado", "estudio juridico", "derecho", "lawyer"],
    "academias":         ["academia", "instituto", "capacitacion", "escuela"],
    "gimnasios":         ["gimnasio", "fitness", "gym", "entrenamiento"],
    "constructoras":     ["constructora", "construccion", "inmobiliaria", "arquitectura"],
    "contadores":        ["contador", "contabilidad", "estudio contable", "impuestos"],
}

class LinkedInScraper:
    def __init__(self, email: str, password: str, delay_min=5, delay_max=20):
        """
        email/password: credenciales de LinkedIn
        Recomendado: usar cuenta secundaria, no la personal
        """
        self.email     = email
        self.password  = password
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.api       = None
        self._conectado = False

    def conectar(self) -> bool:
        try:
            from linkedin_api import Linkedin
            log.info(f"Conectando LinkedIn como {self.email}...")
            self.api = Linkedin(self.email, self.password)
            self._conectado = True
            log.info("✅ LinkedIn conectado")
            return True
        except ImportError:
            log.error("❌ Instalar: pip install linkedin-api")
            return False
        except Exception as e:
            log.error(f"❌ Error login LinkedIn: {e}")
            return False

    def _delay(self):
        t = random.uniform(self.delay_min, self.delay_max)
        log.debug(f"Esperando {t:.1f}s...")
        time.sleep(t)

    def _es_decisor(self, titulo: str) -> bool:
        """Verifica si el título del perfil es un tomador de decisiones"""
        titulo_lower = titulo.lower()
        return any(t in titulo_lower for t in TITULOS_DECISOR)

    def _extraer_email_de_contacto(self, contact_info: dict) -> str:
        """Extrae email del contacto de LinkedIn"""
        email_addr = contact_info.get("email_address", "")
        if email_addr:
            return email_addr
        # Buscar en websites/otras secciones
        websites = contact_info.get("websites", [])
        return ""

    def _extraer_telefono(self, contact_info: dict, resumen: str = "") -> str:
        """Extrae teléfono del contacto o del resumen"""
        phones = contact_info.get("phone_numbers", [])
        if phones:
            return phones[0].get("number", "")
        # Buscar en el resumen/bio
        match = re.search(r'(?:\+?54|0)?(?:9\s*)?(?:11|[2-9]\d{2,3})\s*[\s\-]?\d{4}[\s\-]?\d{4}', resumen)
        return match.group(0) if match else ""

    def _tiene_web_propia(self, profile: dict, contact_info: dict) -> bool:
        """Verifica si tiene web en su perfil"""
        # Web en contacto
        websites = contact_info.get("websites", [])
        if websites:
            return True
        # URL de empresa en el perfil
        experiences = profile.get("experience", [])
        for exp in experiences:
            company = exp.get("company", {})
            if company.get("url") or company.get("website"):
                return True
        return False

    def _extraer_datos(self, profile: dict, contact_info: dict, ciudad: str = "") -> Dict[str, Any]:
        """Convierte perfil LinkedIn al formato estándar"""
        nombre    = f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip()
        titulo    = profile.get("headline", "")
        resumen   = profile.get("summary", "")
        ubicacion = profile.get("locationName", ciudad)

        # Empresa actual
        empresa = ""
        experiences = profile.get("experience", [])
        if experiences:
            exp_actual = experiences[0]
            empresa = exp_actual.get("companyName", "")

        email    = self._extraer_email_de_contacto(contact_info)
        telefono = self._extraer_telefono(contact_info, resumen)

        # URL del perfil
        public_id  = profile.get("public_id", "")
        perfil_url = f"https://linkedin.com/in/{public_id}" if public_id else ""

        # Industria
        industria = profile.get("industryName", "")

        return {
            "nombre_negocio": empresa or nombre,
            "contacto":       nombre,
            "telefono":       telefono,
            "email":          email,
            "website":        "",
            "tiene_web":      False,  # Ya filtramos antes
            "ciudad":         ubicacion,
            "categoria":      industria,
            "fuente":         "linkedin",
            "fuente_detalle": titulo,
            "perfil_url":     perfil_url,
            "seguidores":     profile.get("followersCount", 0),
            "descripcion":    f"{titulo} | {resumen[:200]}" if resumen else titulo,
            "raw_data": {
                "nombre":     nombre,
                "titulo":     titulo,
                "empresa":    empresa,
                "resumen":    resumen,
                "ubicacion":  ubicacion,
                "industria":  industria,
                "email":      email,
                "telefono":   telefono,
                "public_id":  public_id,
            }
        }

    def buscar_por_rubro_ciudad(self, rubros: List[str], ciudades: List[str],
                                  max_por_busqueda=25) -> List[Dict]:
        """
        Busca dueños/gerentes de PYME por rubro y ciudad.
        Extrae email + teléfono al CRM.
        """
        if not self._conectado:
            if not self.conectar():
                return []

        resultados = []
        vistos = set()

        for rubro in rubros:
            keywords_lista = KEYWORDS_POR_RUBRO.get(rubro.lower(), [rubro.lower()])

            for ciudad in ciudades:
                for keyword in keywords_lista[:2]:  # 2 keywords por rubro
                    query = f"dueño {keyword} {ciudad}"
                    log.info(f"🔍 LinkedIn: buscando '{query}'...")

                    try:
                        results = self.api.search_people(
                            keywords=query,
                            limit=max_por_busqueda,
                            filters={
                                "geoUrn": self._get_geo_urn(ciudad),
                            }
                        )

                        for person in results:
                            urn = person.get("urn_id", "")
                            if urn in vistos:
                                continue

                            # Filtrar por título de decisor
                            titulo = person.get("title", "")
                            if not self._es_decisor(titulo):
                                continue

                            vistos.add(urn)
                            self._delay()

                            try:
                                # Obtener perfil completo
                                profile = self.api.get_profile(urn_id=urn)
                                contact = self.api.get_profile_contact_info(urn_id=urn)

                                # Saltar si ya tiene web
                                if self._tiene_web_propia(profile, contact):
                                    log.debug(f"Tiene web, saltando: {urn}")
                                    continue

                                dato = self._extraer_datos(profile, contact, ciudad)
                                dato["rubro_buscado"] = rubro
                                resultados.append(dato)

                                nombre = dato["contacto"]
                                empresa = dato["nombre_negocio"]
                                email   = "✉️" if dato["email"] else "—"
                                tel     = "📱" if dato["telefono"] else "—"
                                log.info(f"   ✅ {nombre} / {empresa} email:{email} tel:{tel}")

                            except Exception as e:
                                log.debug(f"Error perfil {urn}: {e}")
                                continue

                        self._delay()

                    except Exception as e:
                        log.warning(f"Error búsqueda LinkedIn '{query}': {e}")
                        self._delay()
                        continue

        log.info(f"✅ LinkedIn: {len(resultados)} decisores encontrados")
        return resultados

    def _get_geo_urn(self, ciudad: str) -> str:
        """Mapeo ciudad → LinkedIn geoUrn"""
        GEO_URNS = {
            "CABA":     "urn:li:geo:100877138",
            "Buenos Aires": "urn:li:geo:100877138",
            "GBA Norte": "urn:li:geo:106321", 
            "Rosario":  "urn:li:geo:104677530",
            "Córdoba":  "urn:li:geo:101427483",
            "Mendoza":  "urn:li:geo:102139371",
        }
        return GEO_URNS.get(ciudad, "")

    def enviar_mensaje_directo(self, profile_urn: str, mensaje: str) -> bool:
        """
        Envía mensaje directo en LinkedIn.
        Límite: ~20/día en free, ~150 con Sales Navigator.
        """
        if not self._conectado:
            return False
        try:
            self._delay()
            self.api.send_message(message=mensaje, recipients=[profile_urn])
            log.info(f"✅ Mensaje LinkedIn enviado a {profile_urn}")
            return True
        except Exception as e:
            log.error(f"Error enviando mensaje LinkedIn: {e}")
            return False

    def buscar_todo(self, rubros: List[str], ciudades: List[str]) -> List[Dict]:
        return self.buscar_por_rubro_ciudad(rubros, ciudades)
