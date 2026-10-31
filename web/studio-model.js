import * as THREE from './assets/vendor/three/build/three.module.min.js';
import { GLTFLoader } from './assets/vendor/three/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from './assets/vendor/three/examples/jsm/controls/OrbitControls.js';
import { MeshoptDecoder } from './assets/vendor/meshopt/meshopt_decoder.js';

/** Owns its complete lifecycle, including GLB loads that finish after disposal. */
export function houseModel(host, url, rooms, onCapture, options = {}) {
  let stopped = false, frame, root;
  const stage = document.createElement('div');
  stage.className = 'house-stage';
  const status = document.createElement('p');
  status.className = 'house-status';
  status.textContent = 'Đang tải mô hình…';
  status.setAttribute('role','status');
  stage.append(status);
  host.replaceChildren(stage);
  let renderer;
  try { renderer = new THREE.WebGLRenderer({antialias:true,alpha:true}); }
  catch { status.textContent = 'Thiết bị chưa hỗ trợ WebGL. Bạn vẫn có thể tải GLB.'; return () => {}; }
  renderer.setPixelRatio(Math.min(devicePixelRatio,2));
  renderer.setClearColor(0xf0efeb,1);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = options.exposure ?? 1.3;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.domElement.tabIndex = 0;
  renderer.domElement.setAttribute('aria-label','Mô hình nhà 3D. Kéo để xoay, cuộn để phóng to.');
  stage.prepend(renderer.domElement);
  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xffffff,0x9b9589,2.3));
  const sun = new THREE.DirectionalLight(0xfff7e8,3.2);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048,2048);
  sun.shadow.normalBias = .025;
  scene.add(sun,sun.target);
  const fill = new THREE.DirectionalLight(0xddeaff,1.2);
  fill.position.set(-10,8,-10); scene.add(fill);
  const camera = new THREE.PerspectiveCamera(40,1,.05,200);
  const controls = new OrbitControls(camera,renderer.domElement);
  controls.enableDamping = true;
  controls.maxPolarAngle = Math.PI*.48;
  const markers = [], wallObjects = [];
  const toolbar = document.createElement('div'); toolbar.className = 'house-toolbar';
  const reset = document.createElement('button'); reset.textContent = 'Đặt lại góc nhìn';
  const walls = document.createElement('button'); walls.textContent = 'Ẩn tường';
  let wallsVisible = true;
  walls.onclick = () => {
    wallsVisible = !wallsVisible;
    wallObjects.forEach(o => { o.visible = wallsVisible; });
    walls.textContent = wallsVisible ? 'Ẩn tường' : 'Hiện tường';
  };
  toolbar.append(reset,walls); stage.append(toolbar);
  let initialPosition, initialTarget;
  const framingSine = aspect => Math.sin(Math.atan(Math.tan(THREE.MathUtils.degToRad(camera.fov/2))*Math.min(1,aspect)));
  reset.onclick = () => {
    if (!initialPosition) return;
    camera.position.copy(initialPosition); controls.target.copy(initialTarget); controls.update();
  };
  function release(object) {
    const textures = new Set(), materials = new Set(), geometries = new Set();
    object.traverse(o => {
      if(o.geometry) geometries.add(o.geometry);
      for (const m of Array.isArray(o.material)?o.material:o.material?[o.material]:[]) {
        materials.add(m);
        for(const value of Object.values(m)) if(value?.isTexture) textures.add(value);
      }
    });
    textures.forEach(t => { t.source?.data?.close?.(); t.dispose(); });
    materials.forEach(m => m.dispose()); geometries.forEach(g => g.dispose());
  }
  const observer = new ResizeObserver(() => {
    const w = stage.clientWidth, h = stage.clientHeight;
    if(!w || !h || stopped) return;
    renderer.setSize(w,h,false);
    const aspect=w/h, factor=framingSine(camera.aspect)/framingSine(aspect);
    if(root && initialPosition) {
      camera.position.sub(controls.target).multiplyScalar(factor).add(controls.target);
      initialPosition.sub(initialTarget).multiplyScalar(factor).add(initialTarget);
    }
    camera.aspect=aspect; camera.updateProjectionMatrix();
  }); observer.observe(stage);
  new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).load(url, gltf => {
    if(stopped) { release(gltf.scene); return; }
    root = gltf.scene; scene.add(root);
    const bounds = new THREE.Box3().setFromObject(root), size = bounds.getSize(new THREE.Vector3());
    const center = bounds.getCenter(new THREE.Vector3());
    const radius = Math.max(size.length(),1);
    camera.near = Math.max(.02,radius/1000); camera.far=radius*12; camera.updateProjectionMatrix();
    initialTarget = center.clone();
    initialPosition = center.clone().add(new THREE.Vector3(...(options.cameraDirection ?? [.8,1.1,1])).normalize().multiplyScalar(radius*(options.framing ?? .53)/framingSine(camera.aspect)));
    reset.onclick();
    controls.minDistance = radius*.15; controls.maxDistance = radius*4;
    sun.position.copy(center).add(new THREE.Vector3(radius,radius*1.5,radius));
    sun.target.position.copy(center);
    Object.assign(sun.shadow.camera,{left:-radius,right:radius,top:radius,bottom:-radius,near:.1,far:radius*5});
    sun.shadow.camera.updateProjectionMatrix();
    root.traverse(o => {
      if(o.isMesh) { o.castShadow=true; o.receiveShadow=true; }
      if(['wall','trim','window'].includes(o.userData.kind)) wallObjects.push(o);
    });
    walls.hidden = wallObjects.length === 0;
    // Deliberately no coplanar scene-wide floor/shadow catcher.
    for(const room of rooms.filter(r => r.anchor && r.anchor.dollhouse_visible !== false)) {
      const button = document.createElement('button'); button.className='house-marker';
      button.textContent=room.checkpoint_id.replace('cp','');
      button.title=`${room.label} · ${room.checkpoint_id}`;
      button.setAttribute('aria-label',`Mở panorama ${room.label} ${room.checkpoint_id}`);
      button.dataset.checkpoint=room.checkpoint_id;
      button.onclick = () => onCapture(room.checkpoint_id);
      stage.append(button);
      markers.push({button,position:new THREE.Vector3(...room.anchor.position)});
    }
    status.textContent=(rooms.some(r=>r.anchor?.accuracy!=='measured')?'Mô hình ước lượng · ':'')+'Chọn điểm để vào panorama';
    stage.dataset.loaded='true';
  },undefined,() => { if(!stopped) status.textContent='Không tải được mô hình. Hãy tải lại hoặc tải GLB.'; });
  const projected = new THREE.Vector3();
  function animate() {
    if(stopped) return;
    frame=requestAnimationFrame(animate); controls.update(); renderer.render(scene,camera);
    for(const marker of markers) {
      projected.copy(marker.position).project(camera);
      marker.button.hidden = projected.z < -1 || projected.z > 1 || Math.abs(projected.x)>1 || Math.abs(projected.y)>1;
      marker.button.style.left=`${(projected.x+1)*stage.clientWidth/2}px`;
      marker.button.style.top=`${(1-projected.y)*stage.clientHeight/2}px`;
    }
  } animate();
  return () => {
    stopped=true; cancelAnimationFrame(frame); observer.disconnect(); controls.dispose();
    if(root) release(root); renderer.dispose(); renderer.forceContextLoss(); stage.remove();
  };
}

