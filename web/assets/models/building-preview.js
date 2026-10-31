// Preview the exact cached demo dollhouse, using its manifest URL and embedded base textures.
// No model data is copied into the repository; see README.md for source and limits.
export async function mountBuildingPreview() {
  const canvas = document.querySelector('#hero-building');
  if (!canvas) return;
  const state = document.querySelector('#building-state');
  const gl = canvas.getContext('webgl', { alpha: true, antialias: true, preserveDrawingBuffer: true });
  const fail = () => { state.hidden = false; state.textContent = document.documentElement.lang === 'vi' ? 'Không tải được mô hình 3D.' : '3D preview unavailable.'; canvas.hidden = true; };
  if (!gl) { fail(); return; }
  try {
    const manifestResponse = await fetch('/api/demos/zind-house-000/assets/house/manifest.json');
    if (!manifestResponse.ok) throw Error(`Demo manifest: ${manifestResponse.status}`);
    const manifest = await manifestResponse.json();
    if (!manifest.dollhouse?.url) throw Error('Demo manifest has no dollhouse URL');
    const modelURL = new URL(manifest.dollhouse.url, location.origin);
    if (modelURL.origin !== location.origin || !modelURL.pathname.startsWith('/api/demos/zind-house-000/assets/')) throw Error('Invalid demo dollhouse URL');
    const response = await fetch(modelURL.href);
    if (!response.ok) throw Error(`Building asset: ${response.status}`);
    const bytes = await response.arrayBuffer(), view = new DataView(bytes);
    if (view.getUint32(0, true) !== 0x46546c67 || view.getUint32(4, true) !== 2) throw Error('Expected GLB v2');
    const jsonLength = view.getUint32(12, true);
    const model = JSON.parse(new TextDecoder().decode(new Uint8Array(bytes, 20, jsonLength)));
    const binOffset = 20 + jsonLength + 8;
    const accessor = id => {
      const a = model.accessors[id], b = model.bufferViews[a.bufferView];
      const components = { SCALAR: 1, VEC2: 2, VEC3: 3 }[a.type];
      const types = { 5121: [1, 'getUint8'], 5123: [2, 'getUint16'], 5125: [4, 'getUint32'], 5126: [4, 'getFloat32'] };
      if (!components || !types[a.componentType] || a.sparse || b.buffer !== 0) throw Error('Unsupported preview accessor');
      const [size, read] = types[a.componentType], start = binOffset + (b.byteOffset || 0) + (a.byteOffset || 0);
      return Array.from({ length: a.count }, (_, i) => Array.from({ length: components }, (_, j) => view[read](start + i * (b.byteStride || size * components) + j * size, true)));
    };
    const identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
    const multiply = (a, b) => Array.from({ length: 16 }, (_, i) => [0, 1, 2, 3].reduce((sum, k) => sum + a[i % 4 + k * 4] * b[Math.floor(i / 4) * 4 + k], 0));
    const triangles = [];
    const localMatrix = node => {
      if (node.matrix) return node.matrix;
      const [x, y, z, w] = node.rotation || [0, 0, 0, 1], [sx, sy, sz] = node.scale || [1, 1, 1], [tx, ty, tz] = node.translation || [0, 0, 0];
      return [(1-2*y*y-2*z*z)*sx,(2*x*y+2*z*w)*sx,(2*x*z-2*y*w)*sx,0,
        (2*x*y-2*z*w)*sy,(1-2*x*x-2*z*z)*sy,(2*y*z+2*x*w)*sy,0,
        (2*x*z+2*y*w)*sz,(2*y*z-2*x*w)*sz,(1-2*x*x-2*y*y)*sz,0,tx,ty,tz,1];
    };
    const visit = (id, parent) => {
      const node = model.nodes[id];
      const matrix = multiply(parent, localMatrix(node));
      if (node.mesh !== undefined) for (const primitive of model.meshes[node.mesh].primitives) {
        if ((primitive.mode ?? 4) !== 4) throw Error('Expected triangles');
        const positions = accessor(primitive.attributes.POSITION).map(p => [0, 1, 2].map(i => matrix[i] * p[0] + matrix[i + 4] * p[1] + matrix[i + 8] * p[2] + matrix[i + 12]));
        const indices = accessor(primitive.indices).flat();
        const uv = primitive.attributes.TEXCOORD_0 === undefined ? null : accessor(primitive.attributes.TEXCOORD_0);
        for (let i = 0; i < indices.length; i += 3) {
          const points = indices.slice(i, i + 3).map(j => positions[j]);
          const a = points[1].map((v, j) => v - points[0][j]), b = points[2].map((v, j) => v - points[0][j]);
          const normal = [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
          const length = Math.hypot(...normal) || 1;
          triangles.push({ points, normal: normal.map(v => v / length), uv: indices.slice(i, i + 3).map(j => uv?.[j] || [0, 0]), material: primitive.material });
        }
      }
      for (const child of node.children || []) visit(child, matrix);
    };
    for (const id of model.scenes[model.scene || 0].nodes) visit(id, identity);
    const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
    for (const t of triangles) for (const p of t.points) p.forEach((v, i) => { min[i] = Math.min(min[i], v); max[i] = Math.max(max[i], v); });
    const size = max.map((v, i) => v - min[i]);
    const center = min.map((v, i) => (v + max[i]) / 2), scale = 1.85 / Math.max(Math.hypot(size[0], size[2]), size[1]);
    const groups = model.materials.map(material => ({ material, vertices: [] }));
    for (const t of triangles) for (let i = 0; i < 3; i++) groups[t.material].vertices.push(...t.points[i].map((v, j) => (v - center[j]) * scale), ...t.normal, ...t.uv[i]);
    for (const group of groups) {
      group.buffer = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, group.buffer);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(group.vertices), gl.STATIC_DRAW); group.count = group.vertices.length / 8; delete group.vertices;
      const pbr = group.material.pbrMetallicRoughness || {};
      group.color = pbr.baseColorFactor || [1, 1, 1, 1];
      group.texture = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, group.texture);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([255, 255, 255, 255]));
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      if (pbr.baseColorTexture) {
        const image = model.images[model.textures[pbr.baseColorTexture.index].source], b = model.bufferViews[image.bufferView];
        if (!b || b.buffer !== 0) throw Error('Expected embedded demo base texture');
        const bitmap = await createImageBitmap(new Blob([new Uint8Array(bytes, binOffset + (b.byteOffset || 0), b.byteLength)], { type: image.mimeType }));
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, bitmap);
        if ((bitmap.width & (bitmap.width - 1)) === 0 && (bitmap.height & (bitmap.height - 1)) === 0) {
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);
          gl.generateMipmap(gl.TEXTURE_2D); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
        }
        bitmap.close();
      }
    }
    const shader = (type, source) => { const s = gl.createShader(type); gl.shaderSource(s, source); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(s)); return s; };
    const program = gl.createProgram();
    gl.attachShader(program, shader(gl.VERTEX_SHADER, `
      attribute vec3 position, normal; attribute vec2 uv; uniform vec3 camera; varying float illumination; varying vec2 textureUV;
      void main(){
        float c=cos(camera.x),s=sin(camera.x),p=.88;
        mat3 turn=mat3(c,0.,-s,0.,1.,0.,s,0.,c);
        mat3 tilt=mat3(1.,0.,0.,0.,cos(p),sin(p),0.,-sin(p),cos(p));
        vec3 v=tilt*turn*position,n=normalize(turn*normal);
        float light=.45+.55*max(dot(n,normalize(vec3(-.5,.85,1.))),0.);
        illumination=light; textureUV=uv;
        gl_Position=vec4(v.x*camera.y,v.y*camera.z,-v.z*.4,1.);
      }`));
    gl.attachShader(program, shader(gl.FRAGMENT_SHADER, 'precision mediump float; varying float illumination; varying vec2 textureUV; uniform sampler2D baseTexture; uniform vec4 baseColor; void main(){vec4 color=texture2D(baseTexture,textureUV)*baseColor;gl_FragColor=vec4(color.rgb*illumination,color.a);}'));
    gl.linkProgram(program); if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw Error('Building shader link failed'); gl.useProgram(program);
    const attributes = [['position', 3, 0], ['normal', 3, 12], ['uv', 2, 24]].map(([name, size, offset]) => [gl.getAttribLocation(program, name), size, offset]);
    const colorLocation = gl.getUniformLocation(program, 'baseColor');
    const camera = gl.getUniformLocation(program, 'camera'), motion = matchMedia('(prefers-reduced-motion: reduce)');
    let yaw = -.65, paused = document.querySelector('#hero-rotation')?.ariaPressed === 'true', visible = true, drag = null, frame = 0, last = 0;
    const draw = () => {
      const dpr = Math.min(devicePixelRatio || 1, 2), width = Math.round(canvas.clientWidth * dpr), height = Math.round(canvas.clientHeight * dpr);
      if (!width || !height) return;
      if (canvas.width !== width || canvas.height !== height) { canvas.width = width; canvas.height = height; }
      gl.viewport(0, 0, width, height); gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT); gl.enable(gl.DEPTH_TEST); gl.enable(gl.CULL_FACE); gl.cullFace(gl.BACK);
      const aspect = width / height; gl.uniform3f(camera, yaw, Math.min(1, 1 / aspect), Math.min(1, aspect));
      gl.disable(gl.BLEND); gl.depthMask(true);
      for (const group of groups) {
        if (group.material.doubleSided) gl.disable(gl.CULL_FACE); else gl.enable(gl.CULL_FACE);
        gl.bindBuffer(gl.ARRAY_BUFFER, group.buffer);
        for (const [location, size, offset] of attributes) { gl.enableVertexAttribArray(location); gl.vertexAttribPointer(location, size, gl.FLOAT, false, 32, offset); }
        gl.bindTexture(gl.TEXTURE_2D, group.texture); gl.uniform4fv(colorLocation, group.color); gl.drawArrays(gl.TRIANGLES, 0, group.count);
      }
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
