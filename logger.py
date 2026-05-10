# logger.py
# Guarda logs en consola y en un archivo de texto.

from datetime import datetime
from threading import Lock


_log_lock = Lock()
LOG_FILE = "logs_partida.txt"


def log(mensaje):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{fecha}] {mensaje}"

    with _log_lock:
        print(linea)

        with open(LOG_FILE, "a", encoding="utf-8") as archivo:
            archivo.write(linea + "\n")