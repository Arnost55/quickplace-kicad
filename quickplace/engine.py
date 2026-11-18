"""Dependency-free, deterministic placement planner; all dimensions are millimetres."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from math import cos, sin, radians, hypot
from time import perf_counter
import random

Point = tuple[float, float]


@dataclass(frozen=True)
class Outline:
    outer: tuple[Point, ...]
    holes: tuple[tuple[Point, ...], ...] = ()


@dataclass(frozen=True)
class Part:
    ref: str
    x: float
    y: float
    width: float
    height: float
    side: str = "front"
    angle: int = 0
    fixed: bool = False
    connector: bool = False
    pads: tuple[tuple[str, float, float], ...] = ()
    rotations: tuple[int, ...] = (0, 90, 180, 270)
    courtyard: tuple[Point, ...] = ()


@dataclass(frozen=True)
class Obstacle:
    polygon: tuple[Point, ...]
    side: str = "both"


@dataclass
class Layout:
    parts: list[Part]
    outline: Outline
    obstacles: list[Obstacle] = field(default_factory=list)


@dataclass(frozen=True)
class Settings:
    edge: float = 0.5
    spacing: float = 0.5
    budget_ms: int = 150
    mode: str = "instant"
    optimize_ms: int = 500


@dataclass
class Result:
    positions: dict[str, tuple[float, float, int]]
    elapsed_ms: float
    score_before: float
    score_after: float
    warnings: list[str] = field(default_factory=list)


class PlacementError(ValueError):
    pass


def edges(poly):
    return zip(poly, poly[1:] + poly[:1])


def point_in_polygon(p: Point, poly: tuple[Point, ...]) -> bool:
    if len(poly) < 3:
        return False
    x, y = p
    inside = False
    for (ax, ay), (bx, by) in edges(poly):
        cross = (x-ax)*(by-ay)-(y-ay)*(bx-ax)
        if abs(cross) < 1e-8 and min(ax,bx)-1e-8 <= x <= max(ax,bx)+1e-8 and min(ay,by)-1e-8 <= y <= max(ay,by)+1e-8:
            return True
        if (ay > y) != (by > y) and x < (bx-ax)*(y-ay)/(by-ay)+ax:
            inside = not inside
    return inside


def segments_intersect(a,b,c,d):
    def cross(p,q,r): return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    s1,s2,s3,s4 = cross(a,b,c),cross(a,b,d),cross(c,d,a),cross(c,d,b)
    if s1*s2 < -1e-12 and s3*s4 < -1e-12:
        return True
    return any(abs(s)<1e-9 and min(p[0],q[0])-1e-9 <= r[0] <= max(p[0],q[0])+1e-9 and min(p[1],q[1])-1e-9 <= r[1] <= max(p[1],q[1])+1e-9 for s,p,q,r in ((s1,a,b,c),(s2,a,b,d),(s3,c,d,a),(s4,c,d,b)))


def segment_distance(a,b,c,d):
    if segments_intersect(a,b,c,d): return 0.0
    def distance(p,u,v):
        dx,dy=v[0]-u[0],v[1]-u[1]
        t=max(0.,min(1.,((p[0]-u[0])*dx+(p[1]-u[1])*dy)/(dx*dx+dy*dy))) if dx*dx+dy*dy else 0.
        return hypot(p[0]-u[0]-t*dx,p[1]-u[1]-t*dy)
    return min(distance(a,c,d),distance(b,c,d),distance(c,a,b),distance(d,a,b))


def polygons_overlap(a,b,clearance=0.):
    if max(x for x,y in a)+clearance <= min(x for x,y in b) or max(x for x,y in b)+clearance <= min(x for x,y in a) or max(y for x,y in a)+clearance <= min(y for x,y in b) or max(y for x,y in b)+clearance <= min(y for x,y in a): return False
    if any(point_in_polygon(p,b) for p in a) or any(point_in_polygon(p,a) for p in b): return True
    return any(segment_distance(p,q,r,s) < clearance-1e-8 for p,q in edges(a) for r,s in edges(b)) or any(segments_intersect(p,q,r,s) for p,q in edges(a) for r,s in edges(b))


def shape(part: Part) -> tuple[Point, ...]:
    local = part.courtyard or ((-part.width/2,-part.height/2),(part.width/2,-part.height/2),(part.width/2,part.height/2),(-part.width/2,part.height/2))
    c,s=cos(radians(part.angle)),sin(radians(part.angle))
    return tuple((part.x+c*x-s*y,part.y+s*x+c*y) for x,y in local)


def contained(poly, outline, clearance):
    if not all(point_in_polygon(p,outline) for p in poly): return False
    if any(segments_intersect(a,b,c,d) for a,b in edges(poly) for c,d in edges(outline)): return False
    return not any(segment_distance(a,b,c,d)<clearance-1e-8 for a,b in edges(poly) for c,d in edges(outline))


def _valid_polygon(poly):
    return len(poly)>=3 and abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in edges(poly)))>1e-6 and not any(segments_intersect(a,b,c,d) for i,(a,b) in enumerate(edges(poly)) for j,(c,d) in enumerate(edges(poly)) if j>i+1 and not(i==0 and j==len(poly)-1))


def valid_outline(outline):
    return (_valid_polygon(outline.outer)
            and all(_valid_polygon(h) and all(point_in_polygon(v,outline.outer) for v in h)
                    and not any(segments_intersect(a,b,c,d) for a,b in edges(h) for c,d in edges(outline.outer)) for h in outline.holes)
            and all(not polygons_overlap(a,b) for i,a in enumerate(outline.holes) for b in outline.holes[i+1:]))


def validate(layout: Layout, settings: Settings, *, check_fixed=False):
    if not valid_outline(layout.outline):
        raise PlacementError("Missing or invalid Edge.Cuts outline")
    if settings.edge<0 or settings.spacing<0 or settings.budget_ms<0 or settings.optimize_ms<0:
        raise PlacementError("Clearances and budgets must be non-negative")
    refs=set()
    for part in layout.parts:
        if part.ref in refs or part.width<=0 or part.height<=0 or part.side not in ("front","back") or part.angle%90:
            raise PlacementError(f"Invalid footprint data: {part.ref}")
        refs.add(part.ref)
        if part.fixed and not check_fixed: continue
        poly=shape(part)
        if not contained(poly,layout.outline.outer,settings.edge):
            raise PlacementError(f"Footprint outside board or edge clearance: {part.ref}")
        for hole in layout.outline.holes:
            if polygons_overlap(poly,hole,settings.edge) or any(point_in_polygon(p,poly) for p in hole):
                raise PlacementError(f"Footprint overlaps board cutout: {part.ref}")
        for obs in layout.obstacles:
            if obs.side in (part.side,"both") and polygons_overlap(poly,obs.polygon,settings.spacing):
                raise PlacementError(f"Footprint intersects obstacle: {part.ref}")
        for other in layout.parts:
            if other.ref==part.ref or other.side!=part.side: continue
            if polygons_overlap(poly,shape(other),settings.spacing):
                raise PlacementError(f"Footprint collision: {part.ref} / {other.ref}")


def _nets(parts):
    nets={}
    for p in parts:
        for net,dx,dy in p.pads:
            if net: nets.setdefault(net,[]).append((p,dx,dy))
    return nets


def score(parts):
    total=0.
    for pads in _nets(parts).values():
        if len(pads)<2: continue
        xy=[]
        for part,dx,dy in pads:
            c,s=cos(radians(part.angle)),sin(radians(part.angle))
            xy.append((part.x+c*dx-s*dy,part.y+s*dx+c*dy))
        total += max(x for x,y in xy)-min(x for x,y in xy)+max(y for x,y in xy)-min(y for x,y in xy)
    return total


def _candidate_ok(candidate, placed, outline, obstacles, settings):
    poly=shape(candidate)
    if not contained(poly,outline.outer,settings.edge): return False
    if any(polygons_overlap(poly,h,settings.edge) or any(point_in_polygon(v,poly) for v in h) for h in outline.holes): return False
    if any(o.side in (candidate.side,"both") and polygons_overlap(poly,o.polygon,settings.spacing) for o in obstacles): return False
    return not any(p.side==candidate.side and polygons_overlap(poly,shape(p),settings.spacing) for p in placed)


def plan(layout: Layout, settings: Settings = Settings()) -> Result:
    start=perf_counter()
    if settings.mode not in ("instant","optimize"): raise PlacementError("Unknown placement mode")
    if not valid_outline(layout.outline): raise PlacementError("Missing or invalid Edge.Cuts outline")
    if settings.edge<0 or settings.spacing<0 or settings.budget_ms<0 or settings.optimize_ms<0: raise PlacementError("Invalid clearance or time budget")
    refs=[p.ref for p in layout.parts]
    if len(refs)!=len(set(refs)) or any(p.width<=0 or p.height<=0 or p.side not in ("front","back") or p.angle%90 for p in layout.parts): raise PlacementError("Malformed footprint data")
    xmin=min(x for x,y in layout.outline.outer); xmax=max(x for x,y in layout.outline.outer)
    ymin=min(y for x,y in layout.outline.outer); ymax=max(y for x,y in layout.outline.outer)
    fixed=[p for p in layout.parts if p.fixed]
    moving=[p for p in layout.parts if not p.fixed]
    before=score(layout.parts)
    nets=_nets(layout.parts)
    adjacency={p.ref:{} for p in layout.parts}
    for pads in nets.values():
        refs_on_net=set(p.ref for p,_,_ in pads)
        for a in refs_on_net:
            for b in refs_on_net-{a}: adjacency[a][b]=adjacency[a].get(b,0)+1
    moving.sort(key=lambda p:(-p.width*p.height,-len(adjacency[p.ref]),p.ref))
    placed=list(fixed); warnings=[]
    for p in moving:
        neighbors=[q for q in placed if q.ref in adjacency[p.ref]]
        if neighbors:
            weight=sum(adjacency[p.ref][q.ref] for q in neighbors)
            target=(sum(q.x*adjacency[p.ref][q.ref] for q in neighbors)/weight,sum(q.y*adjacency[p.ref][q.ref] for q in neighbors)/weight)
        else: target=((xmin+xmax)/2,(ymin+ymax)/2)
        step=max(0.8,min(p.width,p.height)/2+settings.spacing)
        best=None; best_cost=float('inf')
        rotations=p.rotations or (p.angle,)
        max_ring=max(2,int(max(xmax-xmin,ymax-ymin)/step)+2)
        for ring in range(max_ring):
            points=[target] if ring==0 else []
            if ring:
                for k in range(-ring,ring+1):
                    points.extend(((target[0]+k*step,target[1]-ring*step),(target[0]+k*step,target[1]+ring*step),(target[0]-ring*step,target[1]+k*step),(target[0]+ring*step,target[1]+k*step)))
            for x,y in points:
                if x<xmin or x>xmax or y<ymin or y>ymax: continue
                for angle in rotations:
                    candidate=replace(p,x=x,y=y,angle=angle%360)
                    if not _candidate_ok(candidate,placed,layout.outline,layout.obstacles,settings): continue
                    cost=sum(w*hypot(candidate.x-q.x,candidate.y-q.y) for q in neighbors for w in (adjacency[p.ref][q.ref],))
                    cost+=0.01*hypot(x-target[0],y-target[1])
                    if p.connector: cost+=0.3*min(x-xmin,xmax-x,y-ymin,ymax-y)
                    if cost<best_cost-1e-9: best,best_cost=candidate,cost
            if best is not None: break
        if best is None: raise PlacementError(f"Insufficient valid board space for {p.ref}; board unchanged")
        placed.append(best)
    if settings.mode=="optimize" and moving:
        limit=perf_counter()+settings.optimize_ms/1000
        rng=random.Random(0)
        indices=[i for i,p in enumerate(placed) if not p.fixed]
        current=score(placed)
        iterations=0
        while perf_counter()<limit and iterations<max(100,len(moving)*40):
            i=indices[iterations%len(indices)]
            old=placed[i]
            radius=max(old.width,old.height,1.0)*(.5 if iterations%2 else 1.0)
            candidate=replace(old,x=old.x+rng.choice((-1,0,1))*radius,y=old.y+rng.choice((-1,0,1))*radius,angle=rng.choice(old.rotations or (old.angle,)))
            if _candidate_ok(candidate,placed[:i]+placed[i+1:],layout.outline,layout.obstacles,settings):
                placed[i]=candidate
                candidate_score=score(placed)
                if candidate_score<current: current=candidate_score
                else: placed[i]=old
            iterations+=1
    result_layout=Layout(placed,layout.outline,layout.obstacles)
    validate(result_layout,settings)
    return Result({p.ref:(p.x,p.y,p.angle) for p in placed if not p.fixed},(perf_counter()-start)*1000,before,score(placed),warnings)
