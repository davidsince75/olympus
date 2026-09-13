/* ---------------- globe camera: inertia, zoom, idle drift ----------------
   The old camera set the latitude and longitude straight from the pointer and
   stopped dead on release, and rebuilt the screen-cell lookup table on every
   single frame of a drag. Both are fixed here: the camera carries angular
   momentum, the lookup table is rebuilt on a time budget rather than per
   frame, and the globe zooms. */

const CAM = {
  vlat:0, vlon:0,          // deg per second
  zoom:1, zTarget:1,
  idle:0,                  // performance.now() of the last deliberate interaction
  auto:false,
  lastLUT:0,
  dt:0.016                 // smoothed frame interval, so the throw test scales
};
const CAM_ZMIN=1, CAM_ZMAX=3.6;
const CAM_IDLE_MS=14000;   // before the globe starts turning on its own
const CAM_AUTO_DPS=1.6;    // deg per second of idle drift

function camTouch(){ CAM.idle=performance.now(); CAM.auto=false; }

/* How long a gap between the last pointer movement and the release still counts
   as a flick. A fixed 140 ms is wrong on a slow machine: at ten frames a second
   the gap between two genuine movements is already 100 ms, and a real flick gets
   read as a deliberate stop. Scale it with the frame the machine is actually
   managing. */
function camFlickGapMs(){ return Math.max(140, CAM.dt*1000*3); }

function camStep(dt){
  CAM.dt = CAM.dt*0.9 + Math.min(0.25, dt)*0.1;
  if(st.mode!=="GLOBE") return;
  // zoom eases toward its target so a wheel notch is not a jump
  if(Math.abs(CAM.zTarget-CAM.zoom)>0.0005){
    CAM.zoom += (CAM.zTarget-CAM.zoom)*Math.min(1, dt*11);
    st.gMoved=performance.now();
  }
  if(st.gDrag) return;
  if(Math.abs(CAM.vlat)>0.02 || Math.abs(CAM.vlon)>0.02){
    setCam(st.glat + CAM.vlat*dt, st.glon + CAM.vlon*dt);
    const k=Math.pow(0.0016, dt);        // ~1.5 s to come to rest
    CAM.vlat*=k; CAM.vlon*=k;
    if(Math.abs(CAM.vlat)<0.02) CAM.vlat=0;
    if(Math.abs(CAM.vlon)<0.02) CAM.vlon=0;
    return;
  }
  if(ocReduced()) return;
  if(!CAM.auto && performance.now()-CAM.idle > CAM_IDLE_MS) CAM.auto=true;
  if(CAM.auto) setCam(st.glat, st.glon + CAM_AUTO_DPS*dt);
}

function camZoom(f,anchor){
  CAM.zTarget=Math.max(CAM_ZMIN, Math.min(CAM_ZMAX, CAM.zTarget*f));
  camTouch();
}
