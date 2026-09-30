namespace Duckify.Tests;

public class DuckMeshReaderTests
{
    /// <summary>One triangle, two bones, one white submesh.</summary>
    private static DuckMeshData Sample(
        float[]? weights = null, byte[]? boneIndices = null, int[]? indices = null, string[]? bones = null)
    {
        return new DuckMeshData(
            bones ?? new[] { "pelvis", "head" },
            positions: new float[] { 0, 0, 0, 1, 0, 0, 0, 1, 0 },
            normals: new float[] { 0, 0, -1, 0, 0, -1, 0, 0, -1 },
            boneIndices: boneIndices ?? new byte[] { 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0 },
            weights: weights ?? new float[] { 0.75f, 0.25f, 0, 0, 1, 0, 0, 0, 0.5f, 0.5f, 0, 0 },
            submeshes: new[] { new DuckSubmesh(new DuckColor(246, 243, 236, 255), 0.35f, indices ?? new[] { 0, 1, 2 }) });
    }

    private static byte[] Bytes(DuckMeshData mesh)
    {
        using var stream = new MemoryStream();
        DuckMeshWriter.Write(stream, mesh);
        return stream.ToArray();
    }

    private static DuckMeshData ReadBytes(byte[] bytes) => DuckMeshReader.Read(new MemoryStream(bytes));

    [Fact]
    public void A_written_mesh_reads_back_the_same()
    {
        var mesh = ReadBytes(Bytes(Sample()));

        Assert.Equal(new[] { "pelvis", "head" }, mesh.Bones);
        Assert.Equal(3, mesh.VertexCount);
        Assert.Equal(1, mesh.TriangleCount);
        Assert.Equal(new float[] { 0, 0, 0, 1, 0, 0, 0, 1, 0 }, mesh.Positions);
        Assert.Equal(new float[] { 0, 0, -1, 0, 0, -1, 0, 0, -1 }, mesh.Normals);
        Assert.Equal(new byte[] { 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0 }, mesh.BoneIndices);
        Assert.Equal(0.75f, mesh.Weights[0]);
        var sub = Assert.Single(mesh.Submeshes);
        Assert.Equal(new DuckColor(246, 243, 236, 255), sub.Color);
        Assert.Equal(0.35f, sub.Smoothness);
        Assert.Equal(new[] { 0, 1, 2 }, sub.Indices);
    }

    [Fact]
    public void The_file_starts_with_DUCK_and_version_1()
    {
        var bytes = Bytes(Sample());
        Assert.Equal("DUCK"u8.ToArray(), bytes[..4]);
        Assert.Equal(1, BitConverter.ToUInt16(bytes, 4));
    }

    [Fact]
    public void Rejects_a_file_that_is_not_a_duck_mesh()
    {
        var bytes = Bytes(Sample());
        bytes[0] = (byte)'X';
        var e = Assert.Throws<DuckMeshFormatException>(() => ReadBytes(bytes));
        Assert.Contains("DUCK", e.Message);
    }

    [Fact]
    public void Rejects_an_unknown_version()
    {
        var bytes = Bytes(Sample());
        bytes[4] = 2;
        var e = Assert.Throws<DuckMeshFormatException>(() => ReadBytes(bytes));
        Assert.Contains("version 2", e.Message);
    }

    [Fact]
    public void Rejects_a_bone_index_past_the_bone_table()
    {
        var bad = Sample(boneIndices: new byte[] { 0, 5, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0 });
        var e = Assert.Throws<DuckMeshFormatException>(() => ReadBytes(Bytes(bad)));
        Assert.Contains("vertex 0", e.Message);
        Assert.Contains("bone 5", e.Message);
    }

    [Fact]
    public void Rejects_weights_that_do_not_add_up_to_one()
    {
        var bad = Sample(weights: new float[] { 0.75f, 0.25f, 0, 0, 0.5f, 0, 0, 0, 0.5f, 0.5f, 0, 0 });
        var e = Assert.Throws<DuckMeshFormatException>(() => ReadBytes(Bytes(bad)));
        Assert.Contains("vertex 1", e.Message);
        Assert.Contains("0.5", e.Message);
    }

