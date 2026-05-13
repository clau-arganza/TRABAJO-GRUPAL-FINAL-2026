# EscapeNet: Escape Room distribuido en tiempo real

## Descripción del proyecto

EscapeNet es una aplicación distribuida desarrollada en Python que simula un escape room multijugador en tiempo real. El sistema permite que varios equipos se conecten desde diferentes terminales u ordenadores, resuelvan salas de forma simultánea y compitan por escapar introduciendo un código final.

El proyecto utiliza una arquitectura cliente-servidor. Un servidor central controla toda la lógica de la partida, mientras que los equipos jugadores se conectan como clientes. Además, existe un cliente especial llamado Game Master, que permite iniciar la partida, enviar mensajes, dar pistas, consultar el ranking, pausar, reanudar o finalizar el juego.

El objetivo principal del proyecto es aplicar conceptos de programación paralela y distribuida vistos en la asignatura: sockets, hilos, sincronización, semáforos, eventos, colas de prioridad, procesos, comunicación en tiempo real y registro de actividad.

## Objetivo del juego

Los equipos deben superar seis salas. Cada sala contiene un acertijo o una prueba. Cuando un equipo responde correctamente, avanza a la siguiente sala y obtiene una letra del código final.

Las letras obtenidas forman el código:

```text
FAUSTO
```

El primer equipo que complete todas las salas e introduzca correctamente el código final gana la partida.

## Estructura del proyecto

```text
escape_net/
│
├── servidor.py
├── cliente.py
├── game_master.py
├── puzzles.py
├── logger.py
├── logs_partida.txt
└── README.md
```

### servidor.py

Es el archivo principal del sistema. Se encarga de iniciar el servidor, aceptar conexiones de clientes, gestionar la partida, comprobar respuestas, actualizar el ranking, enviar mensajes y controlar el estado general del juego.

### cliente.py

Es el archivo que ejecutan los equipos jugadores. Permite conectarse al servidor, recibir salas, enviar respuestas, pedir pistas, consultar el estado del equipo y ver el ranking.

### game_master.py

Es el panel de control del Game Master. Permite iniciar la partida, mandar mensajes globales, enviar pistas privadas, consultar los equipos conectados, ver el ranking, pausar, reanudar o terminar la partida.

### puzzles.py

Contiene las salas del escape room: enunciados, respuestas correctas, pistas y letras que se entregan al resolver cada sala.

### logger.py

Gestiona el registro de actividad. Los eventos importantes se muestran por consola y se guardan en el archivo `logs_partida.txt`.

### logs_partida.txt

Archivo donde queda registrada la actividad de la partida: conexiones, respuestas, pistas, mensajes del Game Master y finalización del juego.

## Conceptos de la asignatura utilizados

### Sockets

La comunicación entre el servidor, los clientes y el Game Master se realiza mediante sockets TCP. El servidor escucha conexiones en un puerto determinado y los clientes se conectan introduciendo la IP del ordenador donde se está ejecutando el servidor.

Esto permite que el proyecto funcione tanto en varias terminales de un mismo ordenador como en varios ordenadores conectados a la misma red WiFi.

### Arquitectura cliente-servidor

EscapeNet sigue una arquitectura cliente-servidor:

```text
Servidor central
│
├── Cliente jugador 1
├── Cliente jugador 2
├── Cliente jugador 3
├── Cliente jugador 4
└── Game Master
```

El servidor centraliza la lógica del juego. Los clientes envían respuestas y comandos, pero no controlan directamente la partida. El Game Master también se conecta al servidor, pero tiene funciones especiales de control.

### Threading

El servidor utiliza hilos para atender a varios clientes al mismo tiempo. Cada vez que un equipo se conecta, el servidor crea un hilo independiente para gestionar su comunicación.

Los clientes también utilizan hilos: uno para recibir mensajes del servidor y otro para permitir que el usuario escriba comandos o respuestas. Esto permite que los equipos reciban avisos, pistas o mensajes globales mientras están jugando.

### Lock

Se utiliza un `Lock` para proteger datos compartidos, como:

- ranking;
- puntuación;
- progreso de cada equipo;
- número de pistas usadas;
- número de errores;
- estado de la partida.

