import math
import os
import random
import time
import tkinter as tk
import winsound

from PIL import Image, ImageOps, ImageTk

TRANSPARENT_KEY = "#ff00ff"  # 이 색만 투명 처리됨
WIN_H = 130
GROUND_Y = WIN_H - 15
SPRITE_H = 70  # 세로 기준으로 리사이즈, 가로는 비율 유지 (졸라맨 사이즈)
CATCHER_SPRITE_H = 55  # 포수는 앉아 있으므로 더 낮게 (공 궤적 맞추려고 조금씩 조정 중)
BATTER_X = 90
CATCHER_X = 40  # 타자보다 왼쪽
BATTER_FRAME_SEC = 0.01  # 타자 프레임 전환 간격(초) - 전체 프레임 동일 간격
PITCHER_SPLIT = 5  # 이 개수까지는 SEC_1, 이후는 SEC_2 간격 적용
PITCHER_FRAME_SEC_1 = 0.2  # 1~5번째 프레임 간격(초)
PITCHER_FRAME_SEC_2 = 0.1  # 6번째 이후 프레임 간격(초)

BALL_RADIUS = 3
BALL_SPEED = 1000  # 투구 속도(px/sec) - 이 값만 바꾸면 됨
PITCHER_RELEASE_Y = GROUND_Y - round(SPRITE_H * 0.6)  # 투수 손 높이(근사)
CATCHER_GLOVE_Y = GROUND_Y - round(CATCHER_SPRITE_H * 0.6)  # 포수 글러브 높이(근사)

HIT_ZONE_X = BATTER_X  # 타이밍 맞으면 여기서 접촉
HIT_TOLERANCE = 15  # 접촉 판정 허용 범위(px)
HIT_PERFECT_TOLERANCE = 5  # 이 안으로 맞으면 완벽한 타이밍 -> 홈런
HIT_VX_RANGE = (220, 380)  # 타구 초기 수평 속도 범위(px/sec) - 매번 랜덤
HIT_VY_RANGE = (-350, -150)  # 타구 초기 수직 속도 범위(px/sec, 음수=위로) - 낮은 라인드라이브~높은 플라이
GRAVITY = 600  # 타구 낙하 가속도(px/sec^2)
HOMERUN_FLIGHT_TIME = 0.6  # 홈런일 때 오른쪽 위 구석까지 도달하는 시간(초) - 작을수록 더 강하게 꽂힘
BOUNCE_COUNT = 2  # 튕기는 횟수 (이후 굴러가다 멈춤)
BOUNCE_RESTITUTION = 0.45  # 튕길 때 수직 속도 유지율
BOUNCE_VX_DECAY = 0.75  # 튕길 때 수평 속도 유지율
ROLL_FRICTION = 500  # 굴러갈 때 수평 감속(px/sec^2)
HIT_LINGER_SEC = 1.0  # 멈춘 후 사라지기까지 대기 시간

IMG_DIR = os.path.join(os.path.dirname(__file__), "img")
# mp3는 MCI로 틀면 재생마다 디코더가 새로 버퍼를 채우느라 100ms+ 지연이 생겨서,
# wav로 한 번 변환해두고 winsound(표준 라이브러리, PCM이라 지연 없음)로 재생한다.
HIT_SOUND_PATH = os.path.join(os.path.dirname(__file__), "sound", "Baseball-hit-wooden-bat.wav")


def play_hit_sound():
    winsound.PlaySound(HIT_SOUND_PATH, winsound.SND_FILENAME | winsound.SND_ASYNC)

BATTER_NUMS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 21, 22, 29, 30]
BATTER_FILES = [f"타자{i}.png" for i in BATTER_NUMS]
PITCHER_FILES = [f"투수{i}.png" for i in range(1, 10)]
CATCHER_FILES = ["catcher1.png"]


def load_frames(folder, filenames, height, flip=False):
    frames = []
    for name in filenames:
        img = Image.open(os.path.join(IMG_DIR, folder, name)).convert("RGBA")
        if flip:
            img = ImageOps.mirror(img)
        w, h = img.size
        new_w = int(w * height / h)
        img = img.resize((new_w, height), Image.LANCZOS)
        # 리사이즈로 생긴 반투명 경계 픽셀 사이로 캔버스 배경(마젠타)이 비쳐서
        # 핑크 테두리가 보이므로, 알파를 완전 투명/불투명으로만 이진화
        r, g, b, a = img.split()
        a = a.point(lambda p: 255 if p >= 128 else 0)
        img = Image.merge("RGBA", (r, g, b, a))
        frames.append(ImageTk.PhotoImage(img))
    return frames


root = tk.Tk()
root.overrideredirect(True)  # 제목표시줄/테두리 제거
root.wm_attributes("-topmost", True)  # 항상 다른 창 위에
root.wm_attributes("-transparentcolor", TRANSPARENT_KEY)

screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()
WIN_W = screen_w
PITCHER_X = WIN_W // 2
x = 0
y = screen_h - WIN_H - 60
root.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")

canvas = tk.Canvas(root, width=WIN_W, height=WIN_H, bg=TRANSPARENT_KEY, highlightthickness=0)
canvas.pack()

batter_frames = load_frames("batter", BATTER_FILES, SPRITE_H)
pitcher_frames = load_frames("pitcher", PITCHER_FILES, SPRITE_H, flip=True)
catcher_frames = load_frames("catcher", CATCHER_FILES, CATCHER_SPRITE_H)

batter_item = canvas.create_image(BATTER_X, GROUND_Y, image=batter_frames[0], anchor="s")
pitcher_item = canvas.create_image(PITCHER_X, GROUND_Y, image=pitcher_frames[0], anchor="s")
catcher_item = canvas.create_image(CATCHER_X, GROUND_Y, image=catcher_frames[0], anchor="s")


HOLD_FRAME = 15  # 타자16.png - z를 누르고 있으면 여기서 대기

swinging = False  # 차징~스윙 전체 진행중 (재시작 방지)
key_held = False  # z가 물리적으로 눌려있는지
holding = False  # HOLD_FRAME에서 대기 중인지
pending_release = None  # OS 키 반복(auto-repeat)이 보내는 가짜 KeyRelease 무시용


def start_swing(event=None):
    # z를 누르면 HOLD_FRAME까지 재생 후 대기, 떼면 나머지 스윙 이어서 재생.
    global swinging, key_held, pending_release
    if pending_release is not None:
        root.after_cancel(pending_release)  # 방금 뗀 게 아니라 키 반복이었음
        pending_release = None
    key_held = True
    if swinging:
        return
    swinging = True
    swing_step(0)


def release_swing(event=None):
    # 키 반복으로 인한 가짜 release일 수 있으니 한 틱 미뤄서 진짜 release인지 확인.
    global pending_release
    pending_release = root.after(1, _do_release)


def _do_release():
    global key_held, holding, pending_release
    pending_release = None
    key_held = False
    if holding:
        holding = False
        begin_follow_through()


def swing_step(i):
    global swinging
    if i >= len(batter_frames):
        swinging = False
        canvas.itemconfig(batter_item, image=batter_frames[0])  # 대기 자세로 복귀
        return
    canvas.itemconfig(batter_item, image=batter_frames[i])
    if i == HOLD_FRAME:
        finish_hold_frame()
        return
    root.after(round(BATTER_FRAME_SEC * 1000), swing_step, i + 1)


def finish_hold_frame():
    # HOLD_FRAME 도달 시점: 아직 z를 누르고 있으면 대기, 이미 놓았으면(차징 중 조기 릴리즈) 바로 이어감.
    global holding
    if key_held:
        holding = True
        return  # _do_release가 begin_follow_through를 불러줌
    begin_follow_through()


def begin_follow_through():
    # z를 놓는 순간(=여기) 판정: 맞았으면 이 즉시 소리+타구, 헛스윙이면 소리 없이 스윙만 이어감.
    check_contact()
    swing_step(HOLD_FRAME + 1)


def check_contact():
    # 아주 정확히 맞으면(HIT_PERFECT_TOLERANCE) 화면 오른쪽 위 구석으로 홈런.
    global ball_item
    if ball_item is None or ball_x is None:
        return
    diff = abs(ball_x - HIT_ZONE_X)
    if diff <= HIT_TOLERANCE:
        hx, hy = ball_x, ball_y
        canvas.delete(ball_item)
        ball_item = None
        play_hit_sound()
        if diff <= HIT_PERFECT_TOLERANCE:
            t = HOMERUN_FLIGHT_TIME
            vx = (WIN_W - hx) / t
            vy = (0 - hy) / t - 0.5 * GRAVITY * t  # 중력 보정해서 (WIN_W, 0) 구석을 정확히 조준
        else:
            vx = random.uniform(*HIT_VX_RANGE)
            vy = random.uniform(*HIT_VY_RANGE)
        hit_ball(hx, hy, vx, vy)


PITCHER_RELEASE_FRAME = 7  # 투수8.png 시점에 공 릴리즈
PITCHER_FOLLOW_THROUGH_SEC = 1.0  # 투수9.png(마지막 프레임) 유지 시간

pitching = False


def start_pitch(event=None):
    # 스페이스바로 투구 시작. 대기 중(투수1.png)이 아니면 무시.
    global pitching
    if pitching:
        return
    pitching = True
    pitch_step(0)


