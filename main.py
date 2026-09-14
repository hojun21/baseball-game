import os
import tkinter as tk

from PIL import Image, ImageTk

TRANSPARENT_KEY = "#ff00ff"  # 이 색만 투명 처리됨
WIN_W, WIN_H = 260, 130
GROUND_Y = WIN_H - 15
SPRITE_H = 70  # 세로 기준으로 리사이즈, 가로는 비율 유지 (졸라맨 사이즈)
BATTER_X = 60
PITCHER_X = WIN_W - 60
ANIM_MS = 120  # 프레임 전환 간격(ms) - ponytail: 지금은 미리보기용 자동 재생, M3/M4에서 키 입력 트리거로 교체

IMG_DIR = os.path.join(os.path.dirname(__file__), "img")

# 파일명이 한글/번호가 뒤섞여 있어 정렬로는 순서 보장이 안 돼서 순서를 직접 명시
BATTER_FILES = [
    "타격준비1.png",
    "타격2 공딱침.png",
    "타격3 공친직후.png",
    "타격후 마무리 먼산보기 4.png",
]
PITCHER_FILES = [f"투수{i}.png" for i in range(1, 6)]


def load_frames(folder, filenames, height):
    frames = []
    for name in filenames:
        img = Image.open(os.path.join(IMG_DIR, folder, name)).convert("RGBA")
        w, h = img.size
        new_w = int(w * height / h)
        frames.append(ImageTk.PhotoImage(img.resize((new_w, height), Image.LANCZOS)))
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
pitcher_frames = load_frames("pitcher", PITCHER_FILES, SPRITE_H)

batter_item = canvas.create_image(BATTER_X, GROUND_Y, image=batter_frames[0], anchor="s")
pitcher_item = canvas.create_image(PITCHER_X, GROUND_Y, image=pitcher_frames[0], anchor="s")


def preview_animate(i=0):
    # 미리보기: 두 캐릭터 프레임을 계속 순환 재생. M3(투구)/M4(스윙)에서 키 입력에 맞춰
    # 이 프레임들을 트리거 방식으로 바꿔치기할 예정.
    canvas.itemconfig(batter_item, image=batter_frames[i % len(batter_frames)])
    canvas.itemconfig(pitcher_item, image=pitcher_frames[i % len(pitcher_frames)])
    root.after(ANIM_MS, preview_animate, i + 1)


preview_animate()

root.bind("<Escape>", lambda e: root.destroy())  # 테두리 없어서 Esc로 종료
root.mainloop()
