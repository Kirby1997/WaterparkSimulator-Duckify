"""Writes and reads .duckmesh files (format version 1). Pure Python so Blender and tests share it.

Layout (little-endian): b"DUCK", u16 version, u16 boneCount, u32 vertexCount, u16 submeshCount,
u16 reserved; bones as u8 length + UTF-8; submeshes as RGBA8, f32 smoothness, u32 count, u32
indices; vertices as 6 f32 (position, normal), 4 u8 bone indices, 4 f32 weights.
Must match src/Duckify.Core/DuckMeshReader.cs.
"""
import struct

VERSION = 1


def write(path, bones, positions, normals, bone_idx, weights, submeshes):
    n = len(positions)
    if not (len(normals) == len(bone_idx) == len(weights) == n):
        raise ValueError("positions, normals, bone_idx and weights need one entry per vertex")
    if not 1 <= len(bones) <= 255:
        raise ValueError(f"a duck mesh needs 1 to 255 bones, not {len(bones)}")
    for v, (idx, w) in enumerate(zip(bone_idx, weights)):
        if any(i >= len(bones) for i in idx):
            raise ValueError(f"vertex {v} uses a bone past the bone table")
        if abs(sum(w) - 1.0) > 0.01:
            raise ValueError(f"vertex {v} has weights adding up to {sum(w):.3f}, not 1")
    out = bytearray(b"DUCK")
    out += struct.pack("<HHIHH", VERSION, len(bones), n, len(submeshes), 0)
    for name in bones:
        b = name.encode("utf-8")
        out += struct.pack("<B", len(b)) + b
    for (r, g, b, a), smooth, indices in submeshes:
        if len(indices) % 3:
            raise ValueError("a submesh needs a whole number of triangles")
        if indices and max(indices) >= n:
            raise ValueError("a submesh uses an index past the vertices")
        out += struct.pack("<BBBBfI", r, g, b, a, smooth, len(indices))
        out += struct.pack(f"<{len(indices)}I", *indices)
    for p, nr, idx, w in zip(positions, normals, bone_idx, weights):
        out += struct.pack("<6f4B4f", *p, *nr, *idx, *w)
    with open(path, "wb") as f:
        f.write(out)


def read(path):
    data = open(path, "rb").read()
    if data[:4] != b"DUCK":
        raise ValueError("not a duck mesh")
    version, bone_count, n, sub_count, _ = struct.unpack_from("<HHIHH", data, 4)
    if version != VERSION:
        raise ValueError(f"version {version} is not supported")
    o = 16
    bones = []
    for _ in range(bone_count):
        length = data[o]
        bones.append(data[o + 1:o + 1 + length].decode("utf-8"))
        o += 1 + length
    submeshes = []
    for _ in range(sub_count):
        r, g, b, a, smooth, count = struct.unpack_from("<BBBBfI", data, o)
        o += 12
        indices = list(struct.unpack_from(f"<{count}I", data, o))
        o += 4 * count
        submeshes.append(((r, g, b, a), smooth, indices))
    positions, normals, bone_idx, weights = [], [], [], []
    for _ in range(n):
        vals = struct.unpack_from("<6f4B4f", data, o)
        o += 44
        positions.append(tuple(vals[0:3]))
        normals.append(tuple(vals[3:6]))
        bone_idx.append(tuple(vals[6:10]))
        weights.append(tuple(vals[10:14]))
    if o != len(data):
        raise ValueError("extra bytes after the last vertex")
    return dict(bones=bones, positions=positions, normals=normals, bone_idx=bone_idx,
                weights=weights, submeshes=submeshes)
