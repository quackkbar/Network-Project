import tkinter as tk
from tkinter import messagebox
import socket
import time
import threading
import queue


SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000


# =========================================================
# NCP Client
# =========================================================

class ChatClient:

    def __init__(self):

        self.sock = None
        self.username = None
        self.running = False

        # Queue สำหรับ Response ของ Request
        self.response_queue = queue.Queue()

        # Queue สำหรับ MESSAGE ที่เข้ามา
        self.message_queue = queue.Queue()

        # Thread สำหรับรับข้อมูลจาก Server
        self.receive_thread = None

        # Lock สำหรับการส่งข้อมูล
        self.send_lock = threading.Lock()

    # =====================================================
    # Login
    # =====================================================

    def login(self, username):

        try:

            self.sock = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM
            )

            self.sock.connect(
                (
                    SERVER_HOST,
                    SERVER_PORT
                )
            )

            request = f"LOGIN {username}"

            start_time = time.perf_counter()

            with self.send_lock:

                self.sock.sendall(
                    (
                        request + "\n"
                    ).encode("utf-8")
                )

            print("[CLIENT] [SEND]")
            print(request)

            # Login เป็น Request แรก
            response = self.receive_line()

            end_time = time.perf_counter()

            response_time = (
                end_time - start_time
            ) * 1000

            print("[CLIENT] [RECEIVE]")
            print(response)

            print(
                f"[PERFORMANCE] "
                f"Response Time: "
                f"{response_time:.2f} ms"
            )

            print()

            if (
                response
                and response.startswith("200 OK")
            ):

                self.username = username
                self.running = True

                # เริ่ม Receiver Thread
                self.start_receiver()

                return True

            return False

        except Exception as e:

            print(
                "[LOGIN ERROR]",
                e
            )

            return False

    # =====================================================
    # Receive Line
    # =====================================================

    def receive_line(self):

        data = b""

        while b"\n" not in data:

            chunk = self.sock.recv(1)

            if not chunk:
                return None

            data += chunk

        return data.decode(
            "utf-8"
        ).strip()

    # =====================================================
    # Receiver Thread
    # =====================================================

    def start_receiver(self):

        self.receive_thread = threading.Thread(
            target=self.receive_messages,
            daemon=True
        )

        self.receive_thread.start()

    def receive_messages(self):

        while self.running:

            try:

                message = self.receive_line()

                if not message:
                    break

                # =========================================
                # MESSAGE จาก User
                # =========================================

                if message.startswith("MESSAGE"):

                    print(
                        "[CLIENT] "
                        "[RECEIVE MESSAGE]"
                    )

                    print(message)

                    print()

                    self.message_queue.put(
                        message
                    )

                # =========================================
                # Response จาก Server
                # =========================================

                else:

                    print(
                        "[CLIENT] "
                        "[RECEIVE RESPONSE]"
                    )

                    print(message)

                    print()

                    self.response_queue.put(
                        message
                    )

            except Exception as e:

                if self.running:

                    print(
                        "[RECEIVER ERROR]",
                        e
                    )

                break

    # =====================================================
    # Send Request
    # =====================================================

    def send_request(self, request):

        try:

            start_time = time.perf_counter()

            with self.send_lock:

                self.sock.sendall(
                    (
                        request + "\n"
                    ).encode("utf-8")
                )

            print("[CLIENT] [SEND]")
            print(request)

            # รอ Response ที่ Receiver Thread
            # แยกเอาไว้ให้แล้ว
            response = self.response_queue.get()

            end_time = time.perf_counter()

            response_time = (
                end_time - start_time
            ) * 1000

            print(
                f"[PERFORMANCE] "
                f"Response Time: "
                f"{response_time:.2f} ms"
            )

            print()

            return response

        except Exception as e:

            print(
                "[REQUEST ERROR]",
                e
            )

            return None

    # =====================================================
    # Close
    # =====================================================

    def close(self):

        self.running = False

        try:

            self.sock.close()

        except:
            pass


# =========================================================
# Chat Window
# =========================================================

