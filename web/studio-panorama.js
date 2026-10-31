// Dependency-free equirectangular panorama preview; original image fallback.
export function panorama(container, url, initialYaw = 0) {
  const canvas = document.createElement("canvas");
  canvas.setAttribute(
    "aria-label",
    "Ảnh panorama 360°. Kéo hoặc dùng phím mũi tên để xoay.",
  );
  canvas.tabIndex = 0;
  const gl = canvas.getContext("webgl");
  let disposed = false;
  let yaw = (initialYaw * Math.PI) / 180,
    pitch = 0,
    fov = 1.3,
    dragging;
  if (!gl) {
    const img = new Image();
    img.src = url;
    img.alt = "Panorama gốc";
    container.replaceChildren(img);
    return () => {};
  }
  function shader(type, source) {
    const s = gl.createShader(type);
    gl.shaderSource(s, source);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS))
      throw new Error("WebGL shader");
    return s;
  }
  const vertex = shader(
    gl.VERTEX_SHADER,
    "attribute vec2 p;varying vec2 uv;void main(){uv=p;gl_Position=vec4(p,0.,1.);}",
  );
  const fragment = shader(
    gl.FRAGMENT_SHADER,
    `precision mediump float;varying vec2 uv;uniform sampler2D tex;uniform vec4 camera;
  void main(){vec3 d=normalize(vec3(uv.x*camera.z*camera.w,-uv.y*camera.z,1.));
  float cp=cos(camera.y),sp=sin(camera.y);d=vec3(d.x,cp*d.y-sp*d.z,sp*d.y+cp*d.z);
  float cy=cos(camera.x),sy=sin(camera.x);d=vec3(cy*d.x+sy*d.z,d.y,-sy*d.x+cy*d.z);
  vec2 t=vec2(atan(d.x,d.z)/6.2831853+.5,asin(clamp(d.y,-1.,1.))/3.14159265+.5);gl_FragColor=texture2D(tex,t);}`,
  );
  const program = gl.createProgram();
  gl.attachShader(program, vertex);
  gl.attachShader(program, fragment);
  gl.linkProgram(program);
  const buffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(
    gl.ARRAY_BUFFER,
    new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]),
    gl.STATIC_DRAW,
  );
  gl.useProgram(program);
  const location = gl.getAttribLocation(program, "p");
  gl.enableVertexAttribArray(location);
  gl.vertexAttribPointer(location, 2, gl.FLOAT, false, 0, 0);
  const texture = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, texture);
  for (const [key, value] of [
    [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE],
    [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE],
    [gl.TEXTURE_MIN_FILTER, gl.LINEAR],
    [gl.TEXTURE_MAG_FILTER, gl.LINEAR],
  ])
    gl.texParameteri(gl.TEXTURE_2D, key, value);
  function draw() {
    if (disposed) return;
    canvas.width = Math.max(1, container.clientWidth * devicePixelRatio);
    canvas.height = Math.max(1, container.clientHeight * devicePixelRatio);
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.uniform4f(
      gl.getUniformLocation(program, "camera"),
      yaw,
      pitch,
      Math.tan(fov / 2),
      canvas.width / canvas.height,
    );
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }
  const img = new Image();
  img.onload = () => {
    if (disposed) return;
    const limit = Math.min(8192, gl.getParameter(gl.MAX_TEXTURE_SIZE));
    let textureImage = img;
    if (Math.max(img.width, img.height) > limit) {
      textureImage = document.createElement("canvas");
      const scale = limit / Math.max(img.width, img.height);
      textureImage.width = Math.max(1, Math.round(img.width * scale));
      textureImage.height = Math.max(1, Math.round(img.height * scale));
      textureImage
        .getContext("2d")
        .drawImage(img, 0, 0, textureImage.width, textureImage.height);
    }
    gl.texImage2D(
      gl.TEXTURE_2D,
      0,
      gl.RGB,
      gl.RGB,
      gl.UNSIGNED_BYTE,
      textureImage,
    );
    draw();
  };
  img.onerror = () => {
    if (!disposed) {
      const p = document.createElement("p");
      p.textContent = "Không tải được panorama. Hãy tải lại trang.";
      container.replaceChildren(p);
    }
  };
  img.src = url;
  container.replaceChildren(canvas);
  const observer = new ResizeObserver(() => {
    if (img.complete && img.naturalWidth) draw();
  });
  observer.observe(container);
  canvas.onpointerdown = (e) => {
    dragging = [e.clientX, e.clientY];
    canvas.setPointerCapture(e.pointerId);
  };
  canvas.onpointermove = (e) => {
    if (!dragging) return;
    yaw -= (e.clientX - dragging[0]) * 0.005;
    pitch = Math.max(
      -1.4,
      Math.min(1.4, pitch + (e.clientY - dragging[1]) * 0.005),
    );
    dragging = [e.clientX, e.clientY];
    draw();
  };
  canvas.onpointerup = canvas.onpointercancel = () => {
    dragging = null;
  };
  canvas.onkeydown = (e) => {
    if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key))
      return;
    e.preventDefault();
    yaw += e.key === "ArrowLeft" ? -0.12 : e.key === "ArrowRight" ? 0.12 : 0;
    pitch = Math.max(
      -1.4,
      Math.min(
        1.4,
        pitch + (e.key === "ArrowUp" ? -0.1 : e.key === "ArrowDown" ? 0.1 : 0),
      ),
    );
    draw();
  };
  canvas.onwheel = (e) => {
    e.preventDefault();
    fov = Math.max(0.4, Math.min(2, fov + e.deltaY * 0.001));
    draw();
  };
  return () => {
    disposed = true;
    observer.disconnect();
    gl.deleteTexture(texture);
    gl.deleteBuffer(buffer);
    gl.deleteProgram(program);
    gl.deleteShader(vertex);
    gl.deleteShader(fragment);
    gl.getExtension("WEBGL_lose_context")?.loseContext();
  };
}
