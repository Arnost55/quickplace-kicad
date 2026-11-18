"""Conservative KiCad 10 pcbnew bridge. Unsupported geometry aborts without edits."""
import pcbnew as k
from .engine import Outline, Part, Obstacle, Layout, PlacementError, shape, polygons_overlap


def mm(value): return k.ToMM(value)
def xy(v): return (mm(v.x),mm(v.y))
def box(obj):
    b=obj.GetBoundingBox()
    return ((mm(b.GetX()),mm(b.GetY())),(mm(b.GetRight()),mm(b.GetY())),(mm(b.GetRight()),mm(b.GetBottom())),(mm(b.GetX()),mm(b.GetBottom())))


def polygon(chain): return tuple(xy(chain.CPoint(i)) for i in range(chain.PointCount()))


def read_board(board):
    if board is None: raise PlacementError('No PCB Editor board is open')
    for drawing in board.GetDrawings():
        if drawing.GetLayer()==k.Edge_Cuts and drawing.GetShape() not in (k.SHAPE_T_SEGMENT,k.SHAPE_T_RECT,k.SHAPE_T_RECTANGLE,k.SHAPE_T_POLY):
            raise PlacementError('Curved Edge.Cuts geometry is not safely supported')
    poly=k.SHAPE_POLY_SET()
    if not board.GetBoardPolygonOutlines(poly,False) or poly.OutlineCount()!=1:
        raise PlacementError('Edge.Cuts must form exactly one closed, valid outer board outline')
    outer=polygon(poly.COutline(0))
    holes=tuple(polygon(poly.CHole(0,i)) for i in range(poly.HoleCount(0)))
    outline=Outline(outer,holes)
    footprints=list(board.GetFootprints())
    items=[]; warnings=[]
    tracks=list(board.GetTracks())
    if any(isinstance(t,k.PCB_ARC) for t in tracks):
        raise PlacementError('Existing curved tracks cannot be conservatively checked; board unchanged')
    for fp in footprints:
        ref=fp.GetReference()
        if not ref: raise PlacementError('A footprint has no reference')
        front=fp.GetLayer()==k.F_Cu
        if not front and fp.GetLayer()!=k.B_Cu: raise PlacementError(f'Unsupported footprint layer: {ref}')
        side='front' if front else 'back'
        pos=xy(fp.GetPosition()); angle=round(fp.GetOrientationDegrees())%360
        if abs(fp.GetOrientationDegrees()-round(fp.GetOrientationDegrees()))>1e-5 or angle%90:
            raise PlacementError(f'Non-orthogonal footprint orientation requires explicit geometry support: {ref}')
        courtyard=fp.GetCourtyard(k.F_CrtYd if front else k.B_CrtYd)
        if courtyard.OutlineCount()>1 or (courtyard.OutlineCount() and courtyard.HoleCount(0)):
            raise PlacementError(f'Unsupported complex courtyard on {ref}')
        if courtyard.OutlineCount():
            world=polygon(courtyard.COutline(0))
            from math import sin,cos,radians
            c,s=cos(radians(angle)),sin(radians(angle))
            local=tuple((c*(x-pos[0])+s*(y-pos[1]),-s*(x-pos[0])+c*(y-pos[1])) for x,y in world)
            if len(local)<3: raise PlacementError(f'Invalid courtyard: {ref}')
            bounds=box(fp)
        else:
            bounds=box(fp)
            from math import sin,cos,radians
            c,s=cos(radians(angle)),sin(radians(angle))
            local=tuple((c*(x-pos[0])+s*(y-pos[1]),-s*(x-pos[0])+c*(y-pos[1])) for x,y in bounds)
            warnings.append(f'{ref}: no courtyard; full footprint bounding box used')
        width=max(x for x,y in bounds)-min(x for x,y in bounds)
        height=max(y for x,y in bounds)-min(y for x,y in bounds)
        if width<=0 or height<=0: raise PlacementError(f'Invalid footprint bounds: {ref}')
        pads=[]; routed=False
        for pad in fp.Pads():
            pp=xy(pad.GetPosition()); dx,dy=pp[0]-pos[0],pp[1]-pos[1]
            from math import sin,cos,radians
            c,s=cos(radians(angle)),sin(radians(angle))
            pads.append((pad.GetNetname(),c*dx+s*dy,-s*dx+c*dy))
            for track in tracks:
                if pad.GetNetCode()>0 and pad.GetNetCode()==track.GetNetCode() and any(track.IsOnLayer(layer) and pad.IsOnLayer(layer) for layer in (k.F_Cu,k.B_Cu)):
                    tx,ty=xy(track.GetStart()); ex,ey=xy(track.GetEnd())
                    from .engine import segment_distance
                    if segment_distance(pp,pp,(tx,ty),(ex,ey)) < max(mm(track.GetWidth())/2,0.05)+0.2: routed=True
        fixed=bool(fp.IsLocked() or routed)
        if routed: warnings.append(f'{ref}: connected to routed copper; kept fixed')
        items.append(Part(ref,pos[0],pos[1],width,height,side,angle,fixed,ref[0].upper()=='J',tuple(pads),(0,90,180,270),local))
    obstacles=[]
    for part,fp in zip(items,footprints):
        if part.fixed:
            for pad in fp.Pads():
                if pad.GetAttribute() in (k.PAD_ATTRIB_PTH,k.PAD_ATTRIB_NPTH):
                    obstacles.append(Obstacle(box(pad),'both'))
    for track in tracks:
        if isinstance(track,k.PCB_VIA): side='both'
        else: side='front' if track.GetLayer()==k.F_Cu else 'back' if track.GetLayer()==k.B_Cu else 'both'
        obstacles.append(Obstacle(box(track),side))
    for zone in board.Zones():
        if zone.GetIsRuleArea():
            zp=zone.Outline()
            if zp.OutlineCount()<1: raise PlacementError('Unrecognized rule-area keepout')
            for i in range(zp.OutlineCount()): obstacles.append(Obstacle(polygon(zp.COutline(i)),'both'))
    for drawing in board.GetDrawings():
        if drawing.GetLayer()==k.Edge_Cuts: continue
        if drawing.GetLayer() in (k.F_CrtYd,k.B_CrtYd): continue
        if drawing.GetClass()=='PCB_SHAPE' and drawing.GetLayer() in (k.F_Cu,k.B_Cu):
            obstacles.append(Obstacle(box(drawing),'front' if drawing.GetLayer()==k.F_Cu else 'back'))
    return Layout(items,outline,obstacles),dict(zip((p.ref for p in items),footprints)),warnings


def apply(board,footprints,result):
    original={ref:(fp.GetPosition(),fp.GetOrientationDegrees()) for ref,fp in footprints.items() if ref in result.positions}
    try:
        for ref,(x,y,angle) in result.positions.items():
            fp=footprints[ref]
            fp.SetOrientationDegrees(angle)
            fp.SetPosition(k.VECTOR2I(k.FromMM(x),k.FromMM(y)))
        k.Refresh()
    except Exception:
        for ref,(pos,angle) in original.items():
            footprints[ref].SetOrientationDegrees(angle)
            footprints[ref].SetPosition(pos)
        k.Refresh()
        raise
