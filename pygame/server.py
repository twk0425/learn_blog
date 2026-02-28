# server.py
import socket
import threading
import json
import random
from collections import deque

HOST = "127.0.0.1"  # 可改为本机真实局域网IP（如 192.168.x.x）
PORT = 5555

class Server:
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((HOST, PORT))
        self.server_socket.listen(5)
        self.clients = {}  # {conn: {'name': str, 'is_drawing': bool}}
        self.word_list = []
        self.current_word = ""
        self.drawing_player = None
        self.round = 0
        self.guessed = False
        self.lock = threading.Lock()

        # 加载词库
        try:
            with open("words.txt", "r", encoding="utf-8") as f:
                self.word_list = [line.strip().lower() for line in f if line.strip()]
        except FileNotFoundError:
            print("⚠️ 未找到 words.txt，使用默认词库")
            self.word_list = ["apple", "banana", "cat", "dog", "elephant"]

        print(f"✅ 服务器启动于 {HOST}:{PORT}")
        print("💡 提示：客户端连接后输入名字，即可加入游戏")

    def broadcast(self, msg_type, data, exclude=None):
        """广播消息给所有客户端（可排除某人）"""
        with self.lock:
            for conn in list(self.clients.keys()):
                if conn == exclude:
                    continue
                try:
                    msg = json.dumps({"type": msg_type, "data": data})
                    conn.send(msg.encode("utf-8"))
                except Exception:
                    self.remove_client(conn)

    def remove_client(self, conn):
        name = self.clients.get(conn, {}).get("name", "Unknown")
        print(f"❌ 客户端断开: {name}")
        if conn in self.clients:
            del self.clients[conn]
        if self.drawing_player == conn:
            self.drawing_player = None
            if self.clients:
                next_conn = next(iter(self.clients))
                self.start_new_round(next_conn)
            else:
                self.current_word = ""
                self.guessed = False
        self.broadcast("update_players", list(self.clients.values()))

    def handle_client(self, conn):
        try:
            # 接收用户名
            name_data = conn.recv(1024).decode("utf-8").strip()
            if not name_data:
                return
            name = name_data[:20]  # 限制长度
            self.clients[conn] = {"name": name, "is_drawing": False}
            print(f"✅ 新玩家加入: {name}")

            self.broadcast("update_players", list(self.clients.values()), exclude=conn)
            conn.send(json.dumps({
                "type": "welcome",
                "data": {
                    "players": list(self.clients.values()),
                    "round": self.round,
                    "is_drawing": conn == self.drawing_player,
                    "word_len": len(self.current_word) if self.current_word else 0
                }
            }).encode("utf-8"))

            if not self.drawing_player and len(self.clients) >= 2:
                # 自动开始第一轮
                first_conn = next(iter(self.clients))
                self.start_new_round(first_conn)

            while True:
                data = conn.recv(4096)
                if not data:
                    break
                try:
                    msg = json.loads(data.decode("utf-8"))
                    msg_type = msg.get("type")
                    payload = msg.get("data")

                    if msg_type == "guess":
                        guess = payload.lower().strip()
                        if self.guessed:
                            continue
                        if guess == self.current_word:
                            self.guessed = True
                            self.broadcast("correct_guess", {"guesser": self.clients[conn]["name"]})
                            # 1秒后自动开始新轮
                            threading.Timer(1.0, self.start_new_round, args=[self.next_draw_player()]).start()
                        else:
                            self.broadcast("wrong_guess", {"guesser": self.clients[conn]["name"], "guess": guess})

                    elif msg_type == "draw":
                        # 转发画笔事件（只发给非画手）
                        self.broadcast("draw", payload, exclude=conn)

                    elif msg_type == "clear":
                        self.broadcast("clear", None, exclude=conn)

                except Exception as e:
                    print("❌ 解析消息出错:", e)
                    break
        except Exception as e:
            print("❌ 客户端处理异常:", e)
        finally:
            self.remove_client(conn)

    def next_draw_player(self):
        """轮到下一位玩家作画（循环）"""
        if not self.clients:
            return None
        keys = list(self.clients.keys())
        if self.drawing_player in keys:
            idx = keys.index(self.drawing_player)
            return keys[(idx + 1) % len(keys)]
        return keys[0]

    def start_new_round(self, drawer_conn):
        """开始新一轮：选词 + 指定画手"""
        with self.lock:
            self.round += 1
            self.current_word = random.choice(self.word_list)
            self.drawing_player = drawer_conn
            self.guessed = False

            # 更新所有客户端状态
            for conn in self.clients:
                is_drawing = (conn == self.drawing_player)
                self.clients[conn]["is_drawing"] = is_drawing
                try:
                    conn.send(json.dumps({
                        "type": "new_round",
                        "data": {
                            "word_len": len(self.current_word),
                            "is_drawing": is_drawing,
                            "round": self.round,
                            "drawer": self.clients[drawer_conn]["name"]
                        }
                    }).encode("utf-8"))
                except:
                    pass

    def run(self):
        try:
            while True:
                conn, addr = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(conn,), daemon=True).start()
        except KeyboardInterrupt:
            print("\n🛑 服务器已关闭")
            self.server_socket.close()

if __name__ == "__main__":
    Server().run()