# servidor.py
# Servidor central del escape room distribuido.
# Usa sockets, threading, Lock, Event, Semaphore, PriorityQueue y multiprocessing.

import json
import socket
import threading
import queue
import itertools
import time
import multiprocessing
from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional

from puzzles import PUZZLES, FINAL_CODE, GAME_DURATION_SECONDS, normalizar
from logger import log


HOST = "0.0.0.0"
PORT = 5050
ENCODING = "utf-8"

PRIORIDAD_ALARMA = 1
PRIORIDAD_CORRECTO = 2
PRIORIDAD_PISTA = 3
PRIORIDAD_NORMAL = 4


@dataclass
class ClientConnection:
    conn: socket.socket
    role: str
    name: str
    send_lock: threading.Lock = field(default_factory=threading.Lock)
    channels: Set[str] = field(default_factory=set)


@dataclass
class PlayerState:
    team: str
    client: ClientConnection
    room: int = 0
    score: int = 0
    hints: int = 0
    wrongs: int = 0
    letters: List[str] = field(default_factory=list)
    finished: bool = False
    finish_time: Optional[float] = None


clients: Dict[str, ClientConnection] = {}
players: Dict[str, PlayerState] = {}
subscriptions: Dict[str, Set[str]] = {}

state_lock = threading.Lock()
game_started = threading.Event()
game_finished = threading.Event()
game_paused = threading.Event()

# Solo dos equipos pueden pedir pista exactamente al mismo tiempo.
hint_semaphore = threading.Semaphore(2)

# Cola de eventos con prioridad: alarmas antes que mensajes normales.
event_queue = queue.PriorityQueue()
event_counter = itertools.count()

# Multiprocessing para el temporizador.
timer_queue = multiprocessing.Queue()
timer_stop_event = multiprocessing.Event()
timer_process = None

start_time = None


def timer_worker(duration, output_queue, stop_event):
    """
    Proceso independiente para controlar el tiempo de partida.
    Envía avisos al servidor cuando queda poco tiempo.
    """
    start = time.time()
    checkpoints = [300, 180, 60, 30, 10]
    already_sent = set()

    while not stop_event.is_set():
        elapsed = int(time.time() - start)
        remaining = duration - elapsed

        for checkpoint in checkpoints:
            if duration >= checkpoint and remaining <= checkpoint and checkpoint not in already_sent:
                output_queue.put({"type": "tick", "remaining": checkpoint})
                already_sent.add(checkpoint)

        if remaining <= 0:
            output_queue.put({"type": "timeout"})
            break

        time.sleep(1)


def format_seconds(seconds):
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def send_packet(client, payload):
    try:
        data = json.dumps(payload, ensure_ascii=False) + "\n"
        with client.send_lock:
            client.conn.sendall(data.encode(ENCODING))
    except OSError:
        log(f"No se pudo enviar mensaje a {client.name}.")


def send_text(client, text):
    send_packet(client, {"type": "message", "text": text})


def publish(channel, text, priority=PRIORIDAD_NORMAL):
    event_queue.put((priority, next(event_counter), channel, text))


def add_subscription_unlocked(client, channel):
    client.channels.add(channel)

    if channel not in subscriptions:
        subscriptions[channel] = set()

    subscriptions[channel].add(client.name)


def dispatcher_loop():
    """
    Hilo que procesa los mensajes de la cola de prioridad y los envía
    a todos los clientes suscritos al canal correspondiente.
    """
    while True:
        priority, _, channel, text = event_queue.get()

        with state_lock:
            recipients = [
                clients[name]
                for name in subscriptions.get(channel, set())
                if name in clients
            ]

        for client in recipients:
            send_text(client, text)

        event_queue.task_done()


def timer_listener_loop():
    """
    Hilo del servidor que escucha los mensajes del proceso temporizador.
    """
    while True:
        data = timer_queue.get()

        if game_finished.is_set():
            continue

        if data["type"] == "tick":
            remaining = data["remaining"]
            publish(
                "alarmas",
                f"\n[TEMPORIZADOR] Quedan {format_seconds(remaining)} para escapar.\n",
                PRIORIDAD_ALARMA,
            )

        elif data["type"] == "timeout":
            game_finished.set()
            publish(
                "alarmas",
                "\n[FIN DE PARTIDA] Se ha acabado el tiempo. Nadie ha escapado.\n",
                PRIORIDAD_ALARMA,
            )
            publish("ranking", ranking_text(), PRIORIDAD_NORMAL)
            log("La partida terminó por tiempo agotado.")


