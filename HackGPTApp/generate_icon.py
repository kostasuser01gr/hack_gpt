#!/usr/bin/env python3
"""Generate HackGPT app icon as .icns for macOS"""

import os


def create_icon_png(size):
    """Create a HackGPT icon at given size using raw PNG generation."""
    # We'll create the icon pixel by pixel
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size / 2, size / 2
    size * 0.44  # main radius

    # Background: rounded square with gradient-like dark fill
    margin = size * 0.06
    corner = size * 0.22
    # Dark navy/black background
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=corner,
        fill=(15, 15, 30, 255),
    )

    # Outer glow ring (red/crimson)
    ring_width = max(2, size // 40)
    for i in range(ring_width * 2):
        alpha = int(255 * (1 - i / (ring_width * 2)) * 0.4)
        offset = margin + i * 0.5
        c = corner - i * 0.3
        if c < 0:
            c = 0
        draw.rounded_rectangle(
            [offset, offset, size - offset, size - offset],
            radius=c,
            outline=(220, 40, 40, alpha),
            width=1,
        )

    # Inner glow border
    inner_margin = margin + ring_width
    draw.rounded_rectangle(
        [inner_margin, inner_margin, size - inner_margin, size - inner_margin],
        radius=corner * 0.85,
        outline=(200, 30, 30, 200),
        width=max(1, size // 80),
    )

    # Shield shape in center
    shield_w = size * 0.38
    shield_h = size * 0.44
    cx - shield_w / 2
    sy = cy - shield_h * 0.42

    # Shield outline points
    shield_points = [
        (cx, sy),  # top center
        (cx + shield_w * 0.5, sy + shield_h * 0.15),  # top right
        (cx + shield_w * 0.5, sy + shield_h * 0.55),  # mid right
        (cx, sy + shield_h),  # bottom center (point)
        (cx - shield_w * 0.5, sy + shield_h * 0.55),  # mid left
        (cx - shield_w * 0.5, sy + shield_h * 0.15),  # top left
    ]

    # Shield fill (dark with slight transparency)
    draw.polygon(shield_points, fill=(30, 30, 50, 220), outline=(220, 50, 50, 255))

    # Draw a terminal cursor ">" inside shield
    cursor_size = size * 0.10
    cursor_x = cx - cursor_size * 0.8
    cursor_y = cy - cursor_size * 0.2

    lw = max(2, size // 60)
    # ">" chevron
    draw.line(
        [
            (cursor_x, cursor_y - cursor_size * 0.5),
            (cursor_x + cursor_size * 0.7, cursor_y),
            (cursor_x, cursor_y + cursor_size * 0.5),
        ],
        fill=(0, 255, 100, 255),
        width=lw,
    )
    # "_" underscore
    draw.line(
        [
            (cursor_x + cursor_size * 0.9, cursor_y + cursor_size * 0.5),
            (cursor_x + cursor_size * 1.6, cursor_y + cursor_size * 0.5),
        ],
        fill=(0, 255, 100, 200),
        width=lw,
    )

    # "H" letterform at top of shield
    try:
        # Try to use a system font
        font_size = int(size * 0.12)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/SFMono-Bold.otf", font_size)
        except Exception:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", font_size)
            except Exception:
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
                except Exception:
                    font = ImageFont.load_default()

        # Draw "H" at top
        text = "H"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = cx - tw / 2
        ty = sy + shield_h * 0.08
        draw.text((tx, ty), text, fill=(255, 60, 60, 255), font=font)
    except Exception:
        pass

    # Small "GPT" text below
    try:
        small_size = int(size * 0.06)
        try:
            small_font = ImageFont.truetype("/System/Library/Fonts/SFMono-Bold.otf", small_size)
        except Exception:
            try:
                small_font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", small_size)
            except Exception:
                small_font = ImageFont.load_default()

        gpt_text = "GPT"
        bbox2 = draw.textbbox((0, 0), gpt_text, font=small_font)
        tw2 = bbox2[2] - bbox2[0]
        draw.text(
            (cx - tw2 / 2, ty + th + size * 0.01),
            gpt_text,
            fill=(200, 200, 200, 220),
            font=small_font,
        )
    except Exception:
        pass

    # Circuit/scan lines decoration (subtle)
    line_color = (0, 200, 100, 40)
    for i in range(3):
        y_line = margin + size * 0.15 + i * size * 0.28
        draw.line(
            [(margin + size * 0.08, y_line), (size - margin - size * 0.08, y_line)],
            fill=line_color,
            width=1,
        )

    return img


def main():
    out_dir = "/Users/user/HackGPT/HackGPTApp"
    iconset_dir = os.path.join(out_dir, "HackGPT.iconset")
    os.makedirs(iconset_dir, exist_ok=True)

    # Required sizes for macOS .icns
    sizes = [
        (16, "icon_16x16.png"),
        (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"),
        (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"),
        (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"),
        (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"),
        (1024, "icon_512x512@2x.png"),
    ]

    for size, filename in sizes:
        print(f"  Generating {filename} ({size}x{size})...")
        img = create_icon_png(size)
        img.save(os.path.join(iconset_dir, filename), "PNG")

    print("  All PNGs generated. Converting to .icns...")

    icns_path = os.path.join(out_dir, "HackGPT.app", "Contents", "Resources", "AppIcon.icns")
    os.makedirs(os.path.dirname(icns_path), exist_ok=True)

    ret = os.system(f"iconutil -c icns -o '{icns_path}' '{iconset_dir}'")
    if ret == 0:
        print(f"  ✅ Icon created: {icns_path}")
    else:
        print(f"  ❌ iconutil failed with code {ret}")
        return 1

    # Cleanup iconset
    import shutil

    shutil.rmtree(iconset_dir)
    print("  Cleaned up iconset directory")
    return 0


if __name__ == "__main__":
    exit(main())
