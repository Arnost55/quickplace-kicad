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

    def test_edge_cuts_fallback_selects_unique_enclosing_rectangle(self):
        from quickplace.adapter import _enclosing_rect_outline
        from quickplace.engine import PlacementError
        board=pcbnew.BOARD()
        for x,y in ((20,20),(80,60)):
            fp=pcbnew.FOOTPRINT(board)
            fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x),pcbnew.FromMM(y)))
            board.Add(fp)
        def add_shape(kind,start,end):
            item=pcbnew.PCB_SHAPE(board)
            item.SetShape(kind); item.SetLayer(pcbnew.Edge_Cuts)
            item.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(start[0]),pcbnew.FromMM(start[1])))
            item.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(end[0]),pcbnew.FromMM(end[1])))
            item.SetWidth(pcbnew.FromMM(0.05)); board.Add(item)
        add_shape(pcbnew.SHAPE_T_RECT,(0,0),(100,80))
        add_shape(pcbnew.SHAPE_T_RECT,(120,0),(180,60))
        add_shape(pcbnew.SHAPE_T_SEGMENT,(0,0),(100,0))
        outline=_enclosing_rect_outline(board,list(board.GetFootprints()))
        self.assertEqual(outline,((0.,0.),(100.,0.),(100.,80.),(0.,80.)))
        add_shape(pcbnew.SHAPE_T_SEGMENT,(10,10),(90,10))
        with self.assertRaises(PlacementError): _enclosing_rect_outline(board,list(board.GetFootprints()))

if __name__=='__main__': unittest.main()