def clean_name(name):
    name = name.strip()

    if not name:
        name = "Equipo"

    # Evitamos espacios para que los comandos del Game Master sean más fáciles.
    name = "_".join(name.split())
    return name


def unique_name_unlocked(base_name):
    name = base_name
    number = 2

    while name in clients or name in players:
        name = f"{base_name}_{number}"
        number += 1

    return name


def format_puzzle(puzzle):
    return (
        "\n" + "=" * 60 +
        puzzle["enunciado"] +
        "\nEscribe tu respuesta directamente o usa: /respuesta TU_RESPUESTA\n" +
        "Puedes pedir una pista con: /pista\n" +
        "=" * 60 + "\n"
    )


def send_current_puzzle(team):
    with state_lock:
        player = players.get(team)

        if not player:
            return

        if player.room >= len(PUZZLES):
            text = (
                "\nHas superado todas las salas.\n"
                f"Letras conseguidas: {' '.join(player.letters)}\n"
                "Introduce el código final para escapar.\n"
                "Puedes escribirlo directamente o usar: /codigo FAUSTO\n"
            )
        else:
            puzzle = PUZZLES[player.room]
            text = format_puzzle(puzzle)

    publish(f"team:{team}", text, PRIORIDAD_NORMAL)


def ranking_text():
    with state_lock:
        ranking = list(players.values())

    if not ranking:
        return "\n[RANKING] Todavía no hay equipos conectados.\n"

    ranking.sort(
        key=lambda p: (
            0 if p.finished else 1,
            -p.score,
            -p.room,
            p.hints,
            p.finish_time if p.finish_time is not None else float("inf"),
        )
    )

    lines = ["\nRANKING ACTUAL", "-" * 60]

    for index, player in enumerate(ranking, start=1):
        if player.finished:
            estado = "ESCAPÓ"
        elif player.room >= len(PUZZLES):
            estado = "Código final"
        else:
            estado = f"Sala {player.room + 1}/{len(PUZZLES)}"

        letras = "".join(player.letters) if player.letters else "-"

        lines.append(
            f"{index}. {player.team} | {estado} | "
            f"{player.score} puntos | pistas: {player.hints} | "
            f"fallos: {player.wrongs} | letras: {letras}"
        )

    lines.append("-" * 60 + "\n")
    return "\n".join(lines)


def help_player_text():
    return """
COMANDOS DISPONIBLES

/respuesta TU_RESPUESTA   Enviar respuesta a la sala actual.
/pista                    Pedir una pista. Resta 20 puntos.
/estado                   Ver tu estado actual.
/ranking                  Ver ranking.
/codigo FAUSTO            Enviar código final.
/salir                    Desconectarse.

También puedes escribir la respuesta directamente sin poner /respuesta.
"""


def help_master_text():
    return """
COMANDOS DEL GAME MASTER

/start                         Iniciar partida.
/broadcast MENSAJE             Mandar mensaje a todos.
/hint EQUIPO MENSAJE           Mandar pista privada a un equipo.
/ranking                       Ver ranking.
/teams                         Ver equipos conectados.
/pause                         Pausar partida.
/resume                        Reanudar partida.
/end                           Terminar partida.
/ayuda                         Ver esta ayuda.
"""


def start_timer():
    global timer_process

    if timer_process is not None and timer_process.is_alive():
        return

    timer_stop_event.clear()

    timer_process = multiprocessing.Process(
        target=timer_worker,
        args=(GAME_DURATION_SECONDS, timer_queue, timer_stop_event),
        daemon=True,
    )
    timer_process.start()


def start_game(master_name):
    global start_time

    if game_started.is_set():
        publish(f"team:{master_name}", "La partida ya estaba iniciada.", PRIORIDAD_NORMAL)
        return

    game_started.set()
    start_time = time.time()

    publish(
        "alarmas",
        "\n[INICIO] La partida ha comenzado. Tenéis que escapar resolviendo las salas.\n",
        PRIORIDAD_ALARMA,
    )

    log(f"{master_name} inició la partida.")
    start_timer()

    with state_lock:
        teams = list(players.keys())

    for team in teams:
        send_current_puzzle(team)


def finish_game(reason):
    game_finished.set()
    timer_stop_event.set()

    publish(
        "alarmas",
        f"\n[FIN DE PARTIDA] {reason}\n",
        PRIORIDAD_ALARMA,
    )
    publish("ranking", ranking_text(), PRIORIDAD_NORMAL)
    log(f"Partida finalizada: {reason}")


