// Small, dependency-free preview of the supplied untextured procedural GLB.
// This is an illustration, not a reconstruction of the sample home's photos.
export async function mountBuildingPreview() {
  const canvas = document.querySelector('#hero-building');
  if (!canvas) return;
  const state = document.querySelector('#building-state');
  const gl = canvas.getContext('webgl', { alpha: true, antialias: true, preserveDrawingBuffer: true });
  const fail = () => { state.hidden = false; state.textContent = document.documentElement.lang === 'vi' ? 'Không tải được mô hình 3D.' : '3D preview unavailable.'; canvas.hidden = true; };
  if (!gl) { fail(); return; }
  try {
    const response = await fetch('/assets/models/sunrise-office.glb');
    if (!response.ok) throw Error(`Building asset: ${response.status}`);
    const bytes = await response.arrayBuffer(), view = new DataView(bytes);
    if (view.getUint32(0, true) !== 0x46546c67 || view.getUint32(4, true) !== 2) throw Error('Expected GLB v2');
    const jsonLength = view.getUint32(12, true);
    const model = JSON.parse(new TextDecoder().decode(new Uint8Array(bytes, 20, jsonLength)));
    const binOffset = 20 + jsonLength + 8;
    const accessor = id => {
      const a = model.accessors[id], b = model.bufferViews[a.bufferView];
      const components = { SCALAR: 1, VEC3: 3 }[a.type];
      const types = { 5121: [1, 'getUint8'], 5123: [2, 'getUint16'], 5125: [4, 'getUint32'], 5126: [4, 'getFloat32'] };
      if (!components || !types[a.componentType] || a.sparse || b.buffer !== 0) throw Error('Unsupported preview accessor');
      const [size, read] = types[a.componentType], start = binOffset + (b.byteOffset || 0) + (a.byteOffset || 0);
      return Array.from({ length: a.count }, (_, i) => Array.from({ length: components }, (_, j) => view[read](start + i * (b.byteStride || size * components) + j * size, true)));
    };
    const identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
    const multiply = (a, b) => Array.from({ length: 16 }, (_, i) => [0, 1, 2, 3].reduce((sum, k) => sum + a[i % 4 + k * 4] * b[Math.floor(i / 4) * 4 + k], 0));
    const triangles = [];
    const visit = (id, parent) => {
      const node = model.nodes[id];
      if (node.name === 'shell_ground') return; // Omit the presentation slab, keep building geometry.
      if (node.translation || node.rotation || node.scale) throw Error('Expected baked/matrix preview transforms');
      const matrix = multiply(parent, node.matrix || identity);
      if (node.mesh !== undefined) for (const primitive of model.meshes[node.mesh].primitives) {
        if ((primitive.mode ?? 4) !== 4) throw Error('Expected triangles');
        const positions = accessor(primitive.attributes.POSITION).map(p => [0, 1, 2].map(i => matrix[i] * p[0] + matrix[i + 4] * p[1] + matrix[i + 8] * p[2] + matrix[i + 12]));
        const indices = accessor(primitive.indices).flat();
        const color = model.materials[primitive.material].pbrMetallicRoughness.baseColorFactor;
        for (let i = 0; i < indices.length; i += 3) {
          const points = indices.slice(i, i + 3).map(j => positions[j]);
          const a = points[1].map((v, j) => v - points[0][j]), b = points[2].map((v, j) => v - points[0][j]);
          const normal = [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
          const length = Math.hypot(...normal) || 1;
          triangles.push({ points, normal: normal.map(v => v / length), color });
        }
      }
      for (const child of node.children || []) visit(child, matrix);
    };
    for (const id of model.scenes[model.scene || 0].nodes) visit(id, identity);
    const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
    for (const t of triangles) for (const p of t.points) p.forEach((v, i) => { min[i] = Math.min(min[i], v); max[i] = Math.max(max[i], v); });
    const center = min.map((v, i) => (v + max[i]) / 2), scale = 1.65 / Math.max(...max.map((v, i) => v - min[i]));
    const pack = list => new Float32Array(list.flatMap(t => t.points.flatMap(p => [...p.map((v, i) => (v - center[i]) * scale), ...t.normal, ...t.color])));
    const opaque = pack(triangles.filter(t => t.color[3] === 1));
    const transparent = triangles.filter(t => t.color[3] < 1);
    const shader = (type, source) => { const s = gl.createShader(type); gl.shaderSource(s, source); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(s)); return s; };
    const program = gl.createProgram();
    gl.attachShader(program, shader(gl.VERTEX_SHADER, `
      attribute vec3 position, normal; attribute vec4 color; uniform vec3 camera; varying vec4 tint;
      void main(){
        float c=cos(camera.x),s=sin(camera.x),p=.34;
        mat3 turn=mat3(c,0.,-s,0.,1.,0.,s,0.,c);
        mat3 tilt=mat3(1.,0.,0.,0.,cos(p),sin(p),0.,-sin(p),cos(p));
        vec3 v=tilt*turn*position,n=normalize(turn*normal);
        float light=.45+.55*max(dot(n,normalize(vec3(-.5,.85,1.))),0.);
        tint=vec4(color.rgb*light,color.a);
        gl_Position=vec4(v.x*camera.y,v.y*camera.z,-v.z*.4,1.);
      }`));
    gl.attachShader(program, shader(gl.FRAGMENT_SHADER, 'precision mediump float; varying vec4 tint; void main(){gl_FragColor=tint;}'));
    gl.linkProgram(program); if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw Error('Building shader link failed'); gl.useProgram(program);
    const buffer = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    for (const [name, size, offset] of [['position', 3, 0], ['normal', 3, 12], ['color', 4, 24]]) {
      const location = gl.getAttribLocation(program, name); gl.enableVertexAttribArray(location); gl.vertexAttribPointer(location, size, gl.FLOAT, false, 40, offset);
    }
    const camera = gl.getUniformLocation(program, 'camera'), motion = matchMedia('(prefers-reduced-motion: reduce)');
    let yaw = -.65, paused = document.querySelector('#hero-rotation')?.ariaPressed === 'true', visible = true, drag = null, frame = 0, last = 0;
    const draw = () => {
      const dpr = Math.min(devicePixelRatio || 1, 2), width = Math.round(canvas.clientWidth * dpr), height = Math.round(canvas.clientHeight * dpr);
      if (!width || !height) return;
      if (canvas.width !== width || canvas.height !== height) { canvas.width = width; canvas.height = height; }
      gl.viewport(0, 0, width, height); gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT); gl.enable(gl.DEPTH_TEST); gl.enable(gl.CULL_FACE); gl.cullFace(gl.BACK);
      const aspect = width / height; gl.uniform3f(camera, yaw, Math.min(1, 1 / aspect), Math.min(1, aspect));
      gl.disable(gl.BLEND); gl.depthMask(true); gl.bufferData(gl.ARRAY_BUFFER, opaque, gl.STATIC_DRAW); gl.drawArrays(gl.TRIANGLES, 0, opaque.length / 10);
      const depth = t => { const p = [0, 1, 2].map(i => t.points.reduce((sum, vertex) => sum + vertex[i], 0) / 3); return Math.sin(.34) * p[1] + Math.cos(.34) * (-Math.sin(yaw) * p[0] + Math.cos(yaw) * p[2]); };
      const glass = pack([...transparent].sort((a, b) => depth(a) - depth(b)));
      gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA); gl.depthMask(false); gl.bufferData(gl.ARRAY_BUFFER, glass, gl.DYNAMIC_DRAW); gl.drawArrays(gl.TRIANGLES, 0, glass.length / 10); gl.depthMask(true);
    };
    const tick = now => { frame = 0; if (paused || motion.matches || document.hidden || !visible) { last = 0; return; } if (last) yaw += Math.min(now - last, 60) * .00012; last = now; draw(); frame = requestAnimationFrame(tick); };
    const sync = () => { cancelAnimationFrame(frame); last = 0; draw(); if (!paused && !motion.matches && !document.hidden && visible) frame = requestAnimationFrame(tick); };
    canvas.onpointerdown = e => { drag = e.clientX; document.dispatchEvent(new Event('heropause')); paused = true; canvas.setPointerCapture(e.pointerId); sync(); };
    canvas.onpointermove = e => { if (drag === null) return; yaw += (e.clientX - drag) * .008; drag = e.clientX; draw(); };
    canvas.onpointerup = canvas.onpointercancel = () => { drag = null; };
    canvas.onkeydown = e => { if (!['ArrowLeft', 'ArrowRight'].includes(e.key)) return; e.preventDefault(); document.dispatchEvent(new Event('heropause')); paused = true; yaw += e.key === 'ArrowLeft' ? -.15 : .15; sync(); };
    document.addEventListener('heromotionchange', e => { paused = e.detail.paused; sync(); });
    document.addEventListener('visibilitychange', sync); motion.addEventListener('change', sync); window.addEventListener('resize', draw);
    new IntersectionObserver(entries => { visible = entries[0].isIntersecting; sync(); }).observe(canvas);
    window.addEventListener('pagehide', () => cancelAnimationFrame(frame)); window.addEventListener('pageshow', sync);
    canvas.hidden = false; state.hidden = true; document.querySelector('#hero-rotation').hidden = false; canvas.dataset.ready = 'true'; sync();
  } catch (error) { console.error('Building preview:', error); fail(); }
}
