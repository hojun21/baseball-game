import os
import tkinter as tk

from PIL import Image, ImageOps, ImageTk

TRANSPARENT_KEY = "#ff00ff"  # 이 색만 투명 처리됨
WIN_W, WIN_H = 260, 130
GROUND_Y = WIN_H - 15
SPRITE_H = 70  # 세로 기준으로 리사이즈, 가로는 비율 유지 (졸라맨 사이즈)
BATTER_X = 60
PITCHER_X = WIN_W - 60
BATTER_FRAME_SEC = 0.02  # 타자 프레임 전환 간격(초) - 전체 프레임 동일 간격
PITCHER_SPLIT = 5  # 이 개수까지는 SEC_1, 이후는 SEC_2 간격 적용
PITCHER_FRAME_SEC_1 = 0.2  # 1~5번째 프레임 간격(초)
PITCHER_FRAME_SEC_2 = 0.1  # 6번째 이후 프레임 간격(초)

IMG_DIR = os.path.join(os.path.dirname(__file__), "img")

BATTER_NUMS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 21, 22, 29, 30]
BATTER_FILES = [f"타자{i}.png" for i in BATTER_NUMS]
PITCHER_FILES = [f"투수{i}.png" for i in range(1, 10)]


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
x = screen_w - WIN_W - 20
y = screen_h - WIN_H - 60
root.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")

canvas = tk.Canvas(root, width=WIN_W, height=WIN_H, bg=TRANSPARENT_KEY, highlightthickness=0)
canvas.pack()

batter_frames = load_frames("batter", BATTER_FILES, SPRITE_H)
pitcher_frames = load_frames("pitcher", PITCHER_FILES, SPRITE_H, flip=True)

batter_item = canvas.create_image(BATTER_X, GROUND_Y, image=batter_frames[0], anchor="s")
pitcher_item = canvas.create_image(PITCHER_X, GROUND_Y, image=pitcher_frames[0], anchor="s")


def animate_batter(i=0):
    # 미리보기: 계속 순환 재생. M4(스윙)에서 키 입력 트리거로 교체 예정.
    canvas.itemconfig(batter_item, image=batter_frames[i % len(batter_frames)])
    root.after(round(BATTER_FRAME_SEC * 1000), animate_batter, i + 1)


def animate_pitcher(i=0):
    # 미리보기: 계속 순환 재생. M3(투구)에서 키 입력 트리거로 교체 예정.
    idx = i % len(pitcher_frames)
    canvas.itemconfig(pitcher_item, image=pitcher_frames[idx])
    sec = PITCHER_FRAME_SEC_1 if idx < PITCHER_SPLIT else PITCHER_FRAME_SEC_2
    root.after(round(sec * 1000), animate_pitcher, i + 1)


animate_batter()
animate_pitcher()

root.bind("<Escape>", lambda e: root.destroy())  # 테두리 없어서 Esc로 종료
root.mainloop()