Esto evita problemas de concurrencia cuando varios equipos responden o piden pistas al mismo tiempo.

### Semaphore

Se utiliza un `Semaphore` para limitar el número de equipos que pueden pedir pista simultáneamente. En este proyecto, solo dos equipos pueden acceder al sistema de pistas al mismo tiempo.

Esto permite simular un recurso limitado y aplicar control de acceso concurrente.

### Event

Se utilizan eventos para coordinar el estado general de la partida:

- inicio de la partida;
- pausa;
- reanudación;
- finalización.

Por ejemplo, los equipos pueden conectarse antes de que empiece el juego, pero no reciben las salas hasta que el Game Master ejecuta el comando `/start`.

### Queue y PriorityQueue

El servidor utiliza una cola de prioridad para gestionar los mensajes que se envían a los clientes.

Los mensajes urgentes, como alarmas o fin de partida, tienen mayor prioridad que los mensajes normales. Esto permite que los avisos importantes se procesen antes.

Ejemplo de prioridades:

```text
1 → alarmas
2 → respuestas correctas
3 → pistas
4 → mensajes normales
```

### Pub/Sub simulado

Aunque el sistema utiliza sockets TCP, se ha implementado una lógica similar al modelo Publicación/Suscripción mediante canales.

Algunos canales del sistema son:

```text
global       → mensajes para todos los equipos
ranking      → actualizaciones de clasificación
alarmas      → avisos importantes
pistas       → mensajes relacionados con pistas
team:Alfa    → mensajes privados para el equipo Alfa
team:Beta    → mensajes privados para el equipo Beta
```

De esta forma, el servidor puede enviar mensajes a todos los equipos o solo a un equipo concreto.

### Multiprocessing

El temporizador de la partida se ejecuta mediante un proceso independiente. Este proceso controla el tiempo restante y envía avisos al servidor cuando queda poco tiempo.

Esto permite separar el control del tiempo de la lógica principal del servidor.

### Logs

Toda la actividad relevante queda registrada en consola y en el archivo `logs_partida.txt`.

Se registran eventos como:

- conexión de equipos;
- inicio de la partida;
- respuestas enviadas;
- pistas solicitadas;
- mensajes del Game Master;
- finalización de la partida;
- equipo ganador.

## Salas del escape room

El juego está formado por seis salas.

### Sala 1: La puerta bloqueada

Enunciado:

```text
Si A = 1, B = 2, C = 3...
¿Cuánto vale la palabra RED?
```

Respuesta correcta:

```text
27
```

Letra obtenida:

```text
F
```

### Sala 2: La ecuación del laboratorio

Enunciado:

```text
2x + 6 = 18

¿Qué valor tiene x?
```

Respuesta correcta:

```text
6
```

Letra obtenida:

```text
A
```

### Sala 3: La sala del espejo

Enunciado:

```text
Si me tumbas, soy todo.
Si me cortas por la cintura, me quedo en nada.

¿Qué soy?
```

Respuesta correcta:

```text
8
```

También acepta:

```text
ocho
```

Letra obtenida:

```text
U
```

### Sala 4: La alarma de los cables

Enunciado:

```text
Hay tres cables: rojo, azul y verde.

Pista: no cortes el color del fuego ni el color de la naturaleza.

¿Qué cable cortas?
```

Respuesta correcta:

```text
azul
```

Letra obtenida:

```text
S
```

### Sala 5: Pasapalabra sospechoso

Enunciado:

```text
Con la P:

Acción que le gusta hacer a Rodrigo y que no es del todo legal.
```

Respuesta correcta:

```text
piratear
```

Letra obtenida:

```text
T
```

### Sala 6: La habitación a oscuras

Enunciado:

```text
Entras en una habitación completamente oscura.

Dentro hay una vela, una chimenea y una lámpara de aceite.

Solo tienes una cerilla.

¿Qué enciendes primero?
```

Respuesta correcta:

```text
cerilla
```

También acepta:

```text
la cerilla
```

Letra obtenida:

```text
O
```

## Código final

Después de superar las seis salas, el equipo obtiene las letras del código final:

```text
F A U S T O
```

El código final es:

