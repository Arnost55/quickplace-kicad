import unittest
from dataclasses import replace
from quickplace.engine import (Outline, Part, Obstacle, Layout, Settings, PlacementError,
                               plan, validate, shape, point_in_polygon, polygons_overlap)


def board(n=10):
    parts=[]
    for i in range(n):
        pads=((f'N{i//2}',0.0,0.0), (f'N{(i+1)//2}',0.6,0.0))
        parts.append(Part(f'U{i}',-10.0,-10.0,2.0,1.5,pads=pads))
    return Layout(parts, Outline(((0.,0.),(60.,0.),(60.,60.),(0.,60.))))


class EngineTests(unittest.TestCase):
    def test_geometry(self):
        square=((0.,0.),(5.,0.),(5.,5.),(0.,5.))
        self.assertTrue(point_in_polygon((2,2),square))
        self.assertFalse(point_in_polygon((6,2),square))
        self.assertTrue(polygons_overlap(square,((4.,4.),(6.,4.),(6.,6.),(4.,6.))))
        self.assertFalse(polygons_overlap(square,((7.,7.),(9.,7.),(9.,9.),(7.,9.))))

    def test_sizes(self):
        for n in (10,20,50,100):
            with self.subTest(n=n):
                b=board(n)
                result=plan(b,Settings(budget_ms=150))
                self.assertEqual(len(result.positions),n)
                validate(Layout([replace(p,x=result.positions[p.ref][0],y=result.positions[p.ref][1],angle=result.positions[p.ref][2]) for p in b.parts],b.outline),Settings())

    def test_fixed_and_obstacles(self):
        b=board(10)
        b.parts[0]=replace(b.parts[0],x=8,y=8,fixed=True)
        b.obstacles.append(Obstacle(((20.,20.),(30.,20.),(30.,30.),(20.,30.))))
        result=plan(b)
        self.assertNotIn('U0',result.positions)
        self.assertTrue(all(not polygons_overlap(shape(replace(p,x=result.positions[p.ref][0],y=result.positions[p.ref][1])),b.obstacles[0].polygon) for p in b.parts[1:]))

    def test_irregular_cutout_and_sides(self):
        b=board(8)
        b.outline=Outline(((0.,0.),(60.,0.),(60.,15.),(25.,15.),(25.,60.),(0.,60.)),(((5.,5.),(12.,5.),(12.,12.),(5.,12.)),))
        b.parts[1]=replace(b.parts[1],side='back')
        result=plan(b)
        self.assertEqual(len(result.positions),8)

    def test_no_outline_and_no_space(self):
        b=board(1)
        b.outline=Outline(())
        with self.assertRaises(PlacementError): plan(b)
        b.outline=Outline(((0.,0.),(1.,0.),(1.,1.),(0.,1.)))
        with self.assertRaises(PlacementError): plan(b)

    def test_disconnected_missing_courtyard_and_optimize(self):
        b=board(6)
        b.parts=[replace(p,pads=()) for p in b.parts]
        self.assertEqual(len(plan(b,Settings(mode='optimize',optimize_ms=10)).positions),6)

    def test_malformed(self):
        b=board(2)
        b.parts[1]=replace(b.parts[1],ref='U0')
        with self.assertRaises(PlacementError): plan(b)
        b.parts[1]=replace(b.parts[1],ref='U1',width=-1)
        with self.assertRaises(PlacementError): plan(b)
        b=board(1)
        b.outline=Outline(((0.,0.),(10.,10.),(0.,10.),(10.,0.)))
        with self.assertRaises(PlacementError): plan(b)


if __name__=='__main__': unittest.main()
