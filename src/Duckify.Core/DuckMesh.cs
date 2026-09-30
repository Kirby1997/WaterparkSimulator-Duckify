namespace Duckify.Core;

/// <summary>An sRGB colour, as the game's textures store it.</summary>
public readonly record struct DuckColor(byte R, byte G, byte B, byte A);

/// <summary>The triangles drawn in one flat colour.</summary>
public sealed class DuckSubmesh
{
    public DuckSubmesh(DuckColor color, float smoothness, int[] indices)
    {
        Color = color;
        Smoothness = smoothness;
        Indices = indices;
    }

    public DuckColor Color { get; }

    /// <summary>0 is matte, 1 is mirror-smooth.</summary>
    public float Smoothness { get; }

    /// <summary>Three vertex indices per triangle, clockwise seen from outside (Unity's front face).</summary>
    public int[] Indices { get; }
}

/// <summary>One duck mesh as stored in a .duckmesh file, before it becomes a Unity Mesh.</summary>
public sealed class DuckMeshData
{
    public const int FormatVersion = 1;

    public DuckMeshData(string[] bones, float[] positions, float[] normals, byte[] boneIndices, float[] weights, DuckSubmesh[] submeshes)
    {
        Bones = bones;
        Positions = positions;
        Normals = normals;
        BoneIndices = boneIndices;
        Weights = weights;
        Submeshes = submeshes;
    }

    /// <summary>Game bone names; <see cref="BoneIndices"/> index into this list.</summary>
    public string[] Bones { get; }

    /// <summary>x, y, z per vertex, in the bind space of the game mesh the duck was built against.</summary>
    public float[] Positions { get; }

    public float[] Normals { get; }

    /// <summary>Four per vertex.</summary>
    public byte[] BoneIndices { get; }

    /// <summary>Four per vertex, summing to 1.</summary>
    public float[] Weights { get; }

    public DuckSubmesh[] Submeshes { get; }

    public int VertexCount => Positions.Length / 3;

    public int TriangleCount => Submeshes.Sum(s => s.Indices.Length) / 3;
}

public sealed class DuckMeshFormatException : Exception
{
    public DuckMeshFormatException(string message) : base(message)
    {
    }
}
