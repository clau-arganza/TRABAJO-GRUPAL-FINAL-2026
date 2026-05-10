# cliente.py
# Cliente de los equipos jugadores.

import json
import socket
import threading


ENCODING = "utf-8"
DEFAULT_PORT = 5050


def send_packet(sock, payload):
    data = json.dumps(payload, ensure_ascii=False) + "\n"
    sock.sendall(data.encode(ENCODING))


def receiver_loop(sock):
    file = sock.makefile("r", encoding=ENCODING)

    try:
        for line in file:
            try:
                data = json.loads(line)
                print(data.get("text", ""))
            except json.JSONDecodeError:
                print("[ERROR] Mensaje recibido no válido.")

    except OSError:
        pass

    print("\nConexión cerrada por el servidor.")


def main():
    print("=" * 60)
    print("ESCAPENET - CLIENTE JUGADOR")
    print("=" * 60)

    host = input("Introduce la IP del servidor [127.0.0.1]: ").strip()

    if not host:
        host = "127.0.0.1"

    team = input("Introduce el nombre de tu equipo: ").strip()

    if not team:
        team = "Equipo"

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        sock.connect((host, DEFAULT_PORT))
    except OSError as error:
        print(f"No se pudo conectar con el servidor: {error}")
        return

    send_packet(sock, {
        "type": "register",
        "role": "player",
        "team": team,
    })

    receiver = threading.Thread(target=receiver_loop, args=(sock,), daemon=True)
    receiver.start()

    print("\nConectado. Escribe /ayuda para ver comandos.")
    print("También puedes escribir las respuestas directamente.\n")

    try:
        while True:
            command = input("> ")

            send_packet(sock, {
                "type": "command",
                "command": command,
            })

            if command.strip().lower() == "/salir":
                break

    except KeyboardInterrupt:
        try:
            send_packet(sock, {
                "type": "command",
                "command": "/salir",
            })
        except OSError:
            pass

    except OSError:
        print("Se perdió la conexión con el servidor.")

    finally:
        sock.close()
        print("Cliente cerrado.")


if __name__ == "__main__":
    main()