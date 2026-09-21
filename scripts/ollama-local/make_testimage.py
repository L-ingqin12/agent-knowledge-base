"""用纯标准库生成一张内容已知的 PNG，用于验证本地模型的多模态（视觉）能力。

图内容（便于核对）：
  - 左上：1 个红色圆形
  - 右上：1 个蓝色正方形
  - 底部：3 个绿色小方块（排成一行）
"""
import struct
import zlib

W, H = 400, 240


def blank():
    return [[(255, 255, 255) for _ in range(W)] for _ in range(H)]


def fill_circle(img, cx, cy, r, color):
    for y in range(max(0, cy - r), min(H, cy + r + 1)):
        for x in range(max(0, cx - r), min(W, cx + r + 1)):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                img[y][x] = color


def fill_rect(img, x0, y0, w, h, color):
    for y in range(max(0, y0), min(H, y0 + h)):
        for x in range(max(0, x0), min(W, x0 + w)):
            img[y][x] = color


def write_png(path, img):
    raw = b"".join(b"\x00" + b"".join(bytes(px) for px in row) for row in img)

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


img = blank()
fill_circle(img, 90, 80, 55, (220, 30, 30))       # 红圆
fill_rect(img, 250, 30, 100, 100, (30, 60, 220))  # 蓝方
for i in range(3):                                 # 3 个绿方块
    fill_rect(img, 60 + i * 80, 190, 45, 40, (20, 170, 60))

out = r"D:\OllamaModels\bench\vision_test.png"
write_png(out, img)
print("已生成:", out, "大小", len(open(out, "rb").read()), "字节")
print("内容：左上1个红圆 / 右上1个蓝方 / 底部3个绿块")
