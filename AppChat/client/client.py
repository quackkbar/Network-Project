import socket
import threading
from datetime import datetime
import time
import queue


SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000
BUFFER_SIZE = 4096

# Queue สำหรับเก็บ Response จาก Server
response_queue = queue.Queue()


def log(message_type, message):

    timestamp = datetime.now().strftime(
        "%H:%M:%S"
    )

    print(
        f"\n[{timestamp}] "
        f"[CLIENT] [{message_type}]"
    )

    print(
        f"             {message}"
    )

    print()


def receive_messages(client_socket):
    """
    Thread เดียวสำหรับอ่านข้อมูลจาก Server
    แล้วแยกว่าเป็น Response หรือ Incoming Message
    """

    while True:

        try:

            message = receive_line(
                client_socket
            )

            if message is None:

                print(
                    "\n[SERVER DISCONNECTED]"
                )

                break

            # =========================
            # Incoming Message
            # =========================

            if message.startswith("MESSAGE "):

                log(
                    "INCOMING",
                    message
                )

            # =========================
            # Response
            # =========================

            else:

                response_queue.put(
                    message
                )

        except ConnectionResetError:

            print(
                "\n[CONNECTION LOST]"
            )

            break

        except OSError:

            break

def receive_line(client_socket):
    """รับข้อมูลจนกว่าจะเจอ \\n"""

    data = b""

    while b"\n" not in data:

        chunk = client_socket.recv(1)

        if not chunk:
            return None

        data += chunk

    return data.decode("utf-8").strip()

def send_request(
    client_socket,
    request
):

    # เริ่มจับเวลา
    start_time = time.perf_counter()

    # =========================
    # ส่ง Request
    # =========================

    client_socket.sendall(
        (request + "\n").encode("utf-8")
    )

    log(
        "SEND",
        request
    )

    # =========================
    # รอ Response จาก Queue
    # =========================

    try:

        response = response_queue.get(
            timeout=10
        )

    except queue.Empty:

        print(
            "[ERROR] Response timeout."
        )

        return ""

    # หยุดจับเวลา
    end_time = time.perf_counter()

    # คำนวณเวลา
    response_time = (
        end_time - start_time
    ) * 1000

    log(
        "RECEIVE RESPONSE",
        response
    )

    print(
        f"[PERFORMANCE] "
        f"Response Time: "
        f"{response_time:.2f} ms"
    )

    print()

    return response


def start_client():

    client_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    try:

        print("=" * 50)
        print("              NetChat Client")
        print("=" * 50)

        print(
            f"[CONNECTING] "
            f"{SERVER_HOST}:{SERVER_PORT}"
        )

        client_socket.connect(
            (
                SERVER_HOST,
                SERVER_PORT
            )
        )
        
        # =========================
        # เริ่ม Thread รับข้อมูล
        # =========================

        receiver_thread = threading.Thread(
            target=receive_messages,
            args=(client_socket,),
            daemon=True
        )

        receiver_thread.start()

        print(
            "[CONNECTED] "
            "Successfully connected."
        )

        print()

        # =========================
        # LOGIN
        # =========================

        username = input(
            "Enter username: "
        )

        login_request = (
            f"LOGIN {username}"
        )

        login_response = send_request(
            client_socket,
            login_request
        )

        # ถ้า Login ไม่สำเร็จ
        if not login_response.startswith(
            "200 OK"
        ):

            return

        print("=" * 50)
        print("Commands:")
        print("LIST")
        print("SEND <username> <message>")
        print("SENDALL <message>")
        print("QUIT")
        print("=" * 50)

        # =========================
        # Main Command Loop
        # =========================

        while True:

            command = input(
                "> "
            )

            if not command:
                continue

            # -------------------------
            # LIST
            # -------------------------

            if command.upper() == "LIST":

                send_request(
                    client_socket,
                    "LIST"
                )

            # -------------------------
            # SEND
            # -------------------------

            elif command.upper().startswith(
                "SEND "
            ):

                send_request(
                    client_socket,
                    command
                )
                
            # -------------------------
            # SENDALL
            # -------------------------
            
            elif command.upper().startswith(
                "SENDALL "
            ):

                send_request(
                    client_socket,
                     command
                )

            # -------------------------
            # QUIT
            # -------------------------

            elif command.upper() == "QUIT":

                response = send_request(
                    client_socket,
                    "QUIT"
                )
                if response.startswith("200 OK BYE"):
                    print("[STATUS] You are now offline.")

                break

            # -------------------------
            # Unknown
            # -------------------------

            else:

                print(
                    "[ERROR] Unknown command."
                )

                print(
                    "Use LIST, SEND or QUIT."
                )

    except ConnectionRefusedError:

        print(
            "[ERROR] Cannot connect "
            "to server."
        )

    except ConnectionResetError:

        print(
            "[ERROR] Server closed "
            "the connection."
        )

    finally:

        client_socket.close()

        print(
            "[DISCONNECTED]"
        )


if __name__ == "__main__":

    start_client()
    
