# puzzles.py
# Contiene las salas, respuestas, pistas y el código final del escape room.

import unicodedata


FINAL_CODE = "FAUSTO"
GAME_DURATION_SECONDS = 7 * 60  # 7 minutos. Podéis cambiarlo si queréis más tiempo.


def normalizar(texto):
    """
    Normaliza las respuestas:
    - quita espacios al principio/final
    - pasa a minúsculas
    - elimina tildes
    Así acepta: fausto, Fausto, FAUSTO, etc.
    """
    texto = texto.strip().lower()
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    return texto


PUZZLES = [
    {
        "sala": 1,
        "titulo": "La puerta bloqueada",
        "enunciado": """
SALA 1: LA PUERTA BLOQUEADA

Para abrir la primera puerta, resuelve este código:

Si A = 1, B = 2, C = 3...
¿Cuánto vale la palabra RED?
""",
        "respuestas": ["27"],
        "pista": "Convierte cada letra en su posición del abecedario y suma los valores.",
        "letra": "F",
    },
    {
        "sala": 2,
        "titulo": "La ecuación del laboratorio",
        "enunciado": """
SALA 2: EL LABORATORIO

En la pared aparece escrita esta ecuación:

2x + 6 = 18

¿Qué valor tiene x?
""",
        "respuestas": ["6"],
        "pista": "Primero resta 6 a ambos lados y después divide entre 2.",
        "letra": "A",
    },
    {
        "sala": 3,
        "titulo": "La sala del espejo",
        "enunciado": """
SALA 3: LA SALA DEL ESPEJO

Si me tumbas, soy todo.
Si me cortas por la cintura, me quedo en nada.

¿Qué soy?
""",
        "respuestas": ["8", "ocho"],
        "pista": "Piensa en un número que, al tumbarlo, se parece al infinito.",
        "letra": "U",
    },
    {
        "sala": 4,
        "titulo": "La alarma de los cables",
        "enunciado": """
SALA 4: LA ALARMA

La alarma está a punto de activarse.

Hay tres cables: rojo, azul y verde.

Pista: no cortes el color del fuego ni el color de la naturaleza.

¿Qué cable cortas?
""",
        "respuestas": ["azul"],
        "pista": "El color del fuego es rojo y el de la naturaleza es verde.",
        "letra": "S",
    },
    {
        "sala": 5,
        "titulo": "Pasapalabra sospechoso",
        "enunciado": """
SALA 5: PASAPALABRA SOSPECHOSO

Con la P:

Acción que le gusta hacer a Rodrigo y que no es del todo legal.
""",
        "respuestas": ["piratear"],
        "pista": "Empieza por P y tiene que ver con conseguir cosas digitales de forma no muy legal.",
        "letra": "T",
    },
    {
        "sala": 6,
        "titulo": "La habitación a oscuras",
        "enunciado": """
SALA 6: LA HABITACIÓN A OSCURAS

Entras en una habitación completamente oscura.

Dentro hay una vela, una chimenea y una lámpara de aceite.

Solo tienes una cerilla.

¿Qué enciendes primero?
""",
        "respuestas": ["cerilla", "la cerilla"],
        "pista": "Antes de encender cualquier objeto, necesitas encender algo más pequeño.",
        "letra": "O",
    },
]