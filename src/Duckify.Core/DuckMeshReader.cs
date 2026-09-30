using System.Text;

namespace Duckify.Core;

public static class DuckMeshReader
{
    private const float WeightTolerance = 0.01f;

    /// <summary>Reads and checks a .duckmesh file. Every problem is a <see cref="DuckMeshFormatException"/> that says what is wrong.</summary>
    public static DuckMeshData Read(Stream stream)
    {
        try
        {
            return ReadChecked(stream);
        }
        catch (EndOfStreamException)
        {
            throw new DuckMeshFormatException("The duck mesh file ends early.");
        }
    }

    private static DuckMeshData ReadChecked(Stream stream)
    {
        using var r = new BinaryReader(stream, Encoding.UTF8, leaveOpen: true);

        var magic = r.ReadBytes(4);
        if (magic.Length < 4) throw new EndOfStreamException();
        if (magic[0] != 'D' || magic[1] != 'U' || magic[2] != 'C' || magic[3] != 'K')
            throw new DuckMeshFormatException("Not a duck mesh: the file does not start with DUCK.");

        var version = r.ReadUInt16();
        if (version != DuckMeshData.FormatVersion)
            throw new DuckMeshFormatException($"Duck mesh version {version} is not supported; this build reads version {DuckMeshData.FormatVersion}.");

        var boneCount = r.ReadUInt16();
        var vertexCount = r.ReadUInt32();
        var submeshCount = r.ReadUInt16();
        r.ReadUInt16(); // reserved
        if (boneCount is 0 or > 255) throw new DuckMeshFormatException($"A duck mesh needs 1 to 255 bones, not {boneCount}.");
        if (vertexCount == 0 || vertexCount > 1_000_000) throw new DuckMeshFormatException($"A duck mesh needs 1 to 1,000,000 vertices, not {vertexCount}.");
        if (submeshCount == 0) throw new DuckMeshFormatException("A duck mesh needs at least one submesh.");

        var bones = new string[boneCount];
        for (var i = 0; i < boneCount; i++)
        {
            var length = r.ReadByte();
            var bytes = r.ReadBytes(length);
            if (bytes.Length < length) throw new EndOfStreamException();
            bones[i] = Encoding.UTF8.GetString(bytes);
        }

        var submeshes = new DuckSubmesh[submeshCount];
        for (var s = 0; s < submeshCount; s++)
        {
            var color = new DuckColor(r.ReadByte(), r.ReadByte(), r.ReadByte(), r.ReadByte());
            var smoothness = r.ReadSingle();
            var indexCount = r.ReadUInt32();
            if (indexCount % 3 != 0) throw new DuckMeshFormatException($"Submesh {s} has {indexCount} indices, which is not a whole number of triangles.");

            // Reject counts that cannot fit in the file before allocating
            if (stream.CanSeek)
            {
                if (indexCount * 4L > stream.Length - stream.Position)
                    throw new DuckMeshFormatException($"Submesh {s} claims {indexCount} indices, more than the file holds.");
            }
            else
            {
                if (indexCount > 3u * 1_000_000u * 20u)
                    throw new DuckMeshFormatException($"Submesh {s} claims {indexCount} indices, more than the file holds.");
            }

            var indices = new int[indexCount];
            for (var i = 0; i < indexCount; i++)
            {
                var index = r.ReadUInt32();
                if (index >= vertexCount) throw new DuckMeshFormatException($"Submesh {s} uses index {index}, but the mesh has {vertexCount} vertices.");
                indices[i] = (int)index;
            }
            submeshes[s] = new DuckSubmesh(color, smoothness, indices);
        }

        var n = (int)vertexCount;
        var positions = new float[n * 3];
        var normals = new float[n * 3];
        var boneIndices = new byte[n * 4];
        var weights = new float[n * 4];
        for (var v = 0; v < n; v++)
        {
            for (var k = 0; k < 3; k++) positions[v * 3 + k] = r.ReadSingle();
            for (var k = 0; k < 3; k++) normals[v * 3 + k] = r.ReadSingle();
            for (var k = 0; k < 4; k++)
            {
                var bone = r.ReadByte();
                if (bone >= boneCount) throw new DuckMeshFormatException($"vertex {v} uses bone {bone}, but the mesh has {boneCount} bones.");
                boneIndices[v * 4 + k] = bone;
            }
            var sum = 0f;
            for (var k = 0; k < 4; k++)
            {
                var w = r.ReadSingle();
                if (w < 0 || float.IsNaN(w)) throw new DuckMeshFormatException($"vertex {v} has a negative or invalid weight.");
                weights[v * 4 + k] = w;
                sum += w;
            }
            if (Math.Abs(sum - 1f) > WeightTolerance)
                throw new DuckMeshFormatException($"vertex {v} has weights adding up to {sum:0.###}, not 1.");
        }

        if (stream.ReadByte() != -1)
            throw new DuckMeshFormatException("The duck mesh file has extra bytes after the last vertex.");

        return new DuckMeshData(bones, positions, normals, boneIndices, weights, submeshes);
    }
}
