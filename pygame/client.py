# client.py
import pygame
import socket
import json
import threading
import sys

HOST = "127.0.0.1"
PORT = 5555

pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("🎉 你画我猜 - 客户端")

FONT = pygame.font.SysFont("simhei", 20)
BIG_FONT = pygame.font.SysFont("simhei", 36)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 50, 50)
GREEN = (50, 255, 50)
BLUE = (50, 150, 255)
GRAY = (200, 200, 200)
PINK = (255, 200, 200)

# 绘画区域
CANVAS_LEFT, CANVAS_TOP = 100, 100
CANVAS_WIDTH, CANVAS_HEIGHT = 500, 300
canvas_surface = pygame.Surface((CANVAS_WIDTH, CANVAS_HEIGHT))
canvas_surface.fill(WHITE)

# UI 状态
name = ""
connected = False
client_socket = None
is_drawing = False
current_round = 0
current_word_len = 0
drawer_name = ""
guessed_correctly = False
guess_input = ""
players = []

# 画笔设置
brush_size = 5
brush_color = BLACK
last_pos = None

def send_message(msg_type, data=None):
    if not connected:
        return
    try:
        msg = json.dumps({"type": msg_type, "data": data})
        client_socket.send(msg.encode("utf-8"))
    except Exception as e:
        print("📤 发送失败:", e)

def draw_canvas():
    screen.fill(GRAY)
    # 标题
    title = BIG_FONT.render("🎨 你画我猜", True, BLUE)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 20))

    # 画布
    pygame.draw.rect(screen, WHITE, (CANVAS_LEFT, CANVAS_TOP, CANVAS_WIDTH, CANVAS_HEIGHT), border_radius=8)
    pygame.draw.rect(screen, BLACK, (CANVAS_LEFT, CANVAS_TOP, CANVAS_WIDTH, CANVAS_HEIGHT), 2, border_radius=8)
    screen.blit(canvas_surface, (CANVAS_LEFT, CANVAS_TOP))

    # 状态栏
    status = f"第 {current_round} 轮 | 画手: {drawer_name} | 词长: {current_word_len} 字"
    if is_drawing:
        status += " (你正在画!)"
    status_text = FONT.render(status, True, BLACK)
    screen.blit(status_text, (20, 20))

    # 玩家列表
    y = 60
    for p in players:
        color = GREEN if p["is_drawing"] else BLACK
        text = FONT.render(p["name"], True, color)
        screen.blit(text, (20, y))
        y += 25

    # 输入框
    input_box = pygame.Rect(20, HEIGHT - 80, 300, 40)
    pygame.draw.rect(screen, WHITE, input_box, border_radius=5)
    pygame.draw.rect(screen, BLACK, input_box, 2, border_radius=5)
    input_text = FONT.render(guess_input if guess_input else "输入你的猜测...", True, BLACK)
    screen.blit(input_text, (25, HEIGHT - 72))

    # 按钮
    clear_btn = pygame.Rect(WIDTH - 120, HEIGHT - 80, 100, 40)
    pygame.draw.rect(screen, PINK, clear_btn, border_radius=5)
    pygame.draw.rect(screen, BLACK, clear_btn, 2, border_radius=5)
    clear_text = FONT.render("清空画布", True, BLACK)
    screen.blit(clear_text, (WIDTH - 110, HEIGHT - 72))

    # 提示
    if guessed_correctly:
        hint = FONT.render("✅ 正确！下一轮即将开始...", True, GREEN)
        screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT - 130))

    pygame.display.flip()

