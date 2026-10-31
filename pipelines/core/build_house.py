"""Run inside Blender. No network, generated code or external assets are used."""
import json
import math
from pathlib import Path
import random
import sys
import bpy

spec_path, out_path = sys.argv[sys.argv.index('--')+1:]
plan = json.loads(Path(spec_path).read_text(encoding='utf-8'))
out = Path(out_path)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene['coordinate_contract'] = 'GLB: meters, Y up. Blender: (X,-Z,Y). Floor top 0.'
scene['scale_accuracy'] = plan['scale']
scene['plan_summary'] = plan['summary']

COLORS = {'plaster':(.78,.76,.70), 'wood':(.53,.31,.14), 'tile':(.73,.72,.66),
          'carpet':(.48,.44,.38), 'concrete':(.47,.48,.46), 'stone':(.65,.64,.59),
          'metal':(.46,.49,.52), 'fabric':(.55,.57,.56), 'white':(.88,.87,.82),
          'dark':(.045,.055,.06), 'glass':(.52,.72,.77)}
materials = {}


def material(name):
    if name in materials:
        return materials[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*COLORS[name],1)
    bsdf.inputs['Roughness'].default_value = .3 if name in ('metal','glass','white') else .72
    bsdf.inputs['Metallic'].default_value = .8 if name == 'metal' else 0
    # Deterministic authored maps travel inside GLB, unlike procedural-only shaders.
    if name in ('wood','tile','carpet','concrete','stone','fabric'):
        size = 128
        rng = random.Random(name)
        pixels = []
        for y in range(size):
            for x in range(size):
                noise = rng.uniform(-.04,.04)
                if name == 'wood':
                    noise += .07*math.sin(x*.9+math.sin(y*.09)*1.8)
                    noise += -.14 if x%32 == 0 or (y+(x//32)*37)%128 == 0 else 0
                elif name == 'tile':
                    noise = -.16 if x%64<2 or y%64<2 else noise*.2
                elif name == 'stone':
                    noise += .035*math.sin(x*.12+y*.19)
                pixels.extend([max(.01,min(1,c+noise)) for c in COLORS[name]]+[1])
        img = bpy.data.images.new('authored_'+name, width=size, height=size)
        img.pixels.foreach_set(pixels)
        img.pack()
        tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image = img
        mat.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
    materials[name] = mat
    return mat


def meta(obj, room, kind):
    obj['room_id'],obj['kind'] = room,kind
    return obj


def box(name, pos, dims, mat, room, kind='fixture', rotation=0, bevel=.012):
    # Public coordinate contract is X,Y,Z; convert once at object creation.
    bpy.ops.mesh.primitive_cube_add(size=1,location=(pos[0],-pos[2],pos[1]))
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = (dims[0],dims[2],dims[1])
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    obj.rotation_euler.z = math.radians(rotation)
    obj.data.materials.append(material(mat))
    if bevel:
        mod = obj.modifiers.new('Soft manufactured edges','BEVEL')
        mod.width = min(bevel,min(dims)/5)
        mod.segments = 2
        obj.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL')
    return meta(obj,room,kind)


def ellipsoid(name,pos,dims,mat,room,rotation=0):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,location=(pos[0],-pos[2],pos[1]))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (dims[0]/2,dims[2]/2,dims[1]/2)
    obj.rotation_euler.z = math.radians(rotation)
    obj.data.materials.append(material(mat))
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return meta(obj,room,'fixture')


walls = set()
for room in plan['spaces']:
    rid,poly,h = room['id'],room['polygon'],room['height']
    # One closed slab per disjoint room. No scene-wide floor plane at Y=0.
    verts = [(p['x'],-p['z'],y) for y in (-.12,0) for p in poly]
    n = len(poly)
    faces = [tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    mesh = bpy.data.meshes.new(rid+'_floor')
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    obj = bpy.data.objects.new(rid+'_floor',mesh)
    scene.collection.objects.link(obj)
    meta(obj,rid,'floor')
    obj.data.materials.append(material(room['floor_material']))
    uv = mesh.uv_layers.new()
    for loop in mesh.loops:
        co = mesh.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (co.x/2,co.y/2)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(False)
    for i,a in enumerate(poly):
        b = poly[(i+1)%n]
        key = tuple(sorted(((round(a['x'],4),round(a['z'],4)),(round(b['x'],4),round(b['z'],4)))))
        if key in walls:
            continue
        walls.add(key)
        dx,dz = b['x']-a['x'],b['z']-a['z']
        length = math.hypot(dx,dz)
        angle = -math.degrees(math.atan2(dz,dx))
        def segment(start,end,bottom,top,mat=room['wall_material'],kind='wall',thickness=.12):
            if end-start < .001 or top-bottom < .001:
                return
            mid = (start+end)/2
            return box(rid+'_'+kind,(a['x']+dx*mid/length,(bottom+top)/2,a['z']+dz*mid/length),
                       (end-start,top-bottom,thickness),mat,rid,kind,angle,.004)
        cursor = 0
        for op in sorted([o for o in room['openings'] if o['wall']==i],key=lambda o:o['offset']):
            start,end = op['offset'],op['offset']+op['width']
            segment(cursor,start,0,h)
            segment(start,end,0,op['bottom'])
            segment(start,end,op['bottom']+op['height'],h)
            for edge in (start,end):
                segment(edge-.035,edge+.035,op['bottom'],op['bottom']+op['height'],'wood','trim',.15)
            segment(start,end,op['bottom']+op['height']-.03,op['bottom']+op['height']+.03,'wood','trim',.15)
            if op['kind']=='window':
                segment(start,end,op['bottom']-.03,op['bottom']+.03,'wood','trim',.18)
                segment(start+.04,end-.04,op['bottom']+.04,op['bottom']+op['height']-.04,'glass','window',.018)
            cursor = end
        segment(cursor,length,0,h)
        # Raised baseboard follows solid wall segments, not across doorway openings.
        cursor = 0
        for op in sorted([o for o in room['openings'] if o['wall']==i and o['bottom']<.1],key=lambda o:o['offset']):
            segment(cursor,op['offset'],0,.09,'white','trim',.15)
            cursor = op['offset']+op['width']
        segment(cursor,length,0,.09,'white','trim',.15)


for index,f in enumerate(plan['fixtures']):
    rid,k,w,d,h = f['room_id'],f['kind'],f['width'],f['depth'],f['height']
    p,rot,mat = f['position'],f['rotation'],f['material']
    theta = math.radians(rot)
    def pos(x,y,z):
        return (p['x']+x*math.cos(theta)+z*math.sin(theta),p['y']+y,p['z']-x*math.sin(theta)+z*math.cos(theta))
    def part(label,x,y,z,ww,hh,dd,finish=mat,round_shape=False):
        fn = ellipsoid if round_shape else box
        obj = fn(f'{rid}_{k}{index}_{label}',pos(x,y,z),(ww,hh,dd),finish,rid,rotation=rot)
        obj['evidence'] = f['evidence']
        obj['sources'] = ','.join(f['sources'])
        return obj
    if k in ('cabinet','upper_cabinet','counter','sink','stove'):
        part('carcass',0,h*.475,0,w*.98,h*.95,d*.95)
        part('worktop',0,h-.025,0,w,.05,d,'stone' if k!='upper_cabinet' else mat)
        for sign in (-1,1):
            part('door',sign*w*.25,h*.5,d*.49,w*.47,h*.78,.026)
            part('handle',sign*w*.08,h*.58,d*.52,.025,.13,.025,'metal')
        part('toe_kick',0,.04,-.03,w*.94,.08,d*.87,'dark')
        if k=='sink':
            part('basin_rim',0,h+.007,0,w*.64,.015,d*.64,'metal')
            part('basin_shadow',0,h+.017,0,w*.52,.008,d*.5,'dark')
            part('basin',0,h+.025,0,w*.44,.01,d*.4,'metal')
            part('tap',0,h+.14,-d*.33,.035,.28,.035,'metal')
            part('spout',0,h+.27,-d*.2,.035,.035,d*.28,'metal')
        if k=='stove':
            part('cooktop',0,h+.006,0,w*.94,.018,d*.9,'dark')
            for x in (-.24,.24):
                for z in (-.22,.22):
                    part('burner',x*w,h+.02,z*d,w*.28,.02,d*.27,'metal',True)
            part('oven',0,h*.45,d*.513,w*.76,h*.5,.025,'dark')
    elif k=='fridge':
        part('case',0,h/2,0,w,h,d)
        for yy,hh in ((h*.3,h*.58),(h*.8,h*.38)):
            part('door',0,yy,d*.51,w*.96,hh,.035,'metal')
            part('handle',w*.36,yy,d*.55,.035,hh*.5,.035,'dark')
    elif k in ('table','chair'):
        seat = h if k=='table' else h*.48
        part('top',0,seat-.04,0,w,.08,d)
        for x in (-.4,.4):
            for z in (-.4,.4):
                part('leg',w*x,(seat-.08)/2,d*z,.055,seat-.08,.055)
        if k=='chair':
            part('back',0,h*.72,-d*.43,w,h*.56,.07)
    elif k in ('bed','sofa'):
        part('base',0,h*.18,0,w,h*.36,d)
        part('cushion',0,h*.44,0,w*.97,h*.22,d*.96,'fabric')
        part('back',0,h*.66,-d*.45,w,h*.68,d*.1,mat)
        if k=='bed':
            for x in (-.24,.24):
                part('pillow',x*w,h*.6,-d*.28,w*.4,h*.15,d*.22,'white',True)
        else:
            for x in (-.46,.46):
                part('arm',x*w,h*.52,0,w*.08,h*.4,d,'fabric')
    elif k=='shelf':
        for x in (-.47,.47):
            part('side',x*w,h/2,0,w*.06,h,d)
        for level in range(5):
            part('shelf',0,.025+(h-.05)*level/4,0,w,.05,d)
    elif k=='toilet':
        part('pedestal',0,h*.25,d*.12,w*.6,h*.5,d*.6,'white',True)
        part('bowl',0,h*.5,d*.1,w,h*.25,d*.8,'white',True)
        part('seat',0,h*.62,d*.13,w*.9,h*.05,d*.7,'white',True)
        part('tank',0,h*.7,-d*.35,w*.86,h*.6,d*.27,'white')
    elif k in ('bathtub','shower'):
        rim = h if k=='bathtub' else .12
        part('tray',0,.035,0,w,.07,d,'white')
        for x in (-.47,.47):
            part('side',x*w,rim/2,0,w*.06,rim,d,'white')
        for z in (-.47,.47):
            part('end',0,rim/2,z*d,w,rim,d*.06,'white')
        if k=='shower':
            part('screen',w*.48,h/2,0,.025,h,d,'glass')
            part('riser',-w*.35,h*.55,-d*.43,.03,h*.8,.03,'metal')

# GLB extras preserve semantic room/fixture grouping for consumers.
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(out/'house.blend'))
bpy.ops.export_scene.gltf(filepath=str(out/'house.glb'),export_format='GLB',
                          export_apply=True,export_extras=True,export_yup=True)
print('HOUSE_BUILD_COMPLETE',len(scene.objects))