```text
FAUSTO
```

El equipo puede introducirlo directamente:

```text
FAUSTO
```

O usando el comando:

```text
/codigo FAUSTO
```

## Normalización de respuestas

El sistema normaliza las respuestas antes de comprobarlas. Esto significa que acepta respuestas con mayúsculas, minúsculas o espacios al principio y al final.

Por ejemplo, todas estas respuestas son válidas:

```text
fausto
Fausto
FAUSTO
```

También se aceptan respuestas como:

```text
azul
Azul
AZUL
```

Esto evita errores innecesarios por formato.

## Sistema de puntuación

El sistema utiliza una puntuación para ordenar a los equipos en el ranking.

Reglas principales:

```text
+100 puntos por cada sala superada
-20 puntos por cada pista usada
-10 puntos por cada respuesta incorrecta
+50 puntos extra por introducir correctamente el código final
```

El ranking muestra:

- nombre del equipo;
- sala actual;
- puntuación;
- pistas usadas;
- errores cometidos;
- letras conseguidas.

## Requisitos

Para ejecutar el proyecto es necesario tener instalado Python 3.

Se puede comprobar con:

```bash
python3 --version
```

O, en algunos ordenadores:

```bash
python --version
```

El proyecto utiliza únicamente bibliotecas estándar de Python, por lo que no es necesario instalar dependencias externas.

## Ejecución en un solo ordenador

Para probar el proyecto en un solo ordenador, se deben abrir varias terminales dentro de la carpeta del proyecto.

### 1. Ejecutar el servidor

En la primera terminal:

```bash
python3 servidor.py
```

Si no funciona, probar:

```bash
python servidor.py
```

### 2. Ejecutar el Game Master

En otra terminal:

```bash
python3 game_master.py
```

Si no funciona:

```bash
python game_master.py
```

Cuando pida la IP del servidor, escribir:

```text
127.0.0.1
```

### 3. Ejecutar los clientes jugadores

En otra terminal:

```bash
python3 cliente.py
```

Cuando pida la IP del servidor, escribir:

```text
127.0.0.1
```

Cuando pida el nombre del equipo, escribir un nombre simple, por ejemplo:

```text
Alfa
```

Para crear más equipos, abrir más terminales y volver a ejecutar:

```bash
python3 cliente.py
```

Ejemplos de nombres de equipo:

```text
Alfa
Beta
Gamma
Delta
```

## Ejecución en varios ordenadores

Para que varios equipos participen desde sus propios ordenadores, todos deben estar conectados a la misma red WiFi.

### 1. Ordenador del servidor

En el ordenador principal, ejecutar:

```bash
python3 servidor.py
```

Después, abrir otra terminal y ejecutar:

```bash
python3 game_master.py
```

En el Game Master, como se ejecuta en el mismo ordenador que el servidor, se debe introducir:

```text
127.0.0.1
```

### 2. Obtener la IP local del ordenador servidor

En Mac, abrir una terminal y escribir:

```bash
ipconfig getifaddr en0
```

Si no aparece nada, probar:

```bash
ipconfig getifaddr en1
```

El resultado será una IP parecida a:

```text
172.20.10.2
```

Esa es la IP que deben introducir los demás equipos.

### 3. Ordenadores de los equipos

Cada equipo debe abrir el proyecto en su ordenador y ejecutar:

```bash
python3 cliente.py
```

Cuando el programa pida la IP del servidor, deben introducir la IP local del ordenador que está ejecutando `servidor.py`.

Ejemplo:

```text
172.20.10.2
```

Después deben introducir un nombre de equipo sin espacios, como:

```text
Alfa
Beta
Gamma
Delta
```

## Comandos del Game Master

### Ver equipos conectados

```text
/teams
```

Muestra los equipos que se han unido a la partida.

### Iniciar la partida

```text
/start
```

Inicia el escape room y envía la primera sala a todos los equipos.

### Enviar un mensaje global

```text
/broadcast MENSAJE
```

Ejemplo:

```text
/broadcast Quedan pocos minutos para escapar.
```

Este mensaje lo reciben todos los equipos.

### Enviar una pista privada

```text
/hint EQUIPO MENSAJE
```

