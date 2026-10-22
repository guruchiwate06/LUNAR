"""
prepare_sprites.py - Extract, clean, and standardize desktop pet sprites from sprite_sheet.png.
"""
import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import rembg
import cv2

SPRITE_OUTPUT_DIR = "sprites"
CANVAS_SIZE = (512, 512)

# Precise crop boxes in sprite_sheet.png (1024 x 682)
# Text labels start at y=181 (Row 1) and y=357 (Row 2).
# Row 1 characters are contained within y: 0..177
# Row 2 characters are contained within y: 202..355
SPRITE_DEFS = [
    # (name, (left, top, right, bottom))
    ("idle", (20, 0, 260, 177)),
    ("blink", (265, 0, 505, 177)),
    ("happy", (510, 0, 750, 177)),
    ("float_up", (755, 0, 995, 177)),
    ("float_down", (20, 202, 260, 355)),
    ("sleep", (265, 202, 505, 355)),
    ("look", (510, 202, 750, 355)),
    ("turn", (755, 202, 995, 355)),
]


def remove_floating_artifacts(rgba_img: Image.Image, name: str) -> Image.Image:
    """
    Remove floating sparkles, stars, motion lines, '?', and 'Z z z'
    that are not part of the character body.
    Keeps the main character body and any contiguous body elements.
    """
    arr = np.array(rgba_img)
    alpha = arr[:, :, 3]

    # Binary mask for significant alpha
    bin_mask = (alpha > 25).astype(np.uint8)

    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(bin_mask, connectivity=8)
    if num_labels <= 1:
        return rgba_img

    # stats columns: [LEFT, TOP, WIDTH, HEIGHT, AREA]
    areas = stats[1:, cv2.CC_STAT_AREA]  # skip background (label 0)
    largest_label = np.argmax(areas) + 1
    max_area = stats[largest_label, cv2.CC_STAT_AREA]

    # Mask of components to keep
    keep_mask = np.zeros_like(bin_mask, dtype=bool)
    # Always keep the largest component (the main character body)
    keep_mask[labels == largest_label] = True

    # Check other components: only keep if substantial (> 12% of body) AND near center
    # This filters out floating symbols (?, zzz, stars, sparkles, motion curves)
    h, w = bin_mask.shape
    center_y, center_x = h / 2.0, w / 2.0

    filtered_artifacts = 0
    for label_idx in range(1, num_labels):
        if label_idx == largest_label:
            continue
        comp_area = stats[label_idx, cv2.CC_STAT_AREA]
        cx, cy = centroids[label_idx]

        # Floating sparkles and symbols are small (< 2000 px) or far from center
        # Only keep if it is substantial and close to the body
        is_significant = (comp_area > max_area * 0.12)
        dist_to_center = np.hypot(cx - center_x, cy - center_y)

        if is_significant and dist_to_center < max(w, h) * 0.45:
            keep_mask[labels == label_idx] = True
        else:
            filtered_artifacts += 1

    # Zero out alpha for any pixel belonging to filtered components
    cleaned_alpha = np.where(keep_mask, alpha, 0).astype(np.uint8)
    arr[:, :, 3] = cleaned_alpha

    print(f"[{name}] Filtered {filtered_artifacts} floating artifact(s), retained body area: {max_area} px")
    return Image.fromarray(arr, "RGBA")


