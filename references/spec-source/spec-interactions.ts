export function installActivation(trigger:HTMLButtonElement, robot:SVGElement, panel:HTMLElement, root:HTMLElement){
 let open=false; const close=panel.querySelector<HTMLButtonElement>('.close')!;
 function gesture(name:string){robot.classList.remove('wake','ack');void robot.getBoundingClientRect();robot.classList.add(name)}
 function show(v:boolean){open=v;root.dataset.open=v?'yes':'no';panel.inert=!v;trigger.setAttribute('aria-expanded',String(v));if(v){gesture('wake');close.focus()}else trigger.focus()}
 function click(e:MouseEvent){if(e.detail===0)show(!open);else if(e.detail===1)gesture('ack')}
 function double(e:MouseEvent){e.preventDefault();show(!open)}
 function escape(e:KeyboardEvent){if(e.key==='Escape'&&open)show(false)}
 function end(e:AnimationEvent){if(['activate','ack'].includes(e.animationName))robot.classList.remove('wake','ack')}
 const shut=()=>show(false);trigger.addEventListener('click',click);trigger.addEventListener('dblclick',double);close.addEventListener('click',shut);root.addEventListener('keydown',escape);robot.addEventListener('animationend',end);
 return {show,dispose(){trigger.removeEventListener('click',click);trigger.removeEventListener('dblclick',double);close.removeEventListener('click',shut);root.removeEventListener('keydown',escape);robot.removeEventListener('animationend',end)}};
}
