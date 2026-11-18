"""Real pcbnew binding smoke tests; skipped under ordinary Python."""
import unittest
from pathlib import Path
try:
    import pcbnew
except ImportError:
    pcbnew=None

@unittest.skipIf(pcbnew is None,'KiCad bundled pcbnew unavailable')
class KiCadTests(unittest.TestCase):
    def test_generated_board_adapter_and_plan(self):
        from quickplace.adapter import read_board
        from quickplace.engine import plan
        path=Path(__file__).resolve().parents[1]/'examples'/'quickplace_demo.kicad_pcb'
        board=pcbnew.LoadBoard(str(path))
        self.assertIsNotNone(board)
        layout,footprints,warnings=read_board(board)
        self.assertEqual(len(layout.parts),10)
        self.assertEqual(len(plan(layout).positions),10)

    def test_empty_board_fails_safely(self):
        from quickplace.adapter import read_board
        from quickplace.engine import PlacementError
        with self.assertRaises(PlacementError): read_board(pcbnew.BOARD())

if __name__=='__main__': unittest.main()
