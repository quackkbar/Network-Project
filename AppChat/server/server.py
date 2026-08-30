import socket
import threading
from datetime import datetime


HOST = "0.0.0.0"
PORT = 5000
BUFFER_SIZE = 4096

# เก็บ User ที่ Online
# รูปแบบ:
# {
#     "Prem": socket,
#     "Bank": socket
# }
online_users = {}
send_locks = {}
# ตัวนับ Message ID
message_counter = 0

# Lock สำหรับ Message ID
message_lock = threading.Lock()
# ป้องกันการแก้ไข online_users พร้อมกัน
users_lock = threading.Lock()

def generate_message_id():
    """สร้าง Message ID"""

    global message_counter

    with message_lock:

        message_counter += 1

        return f"MSG-{message_counter:04d}"
    
def get_send_lock(client_socket):
    """คืนค่า Lock สำหรับ Socket แต่ละตัว"""

    with users_lock:

        if client_socket not in send_locks:
            send_locks[client_socket] = threading.Lock()

        return send_locks[client_socket]

def send_message(client_socket, message):
    """ส่งข้อมูลผ่าน Socket โดยป้องกันการส่งชนกัน"""

    lock = get_send_lock(client_socket)

    with lock:

        client_socket.sendall(
            (message + "\n").encode("utf-8")
        )

def log(message_type, message):
    """แสดง Protocol Log"""

    timestamp = datetime.now().strftime("%H:%M:%S")

    print(
        f"[{timestamp}] [SERVER] [{message_type}]"
    )

    print(
        f"             {message}"
    )

    print()


def get_username(client_socket):
    """ค้นหา Username จาก Socket"""

    with users_lock:

        for username, sock in online_users.items():

            if sock == client_socket:
                return username

    return None





def handle_request(message, client_socket):

    parts = message.strip().split()

    if len(parts) == 0:
        return "400 BAD_REQUEST"

    command = parts[0].upper()

    # =========================
    # LOGIN
    # =========================

    if command == "LOGIN":

        if len(parts) != 2:
            return "400 BAD_REQUEST"

        username = parts[1]

        with users_lock:

            if username in online_users:
                return "409 CONFLICT USERNAME_TAKEN"

            online_users[username] = client_socket

        return f"200 OK LOGIN_SUCCESS {username}"

    # =========================
    # LIST
    # =========================

    elif command == "LIST":

        username = get_username(client_socket)

        if username is None:
            return "401 UNAUTHORIZED LOGIN_REQUIRED"

        with users_lock:
            usernames = list(
                online_users.keys()
            )

        response = (
            f"200 OK USER_LIST "
            f"{','.join(usernames)}"
        )

        return response

    # =========================
    # SEND
    # =========================

    elif command == "SEND":

        sender = get_username(client_socket)

        # ต้อง Login ก่อน
        if sender is None:
            return (
                "401 UNAUTHORIZED "
                "LOGIN_REQUIRED"
            )

        # ต้องมีอย่างน้อย:
        # SEND <username> <message>
        if len(parts) < 3:
            return "400 BAD_REQUEST"

        receiver = parts[1]

        # เอาข้อความตั้งแต่คำที่ 3 เป็นต้นไป
        message_text = " ".join(parts[2:])

        # ตรวจสอบว่าปลายทางมีอยู่หรือไม่
        with users_lock:

            if receiver not in online_users:
                return (
                    "404 NOT_FOUND "
                    "USER_NOT_FOUND"
                )

            # สร้าง Message ID
        message_id = generate_message_id()
        
        # สร้าง Message สำหรับผู้รับ
        chat_message = (
            f"MESSAGE {message_id} "
            f"MESSAGE {sender} {message_text}"
        )

        # ส่งให้ผู้รับ
        success = send_to_user(
            receiver,
            chat_message
        )

        if not success:
            return (
                "500 SERVER_ERROR "
                "DELIVERY_FAILED"
            )

        # แสดง Log ฝั่ง Server
        log(
            "SEND",
            f"TO={receiver} | {chat_message}"
        )

        return (
          "200 OK MESSAGE_SENT "
          f"{message_id}"
        )
      
      # =========================
      # SENDALL
      # =========================

    elif command == "SENDALL":

        sender = get_username(client_socket)

        # ต้อง Login ก่อน
        if sender is None:
            return (
              "401 UNAUTHORIZED "
              "LOGIN_REQUIRED"
          )

        # ต้องมีข้อความ
        if len(parts) < 2:
            return "400 BAD_REQUEST"

        # รวมข้อความทั้งหมดหลัง SENDALL
        message_text = " ".join(parts[1:])

        # สร้าง Message ID
        message_id = generate_message_id()
    
        chat_message = (
            f"MESSAGE {message_id} "
            f"{sender} {message_text}"
        )

        # เก็บรายชื่อ User ทั้งหมด
        with users_lock:
            users = list(online_users.items())

        # ส่งให้ทุกคน
        for username, target_socket in users:
          
            #ไม่ส่งกลับไปหา sender
            if target_socket == client_socket:
                continue
              
            try:

                send_message(
                    target_socket,
                    chat_message
                )

                log(
                    "SEND",
                    f"TO={username} | {chat_message}"
                )

            except (
                ConnectionResetError,
                BrokenPipeError
            ):
                pass

        return (
            f"200 OK BROADCAST_SENT "
            f"{message_id}"
        )

    # =========================
    # QUIT
    # =========================

    elif command == "QUIT":

        username = get_username(
            client_socket
        )

        if username is None:
            return (
                "401 UNAUTHORIZED "
                "LOGIN_REQUIRED"
            )

        with users_lock:

            if username in online_users:
                del online_users[username]

        return "200 OK BYE"

    # =========================
    # UNKNOWN COMMAND
    # =========================

    else:

        return (
            "400 BAD_REQUEST "
            "UNKNOWN_COMMAND"
        )

