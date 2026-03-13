import logging
import sys
import os

def setup_logging(log_file="bot.log"):
    """
    Configura un logger que es seguro para Windows (emojis en terminal)
    y guarda todo en UTF-8 en el archivo de log.
    """
    # Evitar configurar varias veces
    logger = logging.getLogger()
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    # 1. File Handler (Siempre UTF-8)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 2. Console Handler (Emoji-safe)
    try:
        handler = SafeStreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    except Exception:
        pass

    return logger

class SafeStreamHandler(logging.StreamHandler):
    """Handler que limpia caracteres no encodables antes de imprimir para evitar UnicodeEncodeError"""
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            # En Windows sys.stdout.encoding suele ser cp1252 o utf-8
            encoding = getattr(stream, 'encoding', 'utf-8') or 'utf-8'
            # Forzar reemplazo de caracteres que no entren en el encoding de la terminal
            safe_msg = msg.encode(encoding, errors='replace').decode(encoding)
            stream.write(safe_msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)
