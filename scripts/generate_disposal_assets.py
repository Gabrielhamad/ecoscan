from __future__ import annotations

import json
from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "disposal_targets.json"
IMAGE_SIZE = (960, 640)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def _blend(left: tuple[int, int, int], right: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
    return tuple(round(left[index] * (1 - ratio) + right[index] * ratio) for index in range(3))


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _draw_background(draw: ImageDraw.ImageDraw, accent: tuple[int, int, int]) -> None:
    width, height = IMAGE_SIZE
    top = _blend((245, 248, 246), accent, 0.08)
    bottom = _blend((228, 236, 231), accent, 0.16)
    for y in range(height):
        ratio = y / max(1, height - 1)
        draw.line([(0, y), (width, y)], fill=_blend(top, bottom, ratio))

    draw.rounded_rectangle((52, 54, width - 52, height - 54), radius=26, fill=(255, 255, 255))
    draw.rectangle((52, height - 190, width - 52, height - 54), fill=(236, 241, 237))
    draw.rounded_rectangle((52, 54, width - 52, height - 54), radius=26, outline=(205, 217, 209), width=2)


def _draw_bin(draw: ImageDraw.ImageDraw, accent: tuple[int, int, int]) -> None:
    ox = 240
    dark = _blend(accent, (10, 18, 14), 0.24)
    light = _blend(accent, (255, 255, 255), 0.22)
    shadow = _blend(accent, (0, 0, 0), 0.65)

    draw.ellipse((245 + ox, 480, 660 + ox, 548), fill=(35, 45, 39, 34))
    draw.rounded_rectangle((310 + ox, 190, 600 + ox, 506), radius=28, fill=accent, outline=dark, width=5)
    draw.rounded_rectangle((286 + ox, 154, 624 + ox, 205), radius=18, fill=dark)
    draw.rounded_rectangle((340 + ox, 116, 570 + ox, 160), radius=16, fill=light, outline=dark, width=4)
    draw.rounded_rectangle((350 + ox, 225, 560 + ox, 430), radius=18, fill=_blend(accent, (255, 255, 255), 0.12))
    draw.line((388 + ox, 248, 388 + ox, 410), fill=light, width=5)
    draw.line((472 + ox, 248, 472 + ox, 410), fill=light, width=5)
    draw.ellipse((332 + ox, 488, 384 + ox, 540), fill=shadow)
    draw.ellipse((526 + ox, 488, 578 + ox, 540), fill=shadow)
    draw.rounded_rectangle((394 + ox, 454, 516 + ox, 484), radius=14, fill=dark)


def _draw_dropoff(draw: ImageDraw.ImageDraw, accent: tuple[int, int, int]) -> None:
    ox = 240
    dark = _blend(accent, (8, 18, 14), 0.36)
    light = _blend(accent, (255, 255, 255), 0.24)
    panel = (246, 248, 247) if sum(accent) > 650 else _blend(accent, (255, 255, 255), 0.18)

    draw.ellipse((225 + ox, 480, 682 + ox, 550), fill=(35, 45, 39, 34))
    draw.rounded_rectangle((296 + ox, 150, 606 + ox, 508), radius=24, fill=accent, outline=dark, width=5)
    draw.rounded_rectangle((332 + ox, 192, 570 + ox, 284), radius=16, fill=panel, outline=dark, width=4)
    draw.rounded_rectangle((360 + ox, 334, 542 + ox, 376), radius=19, fill=dark)
    draw.rounded_rectangle((356 + ox, 414, 546 + ox, 468), radius=16, fill=light, outline=dark, width=4)
    draw.line((378 + ox, 442, 524 + ox, 442), fill=dark, width=5)
    draw.arc((396 + ox, 210, 506 + ox, 320), 25, 160, fill=dark, width=7)
    draw.polygon([(394 + ox, 214), (421 + ox, 204), (417 + ox, 232)], fill=dark)
    draw.arc((396 + ox, 210, 506 + ox, 320), 205, 340, fill=dark, width=7)
    draw.polygon([(508 + ox, 318), (480 + ox, 326), (486 + ox, 298)], fill=dark)


def _draw_text(
    draw: ImageDraw.ImageDraw,
    title: str,
    subtitle: str,
    color_name: str,
    accent: tuple[int, int, int],
) -> None:
    title_font = _font(44, bold=True)
    body_font = _font(28)
    tag_font = _font(24, bold=True)

    ink = (24, 35, 29)
    muted = (83, 100, 91)
    badge_fill = _blend(accent, (255, 255, 255), 0.82)
    badge_line = _blend(accent, (10, 18, 14), 0.18)

    y = 78
    draw.text((88, y), title, fill=ink, font=title_font)
    y += 58
    for line in wrap(subtitle, width=26)[:3]:
        draw.text((88, y), line, fill=muted, font=body_font)
        y += 36

    tag = f"Cor de referência: {color_name}"
    tag_bbox = draw.textbbox((0, 0), tag, font=tag_font)
    tag_width = tag_bbox[2] - tag_bbox[0]
    badge_right = min(520, 154 + tag_width + 26)
    draw.rounded_rectangle((88, 506, badge_right, 562), radius=18, fill=badge_fill, outline=badge_line, width=2)
    draw.ellipse((112, 523, 142, 553), fill=accent, outline=badge_line, width=2)
    draw.text((154, 519), tag, fill=ink, font=tag_font)


def generate_assets() -> list[Path]:
    targets = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    written: list[Path] = []
    for target in targets.values():
        accent = _hex_to_rgb(target["bin_color_hex"])
        image = Image.new("RGB", IMAGE_SIZE, (245, 248, 246))
        draw = ImageDraw.Draw(image, "RGBA")
        _draw_background(draw, accent)
        if target["destination_title"].lower().startswith("lixeira"):
            _draw_bin(draw, accent)
        else:
            _draw_dropoff(draw, accent)
        _draw_text(
            draw,
            target["destination_title"],
            target["destination_type"],
            target["bin_color_name"],
            accent,
        )

        output_path = PROJECT_ROOT / target["asset_path"]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path)
        written.append(output_path)
    return written


def main() -> None:
    for path in generate_assets():
        print(path)


if __name__ == "__main__":
    main()
