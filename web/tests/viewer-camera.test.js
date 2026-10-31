import {test} from 'node:test';
import assert from 'node:assert/strict';
import {constrainView} from '../panorama.js';

// Independently project screen rays using the shader's cylinder coordinates.
function bounds(view,aspect,ratio){
 const r=Math.PI/180,t=Math.tan(view.fov*r/2),x=t*Math.min(1,aspect),y=t*Math.min(1,1/aspect),p=view.pitch*r,c=view.coverage*r;
 for(const sx of [-1,-.5,0,.5,1])for(const sy of [-1,-.5,0,.5,1]){
  const rx=sx*x,ry=Math.cos(p)*sy*y+Math.sin(p),rz=-Math.sin(p)*sy*y+Math.cos(p);
  const longitude=Math.atan2(rx,rz)+view.yaw*r;
  if(view.coverage<360)assert.ok(Math.abs(longitude)<c/2,JSON.stringify({view,aspect,ratio,sx,sy,longitude}));
  assert.ok(Math.abs(ry/Math.hypot(rx,rz))<c*ratio/2,JSON.stringify({view,aspect,ratio,sx,sy}));
 }
}
test('every visible ray stays within captured panorama after extreme pan, pitch, zoom and resize',()=>{
 for(const coverage of [30,90,180,240,359,360])for(const ratio of [.03,.15,.5,1])for(const aspect of [.38,1,1.9,3])for(const pitch of [-65,0,65])for(const yaw of [-720,-120,0,120,720])for(const fov of [20,70,110]){
  const view=constrainView({yaw,pitch,fov,coverage},aspect,ratio);bounds(view,aspect,ratio);
 }
});
test('full 360 panorama wraps while partial panoramas stop at photographed edges',()=>{
 assert.equal(constrainView({yaw:370,pitch:0,fov:70,coverage:360},1,.5).yaw,10);
 const view=constrainView({yaw:180,pitch:0,fov:70,coverage:240},1,.5);
 assert.ok(view.yaw<86&&view.yaw>84);
});