export function planPreview(host, plan) {
  const ns='http://www.w3.org/2000/svg', svg=document.createElementNS(ns,'svg');
  svg.classList.add('plan-preview'); svg.setAttribute('role','img'); svg.setAttribute('aria-label','Bố cục nhà dự kiến');
  const points=plan.spaces.flatMap(s=>s.polygon);
  if(!points.length) { const p=document.createElement('p'); p.textContent='Cần làm rõ bố cục trước khi vẽ mặt bằng.'; host.append(p); return; }
  const xs=points.map(p=>p.x),zs=points.map(p=>p.z),minX=Math.min(...xs)-.5,minZ=Math.min(...zs)-.5;
  svg.setAttribute('viewBox',`${minX} ${minZ} ${Math.max(...xs)-minX+.5} ${Math.max(...zs)-minZ+.5}`);
  plan.spaces.forEach(space => {
    const polygon=document.createElementNS(ns,'polygon'); polygon.setAttribute('points',space.polygon.map(p=>`${p.x},${p.z}`).join(' '));
    polygon.setAttribute('fill','#e3e8df'); polygon.setAttribute('stroke','#777e70'); polygon.setAttribute('stroke-width','.06');
    const title=document.createElementNS(ns,'title'); title.textContent=space.label; polygon.append(title); svg.append(polygon);
  });
  plan.captures.forEach(c => {
    const circle=document.createElementNS(ns,'circle'); circle.setAttribute('cx',c.position.x); circle.setAttribute('cy',c.position.z); circle.setAttribute('r','.12'); circle.setAttribute('fill','#ed321e'); svg.append(circle);
    const text=document.createElementNS(ns,'text'); text.setAttribute('x',c.position.x+.18); text.setAttribute('y',c.position.z+.1); text.setAttribute('font-size','.25'); text.textContent=c.checkpoint_id; svg.append(text);
  });
  host.append(svg);
}