def send_to_user(username, message):
    """ส่งข้อความไปยัง User ที่ระบุ"""

    with users_lock:
        target_socket = online_users.get(username)

    if target_socket is None:
        return False

    try:

        send_message(
            target_socket,
            message
        )

        return True

    except (
        ConnectionResetError,
        BrokenPipeError
    ):
        return False

def remove_user(client_socket):

    username = get_username(
        client_socket
    )

    if username:

        with users_lock:

            if username in online_users:
                del online_users[username]
            send_locks.pop(
            client_socket,
            None
            )
            
        print(
            f"[USER OFFLINE] {username}"
        )

        print()

def receive_line(client_socket):
    data = b""

    while b"\n" not in data:
        chunk = client_socket.recv(1)

        if not chunk:
            return None

        data += chunk

    return data.decode("utf-8").strip()

def handle_client(
    client_socket,
    client_address
):

    client_ip = client_address[0]
    client_port = client_address[1]

    print("[CLIENT CONNECTED]")

    print(
        f"             IP   : {client_ip}"
    )

    print(
        f"             Port : {client_port}"
    )

    print()

    try:

        while True:

            message = receive_line(
                client_socket
            )

            if message is None:
                break

            log(
                "RECEIVE",
                message
            )

            response = handle_request(
                message,
                client_socket
            )

            send_message(
                client_socket,
                response
            )

            log(
                "SEND",
                response
            )

            # ถ้า QUIT ให้จบ Connection
            if message.strip().upper() == "QUIT":
                break

    except ConnectionResetError:

        print(
            "[CLIENT DISCONNECTED]"
        )

        print()

    finally:

        remove_user(
            client_socket
        )

        client_socket.close()

        print(
            f"[CONNECTION CLOSED] "
            f"{client_ip}:{client_port}"
        )

        print()


def start_server():

    server_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server_socket.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    server_socket.bind(
        (HOST, PORT)
    )

    server_socket.listen(10)

    print("=" * 50)
    print("              NetChat Server")
    print("=" * 50)

    print(
        f"[LISTENING] {HOST}:{PORT}"
    )

    print(
        "Waiting for clients...\n"
    )

    while True:

        client_socket, client_address = (
            server_socket.accept()
        )

        client_thread = threading.Thread(
            target=handle_client,
            args=(
                client_socket,
                client_address
            )
        )

        client_thread.daemon = True

        client_thread.start()


if __name__ == "__main__":

    try:

        start_server()

    except KeyboardInterrupt:

        print(
            "\n[SERVER] Server stopped."
        )