def process_sprites(sheet_path="sprite_sheet.png"):
    if not os.path.exists(sheet_path):
        print(f"Error: {sheet_path} not found.")
        sys.exit(1)

    os.makedirs(SPRITE_OUTPUT_DIR, exist_ok=True)
    full_sheet = Image.open(sheet_path).convert("RGBA")
    print(f"Loaded sprite sheet: {sheet_path} ({full_sheet.size[0]}x{full_sheet.size[1]})")

    # Reuse single ONNX session for high-speed inference across all 8 sprites
    print("Initializing rembg session...")
    session = rembg.new_session()
    print("Session ready.")

    processed = {}
    reports = {}

    for name, box in SPRITE_DEFS:
        print(f"\nProcessing {name} (crop box: {box})...")
        cropped = full_sheet.crop(box)

        # 1. Background removal using rembg with cached session
        rembg_result = rembg.remove(cropped, session=session)

        # 2. Filter out detached sparkles, motion lines, and symbols (?, zzz, stars)
        cleaned = remove_floating_artifacts(rembg_result, name)

        # 3. Trim empty space
        bbox = cleaned.getbbox()
        if bbox:
            trimmed = cleaned.crop(bbox)
        else:
            trimmed = cleaned
            print(f"Warning: {name} bounding box was empty!")

        # 4. Center on uniform 512x512 transparent canvas
        canvas = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
        offset_x = (CANVAS_SIZE[0] - trimmed.width) // 2
        offset_y = (CANVAS_SIZE[1] - trimmed.height) // 2
        canvas.paste(trimmed, (offset_x, offset_y), trimmed)

        out_path = os.path.join(SPRITE_OUTPUT_DIR, f"{name}.png")
        canvas.save(out_path, "PNG")
        processed[name] = canvas
        print(f"Saved: {out_path} (Sprite body: {trimmed.width}x{trimmed.height} centered on 512x512)")

        # Analyze cutout quality
        alpha_channel = np.array(canvas)[:, :, 3]
        semi_transparent = np.sum((alpha_channel > 5) & (alpha_channel < 250))
        opaque = np.sum(alpha_channel >= 250)
        reports[name] = {
            "size": (trimmed.width, trimmed.height),
            "semi_transparent_edge_px": int(semi_transparent),
            "opaque_px": int(opaque),
            "quality": "Clean anti-aliased cutout" if semi_transparent > 50 else "Crisp hard edge",
        }

    # Generate preview grid (4 cols x 2 rows)
    generate_preview_grid(processed, reports)
    print("\nSprite preparation complete.")


def generate_preview_grid(sprites_dict, reports):
    cols = 4
    rows = 2
    thumb_w, thumb_h = 256, 256
    pad = 16
    label_h = 28

    cell_w = thumb_w + pad * 2
    cell_h = thumb_h + pad * 2 + label_h

    total_w = cols * cell_w
    total_h = rows * cell_h

    # Create dark slate checkerboard background to visualize transparency and cutouts
    grid = Image.new("RGBA", (total_w, total_h), (20, 24, 32, 255))
    draw = ImageDraw.Draw(grid)

    check_size = 16
    for y in range(0, total_h, check_size):
        for x in range(0, total_w, check_size):
            if ((x // check_size) + (y // check_size)) % 2 == 1:
                draw.rectangle([x, y, x + check_size, y + check_size], fill=(28, 33, 44, 255))

    names = [d[0] for d in SPRITE_DEFS]
    for idx, name in enumerate(names):
        col = idx % cols
        row = idx // cols
        cx = col * cell_w
        cy = row * cell_h

        # Draw cell container border
        draw.rectangle([cx + 6, cy + 6, cx + cell_w - 6, cy + cell_h - 6], outline=(60, 70, 90, 200), width=1)

        # Paste sprite thumbnail
        sprite = sprites_dict[name].resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        grid.paste(sprite, (cx + pad, cy + pad), sprite)

        # Label
        text = f"{idx + 1}. {name} ({reports[name]['size'][0]}x{reports[name]['size'][1]})"
        draw.text((cx + pad, cy + thumb_h + pad + 6), text, fill=(220, 230, 255, 255))

    preview_path = "sprites_preview.png"
    grid.save(preview_path, "PNG")
    print(f"\nPreview grid saved to: {preview_path}")

    print("\n--- CUTOUT QUALITY SUMMARY ---")
    rough_cutouts = []
    for name, r in reports.items():
        print(f" - {name:<12}: Body size {r['size'][0]}x{r['size'][1]} | Edge anti-aliasing: {r['semi_transparent_edge_px']} px | {r['quality']}")
        if r['semi_transparent_edge_px'] < 10:
            rough_cutouts.append(name)

    if rough_cutouts:
        print(f"\nNote: The following sprites had low anti-aliasing: {rough_cutouts}")
    else:
        print("\nAll 8 cutouts produced clean, anti-aliased transparent edges with floating artifacts removed.")


if __name__ == "__main__":
    process_sprites()
