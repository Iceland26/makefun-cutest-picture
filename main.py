#!/usr/bin/env python3
"""cutest-picture-01 entry: a procedural 'cute kitten' PNG rendered
entirely with signed distance fields, using only the Python standard
library (os, zlib, struct, math). Writes entry.png to MAKEFUN_OUTPUT_DIR.
"""
import os
import zlib
import struct
import math

# Canvas dimensions (square).
W = H = 640


# --------------------------------------------------------------------------
# Small math / shading helpers
# --------------------------------------------------------------------------
def clamp01(v):
    """Clamp a float into [0, 1]."""
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)


def smooth(e0, e1, v):
    """Smoothstep: 0 -> 1 over [e0, e1] with zero derivatives at the ends."""
    t = clamp01((v - e0) / (e1 - e0))
    return t * t * (3.0 - 2.0 * t)


def sd_circle(px, py, cx, cy, r):
    """Signed distance to a circle centred at (cx, cy)."""
    return math.hypot(px - cx, py - cy) - r


def sd_ellipse(px, py, cx, cy, rx, ry, th=0.0):
    """Signed distance to an axis-aligned (optionally rotated) ellipse."""
    x = px - cx
    y = py - cy
    c = math.cos(th)
    s = math.sin(th)
    u = c * x + s * y
    v = -s * x + c * y
    n = math.hypot(u / rx, v / ry)
    return (n - 1.0) * min(rx, ry)


def sd_segment(px, py, ax, ay, bx, by):
    """Signed distance to the line segment (ax,ay)-(bx,by)."""
    pax = px - ax
    pay = py - ay
    bax = bx - ax
    bay = by - ay
    h = (pax * bax + pay * bay) / (bax * bax + bay * bay)
    h = max(0.0, min(1.0, h))
    return math.hypot(pax - bax * h, pay - bay * h)


def cov(d):
    """Coverage from a signed distance: 1 inside, 0 outside, soft ~1px edge."""
    return 1.0 - smooth(-1.0, 1.0, d)


def blend(dst, col, a):
    """Alpha-composite `col` over `dst` with coverage `a`."""
    if a <= 0.0:
        return dst
    if a >= 1.0:
        return col
    return (dst[0] * (1 - a) + col[0] * a,
            dst[1] * (1 - a) + col[1] * a,
            dst[2] * (1 - a) + col[2] * a)


# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------
BG_IN = (1.0, 0.97, 0.91)          # warm cream, centre
BG_OUT = (0.99, 0.90, 0.78)        # warmer tan, edges
SHADOW = (0.80, 0.72, 0.63)        # soft floor shadow
FUR = (0.55, 0.66, 0.76)           # gray-blue fur
FUR_DARK = (0.45, 0.56, 0.66)      # darker fur for shading
PINK = (0.968, 0.662, 0.721)       # inner-ear pink
PINK_DEEP = (0.96, 0.47, 0.58)     # nose + blush pink (warmed)
EYE = (0.14, 0.15, 0.19)           # near-black for eyes/mouth
WHITE = (1.0, 1.0, 1.0)            # eye highlights
MUZZLE = (0.86, 0.90, 0.95)        # light muzzle/chin patch
WHISKER = (0.40, 0.48, 0.55)       # whisker grey

