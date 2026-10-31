"""Data-only boundary between the modeling agent, human review and Blender."""
import math
from typing import Annotated, Literal
from pydantic import Field
from .models import Model

Number = Annotated[float, Field(ge=-100, le=100, allow_inf_nan=False)]
Positive = Annotated[float, Field(gt=0.02, le=20, allow_inf_nan=False)]
Material = Literal['plaster', 'wood', 'tile', 'carpet', 'concrete', 'stone', 'metal', 'fabric']


class Point(Model):
    x: Number
    z: Number


class Position(Point):
    y: Number


class Opening(Model):
    wall: int = Field(ge=0, le=31)
    offset: float = Field(ge=0, le=100, allow_inf_nan=False)
    width: Positive
    bottom: float = Field(ge=0, le=5, allow_inf_nan=False)
    height: Positive
    kind: Literal['door', 'window', 'passage']
    sources: list[str] = Field(min_length=1, max_length=13)


class Space(Model):
    id: str = Field(pattern=r'^r[0-9]{2}$')
    label: str = Field(min_length=1, max_length=100)
    polygon: list[Point] = Field(min_length=3, max_length=32)
    height: float = Field(ge=2, le=6, allow_inf_nan=False)
    floor_material: Material
    wall_material: Material
    sources: list[str] = Field(min_length=1, max_length=13)
    openings: list[Opening] = Field(max_length=16)


class Capture(Model):
    checkpoint_id: str = Field(pattern=r'^cp[0-9]{2}$')
    room_id: str = Field(pattern=r'^r[0-9]{2}$')
    position: Position
    # Positive clockwise when looking down at the XZ plane, from world -Z.
    heading: float = Field(ge=-180, le=180, allow_inf_nan=False)
    accuracy: Literal['approximate', 'measured']


class Fixture(Model):
    room_id: str
    kind: Literal['cabinet', 'upper_cabinet', 'counter', 'sink', 'stove', 'fridge',
                  'toilet', 'bathtub', 'shower', 'bed', 'sofa', 'table', 'chair', 'shelf']
    position: Position  # bottom-center, not center of the object
    width: Positive
    depth: Positive
    height: Positive
    rotation: float = Field(ge=-180, le=180, allow_inf_nan=False)
    material: Material
    sources: list[str] = Field(min_length=1, max_length=12)
    evidence: str = Field(min_length=1, max_length=300)


class HousePlan(Model):
    status: Literal['needs_clarification', 'provisional', 'ready']
    scale: Literal['assumed', 'measured']
    scale_evidence: str = Field(max_length=500)
    summary: str = Field(min_length=1, max_length=1500)
    questions: list[str] = Field(max_length=8)
    assumptions: list[str] = Field(max_length=20)
    spaces: list[Space] = Field(max_length=12)
    captures: list[Capture] = Field(max_length=12)
    fixtures: list[Fixture] = Field(max_length=96)


def cross(a, b, c):
    return (b.x-a.x)*(c.z-a.z)-(b.z-a.z)*(c.x-a.x)


def on_edge(p, a, b):
    return (abs(cross(a, b, p)) < 1e-6 and min(a.x,b.x)-1e-6 <= p.x <= max(a.x,b.x)+1e-6
            and min(a.z,b.z)-1e-6 <= p.z <= max(a.z,b.z)+1e-6)


def inside(p, poly, boundary=True):
    result = False
    for a, b in zip(poly, poly[1:]+poly[:1]):
        if on_edge(p, a, b):
            return boundary
        if (a.z > p.z) != (b.z > p.z) and p.x < (b.x-a.x)*(p.z-a.z)/(b.z-a.z)+a.x:
            result = not result
    return result


def proper_intersection(a, b, c, d):
    return cross(a,b,c)*cross(a,b,d) < -1e-9 and cross(c,d,a)*cross(c,d,b) < -1e-9


