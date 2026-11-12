#!/usr/bin/env python3
"""cutest-picture-01 entry: procedural cute kitten rendered with SDF, stdlib only."""
import os, zlib, struct, math

W = H = 640


def clamp01(v):
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)


def smooth(e0, e1, v):
    t = clamp01((v - e0) / (e1 - e0))
    return t * t * (3.0 - 2.0 * t)


def sd_circle(px, py, cx, cy, r):
    return math.hypot(px - cx, py - cy) - r


def sd_ellipse(px, py, cx, cy, rx, ry, th=0.0):
    x = px - cx
    y = py - cy
    c = math.cos(th)
    s = math.sin(th)
    u = c * x + s * y
    v = -s * x + c * y
    n = math.hypot(u / rx, v / ry)
    return (n - 1.0) * min(rx, ry)


def sd_segment(px, py, ax, ay, bx, by):
    pax = px - ax
    pay = py - ay
    bax = bx - ax
    bay = by - ay
    h = (pax * bax + pay * bay) / (bax * bax + bay * bay)
    h = max(0.0, min(1.0, h))
    return math.hypot(pax - bax * h, pay - bay * h)


def cov(d):
    return 1.0 - smooth(-1.0, 1.0, d)


def blend(dst, col, a):
    if a <= 0.0:
        return dst
    if a >= 1.0:
        return col
    return (dst[0] * (1 - a) + col[0] * a,
            dst[1] * (1 - a) + col[1] * a,
            dst[2] * (1 - a) + col[2] * a)


# palette
BG_IN = (1.0, 0.97, 0.91)
BG_OUT = (0.99, 0.90, 0.78)
SHADOW = (0.80, 0.72, 0.63)
FUR = (0.55, 0.66, 0.76)       # gray-blue
FUR_DARK = (0.45, 0.56, 0.66)
PINK = (0.968, 0.662, 0.721)
PINK_DEEP = (0.94, 0.52, 0.60)
EYE = (0.16, 0.17, 0.20)
WHITE = (1.0, 1.0, 1.0)

# figure geometry
CX, CY = 320.0, 310.0        # head centre
BODY = (320.0, 480.0, 145.0, 128.0)   # body ellipse
HEAD_R = 122.0
EAR_L = (232.0, 205.0, 44.0, 74.0, -0.28)
EAR_R = (408.0, 205.0, 44.0, 74.0, 0.28)
EAR_L_IN = (238.0, 212.0, 24.0, 44.0, -0.28)
EAR_R_IN = (402.0, 212.0, 24.0, 44.0, 0.28)
EYE_L = (268.0, 305.0, 34.0)
EYE_R = (372.0, 305.0, 34.0)
NOSE = (320.0, 348.0)
BLUSH_L = (244.0, 360.0)
BLUSH_R = (396.0, 360.0)


def render():
    w2 = W / 2.0
    h2 = H / 2.0
    rows = []
    for y in range(H):
        row = bytearray()
        for x in range(W):
            # background radial gradient (soft cream)
            dx = (x - w2) / w2
            dy = (y - h2) / h2
            r = (math.hypot(dx, dy) * 0.55 + 0.15) * 1.15
            r = clamp01(r)
            bg = (BG_IN[0] * (1 - r) + BG_OUT[0] * r,
                  BG_IN[1] * (1 - r) + BG_OUT[1] * r,
                  BG_IN[2] * (1 - r) + BG_OUT[2] * r)
            c = bg

            # floor shadow
            a = cov(sd_ellipse(x, y, 320.0, 512.0, 190.0, 42.0)) * 0.30
            c = blend(c, SHADOW, a)

            # body
            a = cov(sd_ellipse(x, y, *BODY))
            c = blend(c, FUR, a)

            # ears (behind head)
            a = cov(sd_ellipse(x, y, *EAR_L))
            c = blend(c, FUR, a)
            a = cov(sd_ellipse(x, y, *EAR_R))
            c = blend(c, FUR, a)
            a = cov(sd_ellipse(x, y, *EAR_L_IN))
            c = blend(c, PINK, a)
            a = cov(sd_ellipse(x, y, *EAR_R_IN))
            c = blend(c, PINK, a)

            # head
            a = cov(sd_circle(x, y, CX, CY, HEAD_R))
            c = blend(c, FUR, a)

            # soft jaw shading
            a = cov(sd_ellipse(x, y, 320.0, 392.0, 74.0, 40.0)) * 0.20
            c = blend(c, FUR_DARK, a)

            # white muzzle/chin patch (lighter, cuter)
            a = cov(sd_ellipse(x, y, 320.0, 400.0, 52.0, 34.0)) * 0.85
            c = blend(c, (0.86, 0.90, 0.95), a)

            # eyes
            a = cov(sd_circle(x, y, *EYE_L))
            c = blend(c, EYE, a)
            a = cov(sd_circle(x, y, *EYE_R))
            c = blend(c, EYE, a)
            # eye highlights
            a = cov(sd_circle(x, y, EYE_L[0] - 9, EYE_L[1] - 9, 11.0))
            c = blend(c, WHITE, a)
            a = cov(sd_circle(x, y, EYE_R[0] - 9, EYE_R[1] - 9, 11.0))
            c = blend(c, WHITE, a)
            a = cov(sd_circle(x, y, EYE_L[0] + 10, EYE_L[1] + 10, 5.0))
            c = blend(c, WHITE, a)
            a = cov(sd_circle(x, y, EYE_R[0] + 10, EYE_R[1] + 10, 5.0))
            c = blend(c, WHITE, a)

            # nose (rounded triangle ~ small circle)
            a = cov(sd_circle(x, y, NOSE[0], NOSE[1], 10.0))
            c = blend(c, PINK_DEEP, a)

            # mouth (w shape: two small arcs as circles + vertical join)
            a = cov(sd_circle(x, y, 308.0, 368.0, 7.0)) * 0.9
            c = blend(c, EYE, a)
            a = cov(sd_circle(x, y, 332.0, 368.0, 7.0)) * 0.9
            c = blend(c, EYE, a)
            a = cov(sd_circle(x, y, 320.0, 364.0, 6.0)) * 0.9
            c = blend(c, EYE, a)

            # blush
            a = cov(sd_ellipse(x, y, BLUSH_L[0], BLUSH_L[1], 26.0, 15.0, -0.2)) * 0.45
            c = blend(c, PINK_DEEP, a)
            a = cov(sd_ellipse(x, y, BLUSH_R[0], BLUSH_R[1], 26.0, 15.0, 0.2)) * 0.45
            c = blend(c, PINK_DEEP, a)

            # whiskers
            for (ax, ay, bx, by) in ((196.0, 328.0, 246.0, 338.0),
                                     (190.0, 352.0, 244.0, 352.0),
                                     (196.0, 376.0, 246.0, 368.0),
                                     (444.0, 328.0, 394.0, 338.0),
                                     (450.0, 352.0, 396.0, 352.0),
                                     (444.0, 376.0, 394.0, 368.0)):
                a = cov(sd_segment(x, y, ax, ay, bx, by) - 1.6) * 0.55
                c = blend(c, (0.40, 0.48, 0.55), a)

            row += bytes((int(clamp01(c[0]) * 255 + 0.5),
                          int(clamp01(c[1]) * 255 + 0.5),
                          int(clamp01(c[2]) * 255 + 0.5)))
        rows.append(bytes(row))
    return rows


def write_png(path, rows):
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