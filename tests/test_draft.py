from __future__ import annotations

import unittest

from pipeline.draft import _attach_object_particle


class DraftHelperTests(unittest.TestCase):
    def test_attach_object_particle(self) -> None:
        self.assertEqual(_attach_object_particle("형성"), "형성을")
        self.assertEqual(_attach_object_particle("강화"), "강화를")
        self.assertEqual(_attach_object_particle("확보"), "확보를")


if __name__ == "__main__":
    unittest.main()