def validate_plan(value, rooms, assets):
    plan = HousePlan.model_validate(value)
    known = {a['id'] for a in assets if a['kind'] in ('panorama', 'floorplan')}
    photos = {a['id'] for a in assets if a['kind'] == 'panorama'}
    def sources(ids, allowed=known):
        if not set(ids) <= allowed:
            raise ValueError('Modeling plan cites unknown evidence')
    if plan.status == 'needs_clarification':
        if not plan.questions:
            raise ValueError('Unresolved layout needs a specific clarification question')
        # Still validate any partial geometry; completeness is required only for buildable plans.
    elif plan.questions or not plan.spaces:
        raise ValueError('Resolve layout questions before approving the model')
    if plan.scale == 'assumed' and plan.status == 'ready':
        raise ValueError('Assumed scale must remain provisional')
    if plan.scale == 'measured' and not plan.scale_evidence.strip():
        raise ValueError('Measured scale requires a supplied dimension reference')
    spaces = {s.id:s for s in plan.spaces}
    if len(spaces) != len(plan.spaces):
        raise ValueError('Duplicate room ID')
    for s in plan.spaces:
        sources(s.sources)
        poly = s.polygon
        edges = list(zip(poly, poly[1:]+poly[:1]))
        area = abs(sum(a.x*b.z-b.x*a.z for a,b in edges))/2
        if area < 0.5 or area > 1600 or any(math.hypot(a.x-b.x,a.z-b.z) < .1 for a,b in edges):
            raise ValueError('Room footprint has invalid size')
        for i,(a,b) in enumerate(edges):
            for j,(c,d) in enumerate(edges):
                if j <= i or j == i+1 or (i == 0 and j == len(edges)-1):
                    continue
                if proper_intersection(a,b,c,d) or any((on_edge(c,a,b),on_edge(d,a,b),on_edge(a,c,d),on_edge(b,c,d))):
                    raise ValueError('Room footprint intersects itself')
        for op in s.openings:
            sources(op.sources)
            if op.wall >= len(poly):
                raise ValueError('Opening references an unknown wall')
            a,b = edges[op.wall]
            if op.offset+op.width > math.hypot(a.x-b.x,a.z-b.z)+1e-6 or op.bottom+op.height > s.height:
                raise ValueError('Opening lies outside its wall')
        for i,op in enumerate(s.openings):
            if any(other.wall == op.wall and max(op.offset,other.offset) < min(op.offset+op.width,other.offset+other.width)
                   for other in s.openings[i+1:]):
                raise ValueError('Overlapping openings')
    for i,s in enumerate(plan.spaces):
        for t in plan.spaces[i+1:]:
            for si,(a,b) in enumerate(zip(s.polygon,s.polygon[1:]+s.polygon[:1])):
                for ti,(c,d) in enumerate(zip(t.polygon,t.polygon[1:]+t.polygon[:1])):
                    if abs(cross(a,b,c))>1e-6 or abs(cross(a,b,d))>1e-6:
                        continue
                    length=math.hypot(b.x-a.x,b.z-a.z)
                    def along(p): return ((p.x-a.x)*(b.x-a.x)+(p.z-a.z)*(b.z-a.z))/length
                    left,right=sorted((along(c),along(d)))
                    if min(length,right)-max(0,left)<1e-5:
                        continue
                    if abs(left)>1e-5 or abs(right-length)>1e-5:
                        raise ValueError('Split adjacent polygon edges so shared walls match exactly')
                    def openings(space,index,reverse=False):
                        return sorted((round(length-o.offset-o.width if reverse else o.offset,4),
                            round(o.width,4),round(o.bottom,4),round(o.height,4),o.kind)
                            for o in space.openings if o.wall==index)
                    if openings(s,si)!=openings(t,ti,along(c)>along(d)):
                        raise ValueError('Shared walls must agree on door and window openings')
            # Interior vertices, crossing edges and interior edge midpoints catch identical/partially aligned rooms.
            samples = s.polygon + [Point(x=(a.x+b.x)/2,z=(a.z+b.z)/2) for a,b in zip(s.polygon,s.polygon[1:]+s.polygon[:1])]
            samples2 = t.polygon + [Point(x=(a.x+b.x)/2,z=(a.z+b.z)/2) for a,b in zip(t.polygon,t.polygon[1:]+t.polygon[:1])]
            identical = {(p.x,p.z) for p in s.polygon} == {(p.x,p.z) for p in t.polygon}
            if identical or any(inside(p,t.polygon,False) for p in samples) or any(inside(p,s.polygon,False) for p in samples2) or any(
                proper_intersection(a,b,c,d) for a,b in zip(s.polygon,s.polygon[1:]+s.polygon[:1])
                for c,d in zip(t.polygon,t.polygon[1:]+t.polygon[:1])):
                raise ValueError('Room floors overlap')
    captures = {c.checkpoint_id:c for c in plan.captures}
    ids = {r['checkpoint_id'] for r in rooms}
    if len(captures) != len(plan.captures) or not set(captures) <= ids:
        raise ValueError('Invalid or duplicate capture ID')
    if plan.status != 'needs_clarification' and (set(captures) != ids or {c.room_id for c in plan.captures} != set(spaces)):
        raise ValueError('Assign every capture once and cover every room')
    for c in plan.captures:
        if c.room_id not in spaces or not inside(c.position, spaces[c.room_id].polygon,False) or not .2 < c.position.y < spaces[c.room_id].height:
            raise ValueError('Capture lies outside its room')
        if plan.scale == 'assumed' and c.accuracy == 'measured':
            raise ValueError('Assumed scale cannot have measured camera positions')
    for f in plan.fixtures:
        sources(f.sources,photos)
        if f.room_id not in spaces or f.position.y < 0 or f.position.y+f.height > spaces[f.room_id].height+.01:
            raise ValueError('Fixture lies outside its room')
        theta = math.radians(f.rotation)
        for dx,dz in [(-f.width/2,-f.depth/2),(-f.width/2,f.depth/2),(f.width/2,-f.depth/2),(f.width/2,f.depth/2)]:
            p = Point(x=f.position.x+dx*math.cos(theta)+dz*math.sin(theta), z=f.position.z-dx*math.sin(theta)+dz*math.cos(theta))
            if not inside(p,spaces[f.room_id].polygon):
                raise ValueError('Fixture footprint lies outside its room')
    return plan.model_dump()
