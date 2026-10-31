// Adapted with permission from demo-cache/panorama-tour/renderer.js; see docs/INTEGRATION-HANDOFF.md. No demo photos included.
'use strict';
// Rectilinear camera -> cylindrical panorama. Pixels outside captured UV are neutral dark, never synthesized.
// Coverage is a provisional calibration, never inferred as a complete 360 capture.
// Keep the entire rectilinear frustum inside the captured cylinder, including
// its corners after pitch. FOV is the larger viewport dimension in this renderer.
export function constrainView(view, aspect, ratio) {
  const rad=Math.PI/180, horizontal=Math.min(1,aspect), vertical=Math.min(1,1/aspect);
  const coverage=view.coverage*rad, halfHeight=coverage*ratio/2;
  const maxT=Math.min(Math.tan(55*rad),halfHeight*.995/vertical,
    coverage<Math.PI?Math.tan(coverage*.5)*.995/horizontal:Infinity);
  const fov=Math.min(Math.max(.25,view.fov),2*Math.atan(maxT)/rad);
  const tangent=Math.tan(fov*rad/2), lensX=tangent*horizontal, lensY=tangent*vertical;
  const horizontalPitchLimit=coverage<Math.PI?Math.acos(Math.min(1,lensX/(Math.tan(coverage*.5)*Math.hypot(1,lensY))))-Math.atan(lensY):Math.PI/2-Math.atan(lensY);
  const pitchLimit=Math.max(0,Math.min(Math.atan(halfHeight*.995)-Math.atan(lensY),horizontalPitchLimit*.995));
  const pitch=Math.max(-pitchLimit,Math.min(pitchLimit,view.pitch*rad));
  const cornerLongitude=Math.atan2(lensX,Math.cos(pitch)-Math.abs(Math.sin(pitch))*lensY);
  const yawLimit=Math.max(0,coverage/2-cornerLongitude-.0001)/rad;
  const yaw=view.coverage>=360?((view.yaw+180)%360+360)%360-180:Math.max(-yawLimit,Math.min(yawLimit,view.yaw));
  return {...view,fov,pitch:pitch/rad,yaw};
}

export class PanoramaCamera {
  constructor(canvas){
    this.canvas=canvas;
    this.gl=canvas.getContext('webgl',{alpha:false,antialias:false,preserveDrawingBuffer:true});
    if(!this.gl)throw new Error('Trình duyệt chưa hỗ trợ WebGL. Hãy thử Chrome/Safari có tăng tốc đồ họa.');
    const gl=this.gl;
    const shader=(type,src)=>{const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s));return s;};
    const vertex=shader(gl.VERTEX_SHADER,`attribute vec2 position; varying vec2 screen; void main(){screen=position;gl_Position=vec4(position,0.,1.);}`);
    const fragment=shader(gl.FRAGMENT_SHADER,`
      precision highp float;
      varying vec2 screen;
      uniform sampler2D photo;
      uniform vec2 lens;
      uniform vec2 angle;
      uniform float coverage;
      uniform float verticalSpan;
      void main(){
        vec3 ray=normalize(vec3(screen.x*lens.x,screen.y*lens.y,1.));
        float cp=cos(angle.y),sp=sin(angle.y),cy=cos(angle.x),sy=sin(angle.x);
        ray=vec3(ray.x,cp*ray.y+sp*ray.z,-sp*ray.y+cp*ray.z);
        ray=vec3(cy*ray.x+sy*ray.z,ray.y,-sy*ray.x+cy*ray.z);
        float longitude=atan(ray.x,ray.z);
        float u=.5+longitude/coverage;
        float v=.5-ray.y/(max(length(ray.xz),.00001)*verticalSpan);
        if(u<0.||u>1.||v<0.||v>1.)gl_FragColor=vec4(.09,.115,.12,1.);
        else gl_FragColor=vec4(texture2D(photo,vec2(u,v)).rgb,1.);
      }`);
    this.program=gl.createProgram();gl.attachShader(this.program,vertex);gl.attachShader(this.program,fragment);gl.linkProgram(this.program);
    if(!gl.getProgramParameter(this.program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(this.program));
    gl.useProgram(this.program);
    const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
    const p=gl.getAttribLocation(this.program,'position');gl.enableVertexAttribArray(p);gl.vertexAttribPointer(p,2,gl.FLOAT,false,0,0);
    this.uniforms={};for(const name of ['photo','lens','angle','coverage','verticalSpan'])this.uniforms[name]=gl.getUniformLocation(this.program,name);
    gl.uniform1i(this.uniforms.photo,0);
    this.texture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,this.texture);
    for(const axis of [gl.TEXTURE_WRAP_S,gl.TEXTURE_WRAP_T])gl.texParameteri(gl.TEXTURE_2D,axis,gl.CLAMP_TO_EDGE);
    for(const filter of [gl.TEXTURE_MIN_FILTER,gl.TEXTURE_MAG_FILTER])gl.texParameteri(gl.TEXTURE_2D,filter,gl.LINEAR);
    gl.clearColor(.09,.115,.12,1);gl.clear(gl.COLOR_BUFFER_BIT);
  }
  setImage(image){
    const gl=this.gl,max=Math.min(8192,gl.getParameter(gl.MAX_TEXTURE_SIZE));let source=image;
    this.ratio=image.naturalHeight/image.naturalWidth;
    if(image.naturalWidth>max){source=document.createElement('canvas');source.width=max;source.height=Math.round(max*this.ratio);source.getContext('2d').drawImage(image,0,0,source.width,source.height);}
    gl.bindTexture(gl.TEXTURE_2D,this.texture);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,false);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.RGB,gl.RGB,gl.UNSIGNED_BYTE,source);
    if(gl.getError()!==gl.NO_ERROR)throw new Error('Không tải được ảnh lên GPU. Hãy mở lại trang.');
  }
  draw({yaw,pitch,fov,coverage}){
    const gl=this.gl,c=this.canvas,dpr=Math.min(devicePixelRatio||1,2),w=Math.round(c.clientWidth*dpr),h=Math.round(c.clientHeight*dpr);
    if(c.width!==w||c.height!==h){c.width=w;c.height=h;}gl.viewport(0,0,w,h);
    const rad=Math.PI/180,t=Math.tan(fov*rad/2),aspect=w/h;
    gl.uniform2f(this.uniforms.lens,t*Math.min(1,aspect),t*Math.min(1,1/aspect));
    gl.uniform2f(this.uniforms.angle,yaw*rad,pitch*rad);
    gl.uniform1f(this.uniforms.coverage,coverage*rad);
    gl.uniform1f(this.uniforms.verticalSpan,coverage*rad*this.ratio);
    gl.drawArrays(gl.TRIANGLES,0,3);
  }
}
