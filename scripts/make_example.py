"""Generate the example .kicad_pcb using KiCad's bundled Python."""
from pathlib import Path
import pcbnew as k

out=Path(__file__).resolve().parents[1]/'examples'/'quickplace_demo.kicad_pcb'
b=k.BOARD()
pts=((0,0),(80,0),(80,50),(0,50))
for a,c in zip(pts,pts[1:]+pts[:1]):
    edge=k.PCB_SHAPE(b); edge.SetShape(k.SHAPE_T_SEGMENT); edge.SetLayer(k.Edge_Cuts)
    edge.SetStart(k.VECTOR2I(k.FromMM(a[0]),k.FromMM(a[1])))
    edge.SetEnd(k.VECTOR2I(k.FromMM(c[0]),k.FromMM(c[1]))); edge.SetWidth(k.FromMM(0.05)); b.Add(edge)
for i in range(10):
    fp=k.FOOTPRINT(b); fp.SetReference(f'R{i+1}'); fp.SetValue('10k')
    fp.SetPosition(k.VECTOR2I(k.FromMM(8+i*3),k.FromMM(9)))
    for j in range(2):
        pad=k.PAD(fp); pad.SetName(str(j+1)); pad.SetShape(k.PAD_SHAPE_RECT); pad.SetAttribute(k.PAD_ATTRIB_SMD)
        pad.SetLayerSet(k.LSET.FrontMask()); pad.SetSize(k.VECTOR2I(k.FromMM(0.7),k.FromMM(0.7)))
        pad.SetPosition(k.VECTOR2I(k.FromMM(8+i*3+j),k.FromMM(9)))
        fp.Add(pad)
    b.Add(fp)
k.SaveBoard(str(out),b)
print(out)
