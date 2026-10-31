// Run with glTF Transform 4.5.0 installed in an external tools directory:
// node repair_seoul_uv.mjs <tools/node_modules> <source.glb> <repaired.glb>
// Repairs only source texture references whose UV index is -1. No geometry edits.
import { pathToFileURL } from 'node:url';
import path from 'node:path';
const [modules, input, output]=process.argv.slice(2);
const { NodeIO }=await import(pathToFileURL(path.resolve(modules,'@gltf-transform/core/dist/index.js')));
const { ALL_EXTENSIONS }=await import(pathToFileURL(path.resolve(modules,'@gltf-transform/extensions/dist/index.js')));
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS), doc=await io.read(input);
const repaired=new Set(); let primitives=0;
for(const material of doc.getRoot().listMaterials()) {
  for(const info of [material.getBaseColorTextureInfo(), material.getNormalTextureInfo()]) {
    if(info && info.getTexCoord()<0) { info.setTexCoord(0); repaired.add(material); }
  }
}
for(const mesh of doc.getRoot().listMeshes()) for(const prim of mesh.listPrimitives()) {
  if(!repaired.has(prim.getMaterial()) || prim.getAttribute('TEXCOORD_0')) continue;
  const pos=prim.getAttribute('POSITION'), min=pos.getMin([]), max=pos.getMax([]);
  const axes=[0,1,2].sort((a,b)=>(max[b]-min[b])-(max[a]-min[a]));
  const uv=new Float32Array(pos.getCount()*2), point=[];
  for(let i=0;i<pos.getCount();i++) {
    pos.getElement(i,point);
    for(let j=0;j<2;j++) { const axis=axes[j];uv[i*2+j]=(point[axis]-min[axis])/Math.max(max[axis]-min[axis],1e-6); }
  }
  prim.setAttribute('TEXCOORD_0',doc.createAccessor().setType('VEC2').setArray(uv).setBuffer(pos.getBuffer()));primitives++;
}
if(repaired.size!==4 || primitives!==5) throw new Error('Source changed: expected four materials and five primitives');
await io.write(output,doc);
console.log(JSON.stringify({repaired_materials:repaired.size,planar_uv_primitives:primitives,geometry_changed:false}));