    [Fact]
    public void Rejects_a_triangle_index_past_the_vertices()
    {
        var bad = Sample(indices: new[] { 0, 1, 3 });
        var e = Assert.Throws<DuckMeshFormatException>(() => ReadBytes(Bytes(bad)));
        Assert.Contains("index 3", e.Message);
    }

    [Fact]
    public void Rejects_a_file_that_ends_early()
    {
        var bytes = Bytes(Sample());
        var e = Assert.Throws<DuckMeshFormatException>(() => ReadBytes(bytes[..^5]));
        Assert.Contains("ends early", e.Message);
    }

    [Fact]
    public void Rejects_bytes_after_the_last_vertex()
    {
        var bytes = Bytes(Sample()).Concat(new byte[] { 1, 2, 3 }).ToArray();
        var e = Assert.Throws<DuckMeshFormatException>(() => ReadBytes(bytes));
        Assert.Contains("after the last vertex", e.Message);
    }

    [Fact]
    public void The_writer_refuses_arrays_of_the_wrong_length()
    {
        var bad = new DuckMeshData(new[] { "pelvis" }, new float[] { 0, 0, 0 }, new float[] { 0, 0 },
            new byte[] { 0, 0, 0, 0 }, new float[] { 1, 0, 0, 0 },
            new[] { new DuckSubmesh(new DuckColor(0, 0, 0, 255), 0, new[] { 0, 0, 0 }) });
        Assert.Throws<ArgumentException>(() => Bytes(bad));
    }

    [Fact]
    public void Rejects_a_submesh_that_claims_more_indices_than_the_file_holds()
    {
        var bytes = Bytes(Sample());
        // Overwrite the submesh's indexCount with 0xFFFFFFFFu
        // Format: header (16) + bones (1+6 + 1+4 = 12, ending at 28) + submesh (4 colour + 4 smoothness = 8, starting at 28)
        // So indexCount (u32) sits at offset 36
        BitConverter.GetBytes(0xFFFFFFFFu).CopyTo(bytes, 36);

        var e = Assert.Throws<DuckMeshFormatException>(() => ReadBytes(bytes));
        Assert.Contains("more than the file holds", e.Message);
    }

    [Fact]
    public void Rejects_extra_bytes_on_a_stream_that_cannot_seek()
    {
        var bytes = Bytes(Sample()).Concat(new byte[] { 1, 2, 3 }).ToArray();
        var stream = new NonSeekableStream(new MemoryStream(bytes));

        var e = Assert.Throws<DuckMeshFormatException>(() => DuckMeshReader.Read(stream));
        Assert.Contains("after the last vertex", e.Message);
    }

    [Fact]
    public void Reads_a_valid_mesh_from_a_stream_that_cannot_seek()
    {
        var bytes = Bytes(Sample());
        var stream = new NonSeekableStream(new MemoryStream(bytes));

        var mesh = DuckMeshReader.Read(stream);
        Assert.Equal(new[] { "pelvis", "head" }, mesh.Bones);
    }

    private class NonSeekableStream : Stream
    {
        private readonly MemoryStream _inner;

        public NonSeekableStream(MemoryStream inner) => _inner = inner;

        public override bool CanRead => true;
        public override bool CanSeek => false;
        public override bool CanWrite => false;
        public override long Length => throw new NotSupportedException();
        public override long Position
        {
            get => throw new NotSupportedException();
            set => throw new NotSupportedException();
        }

        public override void Flush() { }
        public override int Read(byte[] buffer, int offset, int count) => _inner.Read(buffer, offset, count);
        public override int ReadByte() => _inner.ReadByte();
        public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();
        public override void SetLength(long value) => throw new NotSupportedException();
        public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();
    }
}
