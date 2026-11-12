import struct
import zlib

SIGNATURE = b"\x89PNG\r\n\x1a\n"
_CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


def _chunk(tag, body):
    return (struct.pack(">I", len(body)) + tag + body
            + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))


def encode_png(width, height, rgb):
    if len(rgb) != width * height * 3:
        raise ValueError("pixel buffer size does not match dimensions")
    stride = width * 3
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (SIGNATURE + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(bytes(raw), 6))
            + _chunk(b"IEND", b""))


def _paeth(a, b, c):
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _over_white(c, a):
    return (c * a + 255 * (255 - a)) // 255


def decode_png(data):
    if bytes(data[:8]) != SIGNATURE:
        raise ValueError("not a PNG file")
    pos = 8
    width = height = bit_depth = color_type = interlace = None
    palette = None
    idat = bytearray()
    while pos + 8 <= len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        tag = bytes(data[pos + 4:pos + 8])
        body = bytes(data[pos + 8:pos + 8 + length])
        pos += 12 + length
        if tag == b"IHDR":
            width, height, bit_depth, color_type, _c, _f, interlace = struct.unpack(">IIBBBBB", body)
        elif tag == b"PLTE":
            palette = body
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
    if width is None:
        raise ValueError("missing IHDR chunk")
    if interlace != 0:
        raise ValueError("interlaced PNG is not supported")
    if color_type not in _CHANNELS:
        raise ValueError(f"unsupported color type {color_type}")
    if bit_depth not in (8, 16):
        raise ValueError(f"unsupported bit depth {bit_depth}")
    if color_type == 3 and (bit_depth != 8 or palette is None):
        raise ValueError("palette PNG must be 8-bit with a PLTE chunk")
    sample = 2 if bit_depth == 16 else 1
    bpp = _CHANNELS[color_type] * sample
    stride = width * bpp
    raw = zlib.decompress(bytes(idat))
    if len(raw) < height * (stride + 1):
        raise ValueError("truncated image data")
    out = bytearray(width * height * 3)
    prev = bytearray(stride)
    off = 0
    for y in range(height):
        f = raw[off]
        off += 1
        line = bytearray(raw[off:off + stride])
        off += stride
        if f == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif f == 3:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif f == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                c = prev[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + _paeth(a, prev[i], c)) & 0xFF
        elif f != 0:
            raise ValueError(f"unknown filter type {f}")
        prev = line
        row = y * width * 3
        for x in range(width):
            s = x * bpp
            if color_type == 0:
                g = line[s]
                out[row + x * 3] = g
                out[row + x * 3 + 1] = g
                out[row + x * 3 + 2] = g
            elif color_type == 2:
                out[row + x * 3] = line[s]
                out[row + x * 3 + 1] = line[s + sample]
                out[row + x * 3 + 2] = line[s + 2 * sample]
            elif color_type == 3:
                idx = line[s]
                out[row + x * 3:row + x * 3 + 3] = palette[idx * 3:idx * 3 + 3]
            elif color_type == 4:
                v = _over_white(line[s], line[s + sample])
                out[row + x * 3] = v
                out[row + x * 3 + 1] = v
                out[row + x * 3 + 2] = v
            else:
                a = line[s + 3 * sample]
                out[row + x * 3] = _over_white(line[s], a)
                out[row + x * 3 + 1] = _over_white(line[s + sample], a)
                out[row + x * 3 + 2] = _over_white(line[s + 2 * sample], a)
    return width, height, out