Ejemplo:

```text
/hint Alfa Fíjate en la posición de las letras en el abecedario.
```

El mensaje solo lo recibe el equipo indicado.

### Ver ranking

```text
/ranking
```

Muestra la clasificación actual.

### Pausar la partida

```text
/pause
```

Pausa temporalmente la partida.

### Reanudar la partida

```text
/resume
```

Reanuda la partida.

### Finalizar la partida

```text
/end
```

Termina la partida manualmente.

### Ver ayuda

```text
/ayuda
```

Muestra la lista de comandos disponibles.

## Comandos de los equipos jugadores

### Enviar respuesta

Se puede escribir la respuesta directamente:

```text
27
```

También se puede usar:

```text
/respuesta 27
```

### Pedir pista

```text
/pista
```

Solicita una pista automática de la sala actual. Usar una pista resta 20 puntos.

### Ver estado del equipo

```text
/estado
```

Muestra la sala actual, puntuación, pistas usadas, fallos y letras conseguidas.

### Ver ranking

```text
/ranking
```

Muestra la clasificación de los equipos.

### Enviar código final

Cuando un equipo completa todas las salas, puede introducir el código directamente:

```text
FAUSTO
```

O usar:

```text
/codigo FAUSTO
```

### Salir de la partida

```text
/salir
```

Desconecta al equipo del servidor.

## Orden recomendado para una demostración

Para hacer una demostración rápida:

1. Ejecutar `servidor.py`.
2. Ejecutar `game_master.py`.
3. Conectar dos o más clientes con `cliente.py`.
4. Desde Game Master, comprobar los equipos conectados:

```text
/teams
```

5. Iniciar la partida:

```text
/start
```

6. Un equipo responde correctamente a la primera sala:

```text
27
```

7. Otro equipo pide una pista:

```text
/pista
```

8. El Game Master envía un mensaje global:

```text
/broadcast Quedan pocos minutos para escapar.
```

9. El Game Master consulta el ranking:

```text
/ranking
```

10. Un equipo resuelve las salas restantes:

```text
6
8
azul
piratear
cerilla
FAUSTO
```

11. Mostrar el archivo de logs:

```bash
tail -n 20 logs_partida.txt
```

## Posibles problemas y soluciones

### Error: Address already in use

Si aparece un error parecido a:

```text
OSError: [Errno 48] Address already in use
```

significa que el puerto del servidor ya está ocupado, probablemente porque hay otro servidor ejecutándose.

En Mac, se puede comprobar con:

```bash
lsof -iTCP:5050 -sTCP:LISTEN -n -P
```

Después, cerrar el proceso correspondiente o usar:

```bash
pkill -f "servidor.py"
```

Luego volver a ejecutar:

```bash
python3 servidor.py
```

### Los clientes no se conectan desde otros ordenadores

Comprobar que:

- todos los ordenadores están en la misma red WiFi;
- el servidor está ejecutándose;
- los clientes están introduciendo la IP correcta;
- los clientes no están usando `127.0.0.1` desde otro ordenador;
- el firewall no está bloqueando la conexión.

### El Game Master se conecta pero los otros equipos no

El Game Master puede usar `127.0.0.1` porque está en el mismo ordenador que el servidor. Sin embargo, los demás equipos deben usar la IP local del ordenador servidor.

### El comando /hint no encuentra al equipo

Primero consultar los nombres exactos:

```text
/teams
```

Después usar el nombre tal y como aparece.

Ejemplo:

```text
/hint Alfa Revisa bien el enunciado.
```

Se recomienda usar nombres de equipo sin espacios.

## Conclusión

EscapeNet es una aplicación distribuida que combina juego e interacción en tiempo real con conceptos técnicos de programación paralela y distribuida. El proyecto utiliza sockets para la comunicación entre nodos, hilos para atender a varios clientes simultáneamente, mecanismos de sincronización para proteger datos compartidos, semáforos para controlar recursos, eventos para coordinar la partida, colas de prioridad para ordenar mensajes, un proceso independiente para el temporizador y logs para registrar la actividad.

El resultado es un escape room multijugador funcional, ejecutable en varias terminales o en varios ordenadores conectados a la misma red.