def process_correct_room(player, answer):
    puzzle = PUZZLES[player.room]

    player.score += 100
    player.letters.append(puzzle["letra"])
    solved_room = player.room + 1
    player.room += 1

    private_message = (
        f"\n[CORRECTO] Has superado la sala {solved_room}.\n"
        f"Has conseguido la letra: {puzzle['letra']}\n"
        f"Letras actuales: {' '.join(player.letters)}\n"
        f"Puntuación actual: {player.score}\n"
    )

    global_message = (
        f"[AVANCE] {player.team} ha superado la sala {solved_room} "
        f"y ha conseguido una nueva letra."
    )

    needs_next_puzzle = player.room < len(PUZZLES)

    if player.room >= len(PUZZLES):
        private_message += (
            "\nHas superado todas las salas.\n"
            "Ahora introduce el código final para escapar.\n"
            "Puedes escribirlo directamente o usar: /codigo FAUSTO\n"
        )

    return private_message, global_message, needs_next_puzzle


def process_final_code(player, answer):
    if normalizar(answer) == normalizar(FINAL_CODE):
        player.finished = True
        player.finish_time = time.time()
        player.score += 50

        game_finished.set()
        timer_stop_event.set()

        private_message = (
            "\n[ESCAPASTE] Código correcto. Habéis escapado del escape room.\n"
            f"Código final: {FINAL_CODE}\n"
            f"Puntuación final: {player.score}\n"
        )

        global_message = (
            f"\n[GANADOR] {player.team} ha introducido el código final "
            f"{FINAL_CODE} y ha ganado la partida.\n"
        )

        log(f"{player.team} ganó la partida con {player.score} puntos.")

        return private_message, global_message, True

    player.score -= 10
    player.wrongs += 1

    return (
        "\n[INCORRECTO] Ese no es el código final. Pierdes 10 puntos.\n",
        f"[FALLO] {player.team} ha fallado el código final.",
        False,
    )


def process_answer(team, answer):
    if not game_started.is_set():
        publish(f"team:{team}", "La partida todavía no ha empezado.", PRIORIDAD_NORMAL)
        return

    if game_finished.is_set():
        publish(f"team:{team}", "La partida ya ha terminado.", PRIORIDAD_NORMAL)
        return

    if game_paused.is_set():
        publish(f"team:{team}", "La partida está pausada.", PRIORIDAD_NORMAL)
        return

    answer_normalized = normalizar(answer)

    with state_lock:
        player = players.get(team)

        if not player:
            return

        if player.finished:
            private_message = "Tu equipo ya ha escapado."
            global_message = None
            needs_next_puzzle = False
            game_won = False

        elif player.room >= len(PUZZLES):
            private_message, global_message, game_won = process_final_code(player, answer)
            needs_next_puzzle = False

        else:
            puzzle = PUZZLES[player.room]
            valid_answers = [normalizar(r) for r in puzzle["respuestas"]]

            if answer_normalized in valid_answers:
                private_message, global_message, needs_next_puzzle = process_correct_room(player, answer)
                game_won = False
            else:
                player.score -= 10
                player.wrongs += 1

                private_message = (
                    "\n[INCORRECTO] Respuesta incorrecta. Pierdes 10 puntos.\n"
                    "Puedes intentarlo otra vez o pedir una pista con /pista.\n"
                )
                global_message = f"[FALLO] {team} ha enviado una respuesta incorrecta."
                needs_next_puzzle = False
                game_won = False

    publish(f"team:{team}", private_message, PRIORIDAD_CORRECTO)

    if global_message:
        publish("global", global_message, PRIORIDAD_CORRECTO)

    publish("ranking", ranking_text(), PRIORIDAD_NORMAL)

    if needs_next_puzzle:
        send_current_puzzle(team)

    if game_won:
        publish("ranking", ranking_text(), PRIORIDAD_ALARMA)


def handle_hint(team):
    if not game_started.is_set():
        publish(f"team:{team}", "La partida todavía no ha empezado.", PRIORIDAD_NORMAL)
        return

    if game_finished.is_set():
        publish(f"team:{team}", "La partida ya ha terminado.", PRIORIDAD_NORMAL)
        return

    acquired = hint_semaphore.acquire(blocking=False)

    if not acquired:
        publish(
            f"team:{team}",
            "El sistema de pistas está ocupado. Inténtalo de nuevo en unos segundos.",
            PRIORIDAD_PISTA,
        )
        return

    try:
        with state_lock:
            player = players.get(team)

            if not player:
                return

            player.hints += 1
            player.score -= 20

            if player.room >= len(PUZZLES):
                hint = f"El código final tiene {len(FINAL_CODE)} letras."
            else:
                hint = PUZZLES[player.room]["pista"]

        time.sleep(0.5)

        publish(
            f"team:{team}",
            f"\n[PISTA] {hint}\nHas perdido 20 puntos.\n",
            PRIORIDAD_PISTA,
        )

        publish(
            "pistas",
            f"[PISTA] {team} ha pedido una pista.",
            PRIORIDAD_PISTA,
        )

        log(f"{team} pidió una pista.")

    finally:
        hint_semaphore.release()