# --------------------------------------------------------------------------
# Figure geometry
# --------------------------------------------------------------------------
CX, CY = 320.0, 310.0                        # head centre
BODY = (320.0, 480.0, 145.0, 128.0)          # body ellipse
HEAD_R = 122.0                               # head radius
EAR_L = (232.0, 205.0, 44.0, 74.0, -0.28)    # left ear
EAR_R = (408.0, 205.0, 44.0, 74.0, 0.28)     # right ear
EAR_L_IN = (238.0, 212.0, 24.0, 44.0, -0.28) # left inner ear
EAR_R_IN = (402.0, 212.0, 24.0, 44.0, 0.28)  # right inner ear
EYE_L = (268.0, 305.0, 34.0)                 # left eye (cx, cy, r)
EYE_R = (372.0, 305.0, 34.0)                 # right eye
NOSE = (320.0, 348.0)                        # nose centre
BLUSH_L = (244.0, 360.0)                     # left blush centre
BLUSH_R = (396.0, 360.0)                     # right blush centre


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------
def render():
    """Compose the kitten one SDF layer at a time into 640x640 RGB rows."""
    w2 = W / 2.0
    h2 = H / 2.0
    rows = []
    for y in range(H):
        row = bytearray()
        for x in range(W):
            # Soft cream radial-gradient background.
            dx = (x - w2) / w2
            dy = (y - h2) / h2
            r = (math.hypot(dx, dy) * 0.55 + 0.15) * 1.15
            r = clamp01(r)
            c = (BG_IN[0] * (1 - r) + BG_OUT[0] * r,
                 BG_IN[1] * (1 - r) + BG_OUT[1] * r,
                 BG_IN[2] * (1 - r) + BG_OUT[2] * r)

            # Floor shadow beneath the body.
            a = cov(sd_ellipse(x, y, 320.0, 512.0, 190.0, 42.0)) * 0.30
            c = blend(c, SHADOW, a)

            # Body.
            a = cov(sd_ellipse(x, y, *BODY))
            c = blend(c, FUR, a)

            # Ears sit behind the head; draw them first, inner patches on top.
            a = cov(sd_ellipse(x, y, *EAR_L))
            c = blend(c, FUR, a)
            a = cov(sd_ellipse(x, y, *EAR_R))
            c = blend(c, FUR, a)
            a = cov(sd_ellipse(x, y, *EAR_L_IN))
            c = blend(c, PINK, a)
            a = cov(sd_ellipse(x, y, *EAR_R_IN))
            c = blend(c, PINK, a)

            # Head.
            a = cov(sd_circle(x, y, CX, CY, HEAD_R))
            c = blend(c, FUR, a)

            # Subtle jaw shading.
            a = cov(sd_ellipse(x, y, 320.0, 392.0, 74.0, 40.0)) * 0.20
            c = blend(c, FUR_DARK, a)

            # Lighter muzzle/chin patch.
            a = cov(sd_ellipse(x, y, 320.0, 400.0, 52.0, 34.0)) * 0.85
            c = blend(c, MUZZLE, a)

            # Eyes: two dark circles, each with a large and a small highlight.
            a = cov(sd_circle(x, y, *EYE_L))
            c = blend(c, EYE, a)
            a = cov(sd_circle(x, y, *EYE_R))
            c = blend(c, EYE, a)
            a = cov(sd_circle(x, y, EYE_L[0] - 9, EYE_L[1] - 9, 11.0))
            c = blend(c, WHITE, a)
            a = cov(sd_circle(x, y, EYE_R[0] - 9, EYE_R[1] - 9, 11.0))
            c = blend(c, WHITE, a)
            a = cov(sd_circle(x, y, EYE_L[0] + 10, EYE_L[1] + 10, 5.0))
            c = blend(c, WHITE, a)
            a = cov(sd_circle(x, y, EYE_R[0] + 10, EYE_R[1] + 10, 5.0))
            c = blend(c, WHITE, a)

            # Nose.
            a = cov(sd_circle(x, y, NOSE[0], NOSE[1], 10.0))
            c = blend(c, PINK_DEEP, a)
            # Small white glint on the nose for a soft, cute shine.
            a = cov(sd_circle(x, y, NOSE[0] - 3, NOSE[1] - 3, 3.0)) * 0.85
            c = blend(c, WHITE, a)

            # Mouth: an upside-down 'w' from two small circles plus a join.
            a = cov(sd_circle(x, y, 308.0, 368.0, 7.0)) * 0.9
            c = blend(c, EYE, a)
            a = cov(sd_circle(x, y, 332.0, 368.0, 7.0)) * 0.9
            c = blend(c, EYE, a)
            a = cov(sd_circle(x, y, 320.0, 364.0, 6.0)) * 0.9
            c = blend(c, EYE, a)

            # Blush cheeks.
            a = cov(sd_ellipse(x, y, BLUSH_L[0], BLUSH_L[1], 26.0, 15.0, -0.2)) * 0.45
            c = blend(c, PINK_DEEP, a)
            a = cov(sd_ellipse(x, y, BLUSH_R[0], BLUSH_R[1], 26.0, 15.0, 0.2)) * 0.45
            c = blend(c, PINK_DEEP, a)

            # Whiskers (three per side).
            for (ax, ay, bx, by) in ((196.0, 328.0, 246.0, 338.0),
                                     (190.0, 352.0, 244.0, 352.0),
                                     (196.0, 376.0, 246.0, 368.0),
                                     (444.0, 328.0, 394.0, 338.0),
                                     (450.0, 352.0, 396.0, 352.0),
                                     (444.0, 376.0, 394.0, 368.0)):
                a = cov(sd_segment(x, y, ax, ay, bx, by) - 1.6) * 0.55
                c = blend(c, WHISKER, a)

            row += bytes((int(clamp01(c[0]) * 255 + 0.5),
                          int(clamp01(c[1]) * 255 + 0.5),
                          int(clamp01(c[2]) * 255 + 0.5)))
        rows.append(bytes(row))
    return rows


# --------------------------------------------------------------------------
# PNG encoding (manual, stdlib only)
# --------------------------------------------------------------------------
def write_png(path, rows):
    """Encode RGB rows as a PNG (IHDR + IDAT + IEND) and write to `path`."""

    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data
                + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))

    raw = b''.join(b'\x00' + r for r in rows)
    ihdr = struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)  # 8-bit RGB
    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', ihdr)
           + chunk(b'IDAT', zlib.compress(raw, 9))
           + chunk(b'IEND', b''))
    with open(path, 'wb') as f:
        f.write(png)


def main():
    outdir = os.environ.get('MAKEFUN_OUTPUT_DIR', '/output')
    os.makedirs(outdir, exist_ok=True)
    write_png(os.path.join(outdir, 'entry.png'), render())


if __name__ == '__main__':
    main()