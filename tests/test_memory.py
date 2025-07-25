import asyncio
import tempfile
import unittest

from ai_trader.memory import Memory


class MemoryTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mem = Memory(file_path=f"{self.tmp.name}/trades.csv")

    def tearDown(self):
        self.tmp.cleanup()

    def test_record_and_load(self):
        info = {"timestamp": 1, "side": "buy", "price": 1.0, "qty": 1.0, "pnl": 0.0}
        self.mem.record(info)
        rows = self.mem.load()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["side"], "buy")

    def test_async_record(self):
        info = {"timestamp": 1, "side": "buy", "price": 1.0, "qty": 1.0, "pnl": 0.0}
        asyncio.run(self.mem.async_record(info))
        rows = asyncio.run(self.mem.async_load())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["price"], "1.0")


if __name__ == "__main__":
    unittest.main()