def receive_loop():
    global is_drawing, current_round, current_word_len, drawer_name, guessed_correctly, players, guess_input
    while connected:
        try:
            data = client_socket.recv(4096)
            if not data:
                break
            msg = json.loads(data.decode("utf-8"))
            msg_type = msg["type"]
            payload = msg["data"]

            if msg_type == "welcome":
                players = payload["players"]
                current_round = payload["round"]
                is_drawing = payload["is_drawing"]
                current_word_len = payload["word_len"]
                drawer_name = next((p["name"] for p in players if p["is_drawing"]), "")

            elif msg_type == "update_players":
                players = payload

            elif msg_type == "new_round":
                current_round = payload["round"]
                is_drawing = payload["is_drawing"]
                current_word_len = payload["word_len"]
                drawer_name = payload["drawer"]
                guessed_correctly = False
                canvas_surface.fill(WHITE)

            elif msg_type == "draw":
                x, y = payload["pos"]
                size = payload["size"]
                color = tuple(payload["color"])
                pygame.draw.circle(canvas_surface, color, (x, y), size)

            elif msg_type == "clear":
                canvas_surface.fill(WHITE)

            elif msg_type == "correct_guess":
                guessed_correctly = True
                guesser = payload["guesser"]
                print(f"🏆 {guesser} 猜对了！")
                # 可选：播放音效 / 弹窗提醒（这里仅打印）

            elif msg_type == "wrong_guess":
                guesser = payload["guesser"]
                guess = payload["guess"]
                print(f"❌ {guesser} 猜了 '{guess}'，不对")

        except Exception as e:
            print("📥 接收错误:", e)
            break

def main():
    global name, connected, client_socket, guess_input

    # 输入用户名
    clock = pygame.time.Clock()
    name_input = ""
    input_active = True
    while input_active:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    name = name_input.strip()
                    if name:
                        input_active = False
                elif event.key == pygame.K_BACKSPACE:
                    name_input = name_input[:-1]
                else:
                    name_input += event.unicode
        screen.fill(GRAY)
        prompt = FONT.render("请输入你的名字（回车确认）:", True, BLACK)
        screen.blit(prompt, (WIDTH//2 - prompt.get_width()//2, HEIGHT//2 - 40))
        name_disp = FONT.render(name_input, True, BLACK)
        screen.blit(name_disp, (WIDTH//2 - name_disp.get_width()//2, HEIGHT//2))
        pygame.display.flip()
        clock.tick(30)

    # 连接服务器
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((HOST, PORT))
        client_socket.send(name.encode("utf-8"))
        connected = True
        threading.Thread(target=receive_loop, daemon=True).start()
    except Exception as e:
        print("🔌 连接服务器失败:", e)
        pygame.quit()
        return
    clock = pygame.time.Clock()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if is_drawing:
                    x, y = event.pos
                    # 映射到画布坐标系
                    cx = x - CANVAS_LEFT
                    cy = y - CANVAS_TOP
                    if 0 <= cx < CANVAS_WIDTH and 0 <= cy < CANVAS_HEIGHT:
                        last_pos = (cx, cy)
                        pygame.draw.circle(canvas_surface, brush_color, (cx, cy), brush_size)
                        send_message("draw", {"pos": (cx, cy), "size": brush_size, "color": brush_color})
            if event.type == pygame.MOUSEMOTION and is_drawing:
                x, y = event.pos
                cx = x - CANVAS_LEFT
                cy = y - CANVAS_TOP
                if 0 <= cx < CANVAS_WIDTH and 0 <= cy < CANVAS_HEIGHT and last_pos:
                    pygame.draw.line(canvas_surface, brush_color, last_pos, (cx, cy), brush_size * 2)
                    send_message("draw", {"pos": (cx, cy), "size": brush_size, "color": brush_color})
                    last_pos = (cx, cy)
            if event.type == pygame.MOUSEBUTTONUP:
                last_pos = None

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if guess_input.strip():
                        send_message("guess", guess_input.strip())
                        guess_input = ""
                elif event.key == pygame.K_BACKSPACE:
                    guess_input = guess_input[:-1]
                elif len(guess_input) < 30:
                    guess_input += event.unicode

                if event.key == pygame.K_r and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    # Ctrl+R 清空画布（仅自己本地，但也要通知其他玩家）
                    canvas_surface.fill(WHITE)
                    send_message("clear")

        draw_canvas()
        clock.tick(60)

    client_socket.close()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()