def send_status(team):
    with state_lock:
        player = players.get(team)

        if not player:
            return

        if player.finished:
            estado = "Habéis escapado."
        elif player.room >= len(PUZZLES):
            estado = "Estáis en el código final."
        else:
            estado = f"Estáis en la sala {player.room + 1}/{len(PUZZLES)}."

        text = (
            f"\n[ESTADO]\n"
            f"Equipo: {player.team}\n"
            f"{estado}\n"
            f"Puntuación: {player.score}\n"
            f"Pistas usadas: {player.hints}\n"
            f"Fallos: {player.wrongs}\n"
            f"Letras: {' '.join(player.letters) if player.letters else '-'}\n"
        )

    publish(f"team:{team}", text, PRIORIDAD_NORMAL)


def process_player_command(team, raw_command):
    command = raw_command.strip()

    if not command:
        return True

    command_lower = command.lower()

    if command_lower == "/salir":
        publish(f"team:{team}", "Te has desconectado de la partida.", PRIORIDAD_NORMAL)
        return False

    if command_lower == "/ayuda":
        publish(f"team:{team}", help_player_text(), PRIORIDAD_NORMAL)
        return True

    if command_lower == "/pista":
        handle_hint(team)
        return True

    if command_lower == "/estado":
        send_status(team)
        return True

    if command_lower == "/ranking":
        publish(f"team:{team}", ranking_text(), PRIORIDAD_NORMAL)
        return True

    if command_lower.startswith("/respuesta "):
        answer = command.split(" ", 1)[1]
        process_answer(team, answer)
        return True

    if command_lower.startswith("/codigo "):
        code = command.split(" ", 1)[1]
        process_answer(team, code)
        return True

    if command.startswith("/"):
        publish(
            f"team:{team}",
            "Comando no reconocido. Escribe /ayuda para ver los comandos.",
            PRIORIDAD_NORMAL,
        )
        return True

    # Si no empieza por /, lo tratamos como respuesta directa.
    process_answer(team, command)
    return True


def process_master_command(master_name, raw_command):
    command = raw_command.strip()

    if not command:
        return True

    command_lower = command.lower()

    if command_lower == "/salir":
        publish(f"team:{master_name}", "Game Master desconectado.", PRIORIDAD_NORMAL)
        return False

    if command_lower == "/ayuda":
        publish(f"team:{master_name}", help_master_text(), PRIORIDAD_NORMAL)
        return True

    if command_lower == "/start":
        start_game(master_name)
        return True

    if command_lower.startswith("/broadcast "):
        message = command.split(" ", 1)[1]
        publish("global", f"\n[GAME MASTER] {message}\n", PRIORIDAD_NORMAL)
        log(f"{master_name} envió broadcast: {message}")
        return True

    if command_lower.startswith("/hint "):
        parts = command.split(" ", 2)

        if len(parts) < 3:
            publish(
                f"team:{master_name}",
                "Uso correcto: /hint EQUIPO MENSAJE",
                PRIORIDAD_NORMAL,
            )
            return True

        team = parts[1]
        message = parts[2]

        with state_lock:
            exists = team in players

        if not exists:
            publish(f"team:{master_name}", f"No existe el equipo {team}.", PRIORIDAD_NORMAL)
            return True

        publish(f"team:{team}", f"\n[PISTA PRIVADA DEL GAME MASTER] {message}\n", PRIORIDAD_PISTA)
        publish(f"team:{master_name}", f"Pista enviada a {team}.", PRIORIDAD_NORMAL)
        log(f"{master_name} envió pista privada a {team}: {message}")
        return True

    if command_lower == "/ranking":
        publish(f"team:{master_name}", ranking_text(), PRIORIDAD_NORMAL)
        return True

    if command_lower == "/teams":
        with state_lock:
            team_names = list(players.keys())

        if team_names:
            text = "\nEquipos conectados:\n" + "\n".join(f"- {t}" for t in team_names)
        else:
            text = "\nNo hay equipos conectados todavía."

        publish(f"team:{master_name}", text, PRIORIDAD_NORMAL)
        return True

    if command_lower == "/pause":
        game_paused.set()
        publish("alarmas", "\n[PAUSA] La partida ha sido pausada por el Game Master.\n", PRIORIDAD_ALARMA)
        log("Partida pausada.")
        return True

    if command_lower == "/resume":
        game_paused.clear()
        publish("alarmas", "\n[REANUDACIÓN] La partida continúa.\n", PRIORIDAD_ALARMA)
        log("Partida reanudada.")
        return True

    if command_lower == "/end":
        finish_game("El Game Master ha terminado la partida manualmente.")
        return True

    publish(
        f"team:{master_name}",
        "Comando no reconocido. Escribe /ayuda.",
        PRIORIDAD_NORMAL,
    )
    return True


