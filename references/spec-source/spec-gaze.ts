/** Adapted from SPEC 4.1. Pointer data stays local. */
export function installGaze(root: HTMLElement, gaze: SVGGElement): () => void {
 let x=0,y=0,tx=0,ty=0,raf=0;
 const reduced=matchMedia('(prefers-reduced-motion: reduce)');
 function frame(){x+=(tx-x)*.55;y+=(ty-y)*.55;gaze.setAttribute('transform',`translate(${x.toFixed(2)} ${y.toFixed(2)})`);raf=Math.abs(tx-x)+Math.abs(ty-y)>.03?requestAnimationFrame(frame):0;}
 function target(a:number,b:number){tx=a;ty=b;if(!raf)raf=requestAnimationFrame(frame);}
 function move(e:PointerEvent){if(reduced.matches||root.dataset.motion==='off')return;const m=(gaze.parentNode as SVGGraphicsElement).getScreenCTM();if(!m)return;const p=new DOMPoint(e.clientX,e.clientY).matrixTransform(m.inverse());const dx=p.x-80,dy=p.y-92,d=Math.hypot(dx,dy),n=Math.max(d,1);target(dx/n*10.5*(1-Math.exp(-d/25)),dy/n*6.3*(1-Math.exp(-d/25)));}
 function leave(){target(0,0)}
 root.addEventListener('pointermove',move);root.addEventListener('pointerleave',leave);
 return ()=>{root.removeEventListener('pointermove',move);root.removeEventListener('pointerleave',leave);cancelAnimationFrame(raf);};
}