class ChatWindow:

    def __init__(
        self,
        root,
        client
    ):

        self.root = root
        self.client = client

        self.root.title(
            f"AppChat - {client.username}"
        )

        self.root.geometry(
            "800x550"
        )

        self.root.minsize(
            700,
            450
        )

        # =================================================
        # Main Frame
        # =================================================

        main_frame = tk.Frame(
            root
        )

        main_frame.pack(
            fill=tk.BOTH,
            expand=True
        )

        # =================================================
        # Online Users
        # =================================================

        users_frame = tk.Frame(
            main_frame,
            width=180
        )

        users_frame.pack(
            side=tk.LEFT,
            fill=tk.Y,
            padx=(10, 5),
            pady=10
        )

        tk.Label(
            users_frame,
            text="Online Users",
            font=("Arial", 14, "bold")
        ).pack(
            pady=(5, 10)
        )

        self.user_list = tk.Listbox(
            users_frame,
            width=22,
            font=("Arial", 11)
        )

        self.user_list.pack(
            fill=tk.BOTH,
            expand=True
        )

        tk.Button(
            users_frame,
            text="Refresh",
            command=self.refresh_users
        ).pack(
            fill=tk.X,
            pady=(10, 0)
        )

        # =================================================
        # Chat
        # =================================================

        chat_frame = tk.Frame(
            main_frame
        )

        chat_frame.pack(
            side=tk.RIGHT,
            fill=tk.BOTH,
            expand=True,
            padx=(5, 10),
            pady=10
        )

        tk.Label(
            chat_frame,
            text="Chat",
            font=("Arial", 14, "bold")
        ).pack(
            anchor=tk.W,
            pady=(5, 10)
        )

        self.chat_area = tk.Text(
            chat_frame,
            state=tk.DISABLED,
            wrap=tk.WORD,
            font=("Arial", 11)
        )

        self.chat_area.pack(
            fill=tk.BOTH,
            expand=True
        )

        # =================================================
        # Input
        # =================================================

        input_frame = tk.Frame(
            chat_frame
        )

        input_frame.pack(
            fill=tk.X,
            pady=(10, 0)
        )

        self.message_entry = tk.Entry(
            input_frame,
            font=("Arial", 11)
        )

        self.message_entry.pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True
        )

        self.send_button = tk.Button(
            input_frame,
            text="SEND",
            width=10,
            command=self.send_message
        )

        self.send_button.pack(
            side=tk.RIGHT,
            padx=(10, 0)
        )

        self.message_entry.bind(
            "<Return>",
            lambda event: self.send_message()
        )

        # =================================================
        # Status
        # =================================================

        self.status_label = tk.Label(
            root,
            text=f"Connected as {client.username}",
            anchor=tk.W
        )

        self.status_label.pack(
            fill=tk.X,
            padx=10,
            pady=(0, 5)
        )

        # =================================================
        # Window Close
        # =================================================

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.on_close
        )

        # เริ่มตรวจ MESSAGE
        self.check_messages()

        # โหลด User List
        self.root.after(
            200,
            self.refresh_users
        )

    # =====================================================
    # Add Chat Message
    # =====================================================

    def add_chat_message(self, text):

        self.chat_area.config(
            state=tk.NORMAL
        )

        self.chat_area.insert(
            tk.END,
            text + "\n"
        )

        self.chat_area.see(
            tk.END
        )

        self.chat_area.config(
            state=tk.DISABLED
        )

    # =====================================================
    # Check Incoming Messages
    # =====================================================

    def check_messages(self):

        try:

            while True:

                message = (
                    self.client
                    .message_queue
                    .get_nowait()
                )

                print(
                    "[GUI] Incoming:",
                    message
                )

                self.display_message(
                    message
                )

        except queue.Empty:
            pass

        if self.client.running:

            self.root.after(
                100,
                self.check_messages
            )

    # =====================================================
    # Display MESSAGE
    # =====================================================

    def display_message(self, message):

        # ตัวอย่าง:
        #
        # MESSAGE MSG-0210 MESSAGE prame hello
        #
        # หรือ
        #
        # MESSAGE MSG-0210 prame hello

        parts = message.split(
            " ",
            3
        )

        if len(parts) >= 4:

            message_id = parts[1]

            sender = parts[2]

            text = parts[3]

            # กรณี Server มี MESSAGE ซ้ำ
            if sender.upper() == "MESSAGE":

                remaining = text.split(
                    " ",
                    1
                )

                if len(remaining) == 2:

                    sender = remaining[0]

                    text = remaining[1]

            self.add_chat_message(
                f"{sender}: {text} "
                f"[{message_id}]"
            )

        else:

            # ถ้ารูปแบบไม่ตรง
            # แสดง Raw Message ไปก่อน
            self.add_chat_message(
                message
            )

    # =====================================================
    # Refresh Users
    # =====================================================

    def refresh_users(self):

        response = self.client.send_request(
            "LIST"
        )

        if not response:
            return

        print(
            "[GUI] LIST Response:",
            response
        )

        parts = response.split(
            " ",
            3
        )

        if (
            len(parts) >= 3
            and parts[0] == "200"
            and parts[1] == "OK"
        ):

            self.user_list.delete(
                0,
                tk.END
            )

            if len(parts) == 4:

                usernames = parts[3].split(",")

                for username in usernames:

                    username = username.strip()

                    if username:

                        self.user_list.insert(
                            tk.END,
                            username
                        )

    # =====================================================
    # Send Message
    # =====================================================

    def send_message(self):

        message = (
            self.message_entry
            .get()
            .strip()
        )

        if not message:
            return

        selected = (
            self.user_list
            .curselection()
        )

        if not selected:

            messagebox.showwarning(
                "Send Message",
                "กรุณาเลือกผู้รับก่อน"
            )

            return

        receiver = (
            self.user_list
            .get(
                selected[0]
            )
        )

        if receiver == self.client.username:

            messagebox.showwarning(
                "Send Message",
                "ไม่สามารถส่งข้อความให้ตัวเองได้"
            )

            return

        # ================================================
        # NCP Request
        # ================================================

        request = (
            f"SEND {receiver} {message}"
        )

        response = (
            self.client
            .send_request(request)
        )

        if not response:

            messagebox.showerror(
                "Send Failed",
                "ไม่ได้รับ Response จาก Server"
            )

            return

        # ================================================
        # ต้องเป็น MESSAGE_SENT เท่านั้น
        # ================================================

        if response.startswith(
            "200 OK MESSAGE_SENT"
        ):

            parts = response.split()

            # 200 OK MESSAGE_SENT MSG-0001

            if len(parts) >= 4:

                message_id = parts[3]

            else:

                message_id = "UNKNOWN"

            self.add_chat_message(
                f"You → {receiver}: "
                f"{message} "
                f"[{message_id}]"
            )

            self.message_entry.delete(
                0,
                tk.END
            )

        else:

            messagebox.showerror(
                "Send Failed",
                response
            )

    # =====================================================
    # Close
    # =====================================================

    def on_close(self):

        try:

            if self.client.running:

                self.client.send_request(
                    "QUIT"
                )

        except:
            pass

        self.client.close()

        self.root.destroy()