def register_player(conn, team_raw):
    with state_lock:
        base_name = clean_name(team_raw)
        team = unique_name_unlocked(base_name)

        client = ClientConnection(conn=conn, role="player", name=team)
        player = PlayerState(team=team, client=client)

        clients[team] = client
        players[team] = player

        for channel in ["global", "ranking", "pistas", "alarmas", f"team:{team}"]:
            add_subscription_unlocked(client, channel)

    send_text(
        client,
        f"""
Bienvenido a EscapeNet, {team}.

Espera a que el Game Master inicie la partida con /start.

Escribe /ayuda para ver los comandos.
""",
    )

    publish("global", f"[CONEXIÓN] {team} se ha unido a la partida.", PRIORIDAD_NORMAL)
    log(f"Equipo conectado: {team}")

    if game_started.is_set() and not game_finished.is_set():
        send_current_puzzle(team)

    return client


def register_master(conn):
    with state_lock:
        base_name = "GameMaster"
        master_name = unique_name_unlocked(base_name)

        client = ClientConnection(conn=conn, role="master", name=master_name)
        clients[master_name] = client

        for channel in ["global", "ranking", "pistas", "alarmas", f"team:{master_name}"]:
            add_subscription_unlocked(client, channel)

    send_text(
        client,
        f"""
Panel del Game Master conectado como {master_name}.

Escribe /ayuda para ver los comandos.
""",
    )

    log(f"Game Master conectado: {master_name}")
    return client


def cleanup_client(client):
    if client is None:
        return

    with state_lock:
        for channel in list(client.channels):
            if channel in subscriptions:
                subscriptions[channel].discard(client.name)

        clients.pop(client.name, None)

        if client.role == "player":
            players.pop(client.name, None)

    try:
        client.conn.close()
    except OSError:
        pass

    if client.role == "player":
        publish("global", f"[DESCONEXIÓN] {client.name} ha salido de la partida.", PRIORIDAD_NORMAL)

    log(f"Cliente desconectado: {client.name}")


def handle_connection(conn, addr):
    client = None

    try:
        file = conn.makefile("r", encoding=ENCODING)

        first_line = file.readline()

        if not first_line:
            return

        data = json.loads(first_line)
        role = data.get("role")

        if role == "player":
            team = data.get("team", "Equipo")
            client = register_player(conn, team)

        elif role == "master":
            client = register_master(conn)

        else:
            conn.close()
            return

        for line in file:
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                send_text(client, "Mensaje no válido.")
                continue

            if message.get("type") != "command":
                continue

            raw_command = message.get("command", "")

            if client.role == "player":
                keep_connected = process_player_command(client.name, raw_command)
            else:
                keep_connected = process_master_command(client.name, raw_command)

            if not keep_connected:
                break

    except ConnectionResetError:
        pass
    except json.JSONDecodeError:
        log(f"Error JSON desde {addr}.")
    except Exception as error:
        log(f"Error con cliente {addr}: {error}")
    finally:
        cleanup_client(client)


def main():
    threading.Thread(target=dispatcher_loop, daemon=True).start()
    threading.Thread(target=timer_listener_loop, daemon=True).start()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.bind((HOST, PORT))
    server_socket.listen()

    log(f"Servidor iniciado en {HOST}:{PORT}")
    print("\nServidor de EscapeNet iniciado.")
    print("Para jugar en este mismo ordenador, los clientes deben usar IP: 127.0.0.1")
    print("Para jugar desde otros ordenadores, deben usar la IP local de este ordenador.")
    print("Pulsa CTRL+C para apagar el servidor.\n")

    try:
        while True:
            conn, addr = server_socket.accept()
            thread = threading.Thread(target=handle_connection, args=(conn, addr), daemon=True)
            thread.start()

    except KeyboardInterrupt:
        print("\nApagando servidor...")
        finish_game("Servidor apagado.")
        timer_stop_event.set()

    finally:
        server_socket.close()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()