using System.Text;

namespace Duckify.Core;

/// <summary>Writes the format <see cref="DuckMeshReader"/> reads. The shipped files come from art/duckmesh_io.py; this is for tests.</summary>
public static class DuckMeshWriter
{
    public static void Write(Stream stream, DuckMeshData mesh)
    {
        var n = mesh.VertexCount;
        if (mesh.Positions.Length != n * 3 || mesh.Normals.Length != n * 3 || mesh.BoneIndices.Length != n * 4 || mesh.Weights.Length != n * 4)
            throw new ArgumentException("Positions and normals need 3 values per vertex, bone indices and weights 4.", nameof(mesh));

        using var w = new BinaryWriter(stream, Encoding.UTF8, leaveOpen: true);
        w.Write("DUCK"u8.ToArray());
        w.Write((ushort)DuckMeshData.FormatVersion);
        w.Write((ushort)mesh.Bones.Length);
        w.Write((uint)n);
        w.Write((ushort)mesh.Submeshes.Length);
        w.Write((ushort)0);
        foreach (var bone in mesh.Bones)
        {
            var bytes = Encoding.UTF8.GetBytes(bone);
            w.Write((byte)bytes.Length);
            w.Write(bytes);
        }
        foreach (var sub in mesh.Submeshes)
        {
            w.Write(sub.Color.R);
            w.Write(sub.Color.G);
            w.Write(sub.Color.B);
            w.Write(sub.Color.A);
            w.Write(sub.Smoothness);
            w.Write((uint)sub.Indices.Length);
            foreach (var index in sub.Indices) w.Write((uint)index);
        }
        for (var v = 0; v < n; v++)
        {
            for (var k = 0; k < 3; k++) w.Write(mesh.Positions[v * 3 + k]);
            for (var k = 0; k < 3; k++) w.Write(mesh.Normals[v * 3 + k]);
            for (var k = 0; k < 4; k++) w.Write(mesh.BoneIndices[v * 4 + k]);
            for (var k = 0; k < 4; k++) w.Write(mesh.Weights[v * 4 + k]);
        }
    }
}