# =========================================================
# Login Window
# =========================================================

class LoginWindow:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "AppChat - Login"
        )

        self.root.geometry(
            "400x250"
        )

        self.root.resizable(
            False,
            False
        )

        self.client = ChatClient()

        # =================================================
        # Title
        # =================================================

        tk.Label(
            root,
            text="AppChat",
            font=("Arial", 24, "bold")
        ).pack(
            pady=(30, 5)
        )

        tk.Label(
            root,
            text="NCP Chat Application"
        ).pack()

        # =================================================
        # Username
        # =================================================

        username_frame = tk.Frame(
            root
        )

        username_frame.pack(
            pady=20
        )

        tk.Label(
            username_frame,
            text="Username:"
        ).pack(
            side=tk.LEFT,
            padx=5
        )

        self.username_entry = tk.Entry(
            username_frame,
            width=25
        )

        self.username_entry.pack(
            side=tk.LEFT
        )

        # =================================================
        # Login Button
        # =================================================

        self.login_button = tk.Button(
            root,
            text="LOGIN",
            width=15,
            command=self.login
        )

        self.login_button.pack()

        self.username_entry.bind(
            "<Return>",
            lambda event: self.login()
        )

    def login(self):

        username = (
            self.username_entry
            .get()
            .strip()
        )

        if not username:

            messagebox.showwarning(
                "Login",
                "กรุณาใส่ Username"
            )

            return

        self.login_button.config(
            state=tk.DISABLED
        )

        success = self.client.login(
            username
        )

        if success:

            self.open_chat()

        else:

            messagebox.showerror(
                "Login Failed",
                "Login ไม่สำเร็จ"
            )

            self.login_button.config(
                state=tk.NORMAL
            )

    def open_chat(self):

        for widget in self.root.winfo_children():

            widget.destroy()

        ChatWindow(
            self.root,
            self.client
        )


# =========================================================
# Main
# =========================================================

def main():

    root = tk.Tk()

    LoginWindow(
        root
    )

    root.mainloop()


if __name__ == "__main__":

    main()