def pitch_step(i):
    global pitching
    canvas.itemconfig(pitcher_item, image=pitcher_frames[i])
    if i == PITCHER_RELEASE_FRAME:
        throw_ball()
    if i + 1 >= len(pitcher_frames):
        root.after(round(PITCHER_FOLLOW_THROUGH_SEC * 1000), end_pitch)
        return
    sec = PITCHER_FRAME_SEC_1 if i < PITCHER_SPLIT else PITCHER_FRAME_SEC_2
    root.after(round(sec * 1000), pitch_step, i + 1)


def end_pitch():
    global pitching
    pitching = False
    canvas.itemconfig(pitcher_item, image=pitcher_frames[0])  # 대기 자세로 복귀


ball_item = None
ball_x = None
ball_y = None


def throw_ball():
    # 투수 손 -> 포수 글러브까지 직선 이동 후 사라짐. (타격 시 check_contact가 중간에 가로챔)
    global ball_item, ball_x, ball_y
    if ball_item is not None:
        return  # 이미 진행 중인 공이 있으면 무시
    start_x, start_y = PITCHER_X, PITCHER_RELEASE_Y
    end_x, end_y = CATCHER_X, CATCHER_GLOVE_Y
    duration = math.hypot(end_x - start_x, end_y - start_y) / BALL_SPEED
    ball_x, ball_y = start_x, start_y
    ball_item = canvas.create_oval(
        start_x - BALL_RADIUS, start_y - BALL_RADIUS,
        start_x + BALL_RADIUS, start_y + BALL_RADIUS,
        fill="black", outline="",
    )
    start_time = time.perf_counter()

    def step():
        global ball_item, ball_x, ball_y
        if ball_item is None:
            return  # 타격당해서 사라짐
        t = (time.perf_counter() - start_time) / duration
        if t >= 1:
            canvas.delete(ball_item)
            ball_item = None
            ball_x = ball_y = None
            return
        ball_x = start_x + (end_x - start_x) * t
        ball_y = start_y + (end_y - start_y) * t
        canvas.coords(ball_item, ball_x - BALL_RADIUS, ball_y - BALL_RADIUS, ball_x + BALL_RADIUS, ball_y + BALL_RADIUS)
        root.after(16, step)

    step()


hit_item = None


def hit_ball(start_x, start_y, vx0, vy0):
    # 접촉 지점에서 포물선으로 날아가다 1~2번 튕기고, 굴러가다 멈추면 잠시 후 사라짐.
    # (홈런이면 착지 전에 화면 오른쪽 위 구석 밖으로 나가서 사라짐)
    global hit_item
    if hit_item is not None:
        canvas.delete(hit_item)
    x, y = start_x, start_y
    vx, vy = vx0, vy0
    bounces_left = BOUNCE_COUNT
    rolling = False
    hit_item = canvas.create_oval(
        x - BALL_RADIUS, y - BALL_RADIUS, x + BALL_RADIUS, y + BALL_RADIUS,
        fill="black", outline="",
    )
    last_time = time.perf_counter()

    def step():
        nonlocal x, y, vx, vy, last_time, bounces_left, rolling
        global hit_item
        now = time.perf_counter()
        dt = now - last_time
        last_time = now

        if rolling:
            vx = max(0.0, vx - ROLL_FRICTION * dt)
            x += vx * dt
            canvas.coords(hit_item, x - BALL_RADIUS, y - BALL_RADIUS, x + BALL_RADIUS, y + BALL_RADIUS)
            if vx <= 0:
                root.after(round(HIT_LINGER_SEC * 1000), remove_hit_ball)
                return
            root.after(16, step)
            return

        vy += GRAVITY * dt
        x += vx * dt
        y += vy * dt
        if x >= WIN_W:
            canvas.delete(hit_item)  # 화면 오른쪽 밖으로 나감 - 홈런
            hit_item = None
            return
        if y >= GROUND_Y:
            y = GROUND_Y
            if bounces_left > 0:
                bounces_left -= 1
                vy = -vy * BOUNCE_RESTITUTION
                vx *= BOUNCE_VX_DECAY
            else:
                rolling = True
                vy = 0
        canvas.coords(hit_item, x - BALL_RADIUS, y - BALL_RADIUS, x + BALL_RADIUS, y + BALL_RADIUS)
        root.after(16, step)

    step()


def remove_hit_ball():
    global hit_item
    if hit_item is not None:
        canvas.delete(hit_item)
        hit_item = None


root.bind("<Escape>", lambda e: root.destroy())  # 테두리 없어서 Esc로 종료
root.bind("q", lambda e: root.destroy())  # 종료 버튼
root.bind("<space>", start_pitch)
root.bind("<KeyPress-z>", start_swing)
root.bind("<KeyRelease-z>", release_swing)
root.mainloop()
