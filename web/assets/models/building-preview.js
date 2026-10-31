import * as THREE from '../vendor/three/build/three.module.min.js';
import { GLTFLoader } from '../vendor/three/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from '../vendor/three/examples/jsm/controls/OrbitControls.js';
import { MeshoptDecoder } from '../vendor/meshopt/meshopt_decoder.js';

// Same furnished Seoul GLB as the sample tour; no extra ground or invented fixtures.
export async function mountBuildingPreview() {
  const canvas=document.querySelector('#hero-building'), state=document.querySelector('#building-state');
  if(!canvas) return;
  let renderer,root,frame=0,destroyed=false,suspended=false,visible=true;
  let paused=document.querySelector('#hero-rotation')?.ariaPressed==='true';
  const motion=matchMedia('(prefers-reduced-motion: reduce)');
  const fail=()=>{state.hidden=false;state.textContent=document.documentElement.lang==='vi'?'Không tải được mô hình Seoul.':'Seoul model unavailable.';canvas.hidden=true;};
  try {
    renderer=new THREE.WebGLRenderer({canvas,alpha:true,antialias:true,preserveDrawingBuffer:true});
    renderer.setPixelRatio(Math.min(devicePixelRatio||1,1.5));renderer.setClearColor(0x000000,0);
    renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1;
    const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(36,1,.05,200);
    scene.add(new THREE.HemisphereLight(0xffffff,0x8c8d85,2.3));
    const key=new THREE.DirectionalLight(0xfff7e8,3.2);key.position.set(-7,10,7);scene.add(key);
    const fill=new THREE.DirectionalLight(0xddeaff,1.2);fill.position.set(8,6,-8);scene.add(fill);
    const controls=new OrbitControls(camera,canvas);controls.enablePan=false;controls.enableZoom=false;
    controls.maxPolarAngle=Math.PI*.47;controls.minPolarAngle=.3;controls.autoRotateSpeed=.6;
    let center,radius;
    function draw(){if(!destroyed&&root)renderer.render(scene,camera);}
    function resize(){
      if(!root||destroyed)return;const w=canvas.clientWidth,h=canvas.clientHeight;if(!w||!h)return;
      renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();
      const distance=radius*.52/Math.sin(Math.atan(Math.tan(THREE.MathUtils.degToRad(camera.fov/2))*Math.min(1,camera.aspect)));
      const direction=camera.position.clone().sub(controls.target).normalize();camera.position.copy(center).add(direction.multiplyScalar(distance));controls.target.copy(center);controls.update();draw();
    }
    let last=0;
    function tick(now){frame=0;if(destroyed||suspended||paused||motion.matches||document.hidden||!visible||!root)return;
      if(now-last>=33){controls.autoRotate=true;controls.update(Math.min((now-last)/1000,.1));draw();last=now;}
      frame=requestAnimationFrame(tick);
    }
    function sync(){cancelAnimationFrame(frame);controls.autoRotate=false;draw();last=performance.now();if(!destroyed&&!suspended&&!paused&&!motion.matches&&!document.hidden&&visible&&root)frame=requestAnimationFrame(tick);}
    controls.addEventListener('start',()=>{paused=true;document.dispatchEvent(new Event('heropause'));sync();});controls.addEventListener('change',draw);
    canvas.addEventListener('keydown',event=>{
      if(!root||!['ArrowLeft','ArrowRight'].includes(event.key))return;event.preventDefault();paused=true;document.dispatchEvent(new Event('heropause'));
      const offset=camera.position.clone().sub(controls.target);offset.applyAxisAngle(new THREE.Vector3(0,1,0),event.key==='ArrowLeft'?-.15:.15);camera.position.copy(controls.target).add(offset);controls.update();sync();
    });
    document.addEventListener('heromotionchange',e=>{paused=e.detail.paused;sync();});
    document.addEventListener('visibilitychange',sync);motion.addEventListener('change',sync);
    const resizeObserver=new ResizeObserver(resize);resizeObserver.observe(canvas);
    const intersection=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;sync();});intersection.observe(canvas);
    function release(object){const textures=new Set();object.traverse(o=>{o.geometry?.dispose();for(const m of Array.isArray(o.material)?o.material:o.material?[o.material]:[]){for(const value of Object.values(m))if(value?.isTexture)textures.add(value);m.dispose();}});textures.forEach(t=>{t.source?.data?.close?.();t.dispose();});}
    window.addEventListener('pagehide',event=>{suspended=true;cancelAnimationFrame(frame);if(!event.persisted){destroyed=true;resizeObserver.disconnect();intersection.disconnect();controls.dispose();if(root)release(root);renderer.dispose();}});
    window.addEventListener('pageshow',()=>{suspended=false;sync();});
    const response=await fetch('/api/demos/seoul-apartment/assets/house/manifest.json');if(!response.ok)throw Error('Sample unavailable');
    const manifest=await response.json();if(manifest.model!=='house/dollhouse-studio.glb')throw Error('Unexpected sample model');
    const gltf=await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).loadAsync('/api/demos/seoul-apartment/assets/'+manifest.model);
    if(destroyed){release(gltf.scene);return;}
    root=gltf.scene;scene.add(root);const bounds=new THREE.Box3().setFromObject(root);center=bounds.getCenter(new THREE.Vector3());radius=bounds.getSize(new THREE.Vector3()).length();
    controls.target.copy(center);camera.position.copy(center).add(new THREE.Vector3(-.8,1.1,1));
    canvas.hidden=false;state.hidden=true;canvas.dataset.ready='true';canvas.dataset.sample='seoul-apartment';document.querySelector('#hero-rotation').hidden=false;resize();sync();
  } catch {if(!destroyed){cancelAnimationFrame(frame);renderer?.dispose();fail();}}
}
