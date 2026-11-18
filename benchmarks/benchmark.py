"""Reproducible synthetic benchmark (run with either Python or bundled KiCad Python)."""
import json
from dataclasses import replace
from pathlib import Path
import sys
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from quickplace.engine import Layout, Outline, Part, Settings, plan


def make_board(n):
    parts=[]
    for i in range(n):
        pads=((f'N{i//2}',0.,0.),(f'N{(i+1)//2}',0.5,0.))
        parts.append(Part(f'R{i+1}',-10.,-10.,2.,1.5,pads=pads))
    return Layout(parts,Outline(((0.,0.),(60.,0.),(60.,60.),(0.,60.))))


if __name__=='__main__':
    for n in (10,20,50,100):
        board=make_board(n)
        start=perf_counter(); result=plan(board,Settings()); elapsed=(perf_counter()-start)*1000
        print(json.dumps({'footprints':n,'wall_ms':round(elapsed,2),'planner_ms':round(result.elapsed_ms,2),'placed':len(result.positions),'before':round(result.score_before,2),'after':round(result.score_after,2)}))
