import os
import struct
import tempfile
import unittest

import duckmesh_io


class DuckMeshIoTest(unittest.TestCase):
    def sample(self):
        return dict(
            bones=["pelvis", "head"],
            positions=[(0, 0, 0), (1, 0, 0), (0, 1, 0)],
            normals=[(0, 0, -1)] * 3,
            bone_idx=[(0, 1, 0, 0), (1, 0, 0, 0), (0, 1, 0, 0)],
            weights=[(0.75, 0.25, 0, 0), (1, 0, 0, 0), (0.5, 0.5, 0, 0)],
            submeshes=[((246, 243, 236, 255), 0.35, [0, 1, 2])],
        )

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "t.duckmesh")
            duckmesh_io.write(path, **self.sample())
            back = duckmesh_io.read(path)
        self.assertEqual(back["bones"], ["pelvis", "head"])
        self.assertEqual(back["positions"][1], (1.0, 0.0, 0.0))
        self.assertEqual(back["bone_idx"][0], (0, 1, 0, 0))
        self.assertAlmostEqual(back["weights"][0][0], 0.75)
        color, smooth, indices = back["submeshes"][0]
        self.assertEqual(color, (246, 243, 236, 255))
        self.assertAlmostEqual(smooth, 0.35, places=6)
        self.assertEqual(indices, [0, 1, 2])

    def test_header_matches_the_csharp_reader(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "t.duckmesh")
            duckmesh_io.write(path, **self.sample())
            data = open(path, "rb").read()
        self.assertEqual(data[:4], b"DUCK")
        self.assertEqual(struct.unpack_from("<HHIHH", data, 4), (1, 2, 3, 1, 0))

    def test_refuses_weights_that_do_not_sum_to_one(self):
        bad = self.sample()
        bad["weights"][1] = (0.5, 0, 0, 0)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                duckmesh_io.write(os.path.join(d, "t.duckmesh"), **bad)


if __name__ == "__main__":
    unittest.main()
