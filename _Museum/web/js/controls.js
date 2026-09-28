import * as THREE from 'three';

const EYE_HEIGHT = 1.7;
const MOVE_SPEED = 4.2; // m/s
const COLLIDE_RADIUS = 0.35;
const DOWN = new THREE.Vector3(0, -1, 0);
// Floor-following searches a narrow band around the player's feet (enough to
// climb stair treads smoothly) rather than "nearest floor anywhere below" --
// this building stacks a ground floor and a mezzanine at the same XZ
// footprint in places, and a wide-open downward search would snap the player
// up onto the floor of the level above.
const STEP_UP = 0.5;
const STEP_DOWN = 1.0;

export function createControls(camera, domElement, getCollidables) {
  const keys = { forward: false, back: false, left: false, right: false };
  let yaw = 0;
  let pitch = 0;
  let engaged = false;      // WASD movement is active
  let pointerLocked = false; // true pointer-lock look (mouse always rotates)
  let dragLooking = false;   // fallback: rotate only while a mouse button is held

  const euler = new THREE.Euler(0, 0, 0, 'YXZ');
  const raycaster = new THREE.Raycaster();
  const forwardVec = new THREE.Vector3();
  const rightVec = new THREE.Vector3();
  const moveVec = new THREE.Vector3();
  const rayOrigin = new THREE.Vector3();

  function onKeyDown(e) {
    switch (e.code) {
      case 'KeyW': case 'ArrowUp': keys.forward = true; break;
      case 'KeyS': case 'ArrowDown': keys.back = true; break;
      case 'KeyA': case 'ArrowLeft': keys.left = true; break;
      case 'KeyD': case 'ArrowRight': keys.right = true; break;
    }
  }
  function onKeyUp(e) {
    switch (e.code) {
      case 'KeyW': case 'ArrowUp': keys.forward = false; break;
      case 'KeyS': case 'ArrowDown': keys.back = false; break;
      case 'KeyA': case 'ArrowLeft': keys.left = false; break;
      case 'KeyD': case 'ArrowRight': keys.right = false; break;
    }
  }
  function applyLook(movementX, movementY) {
    yaw -= movementX * 0.0022;
    pitch -= movementY * 0.0022;
    pitch = Math.max(-Math.PI / 2 + 0.05, Math.min(Math.PI / 2 - 0.05, pitch));
    euler.set(pitch, yaw, 0);
    camera.quaternion.setFromEuler(euler);
  }
  function onMouseMove(e) {
    if (pointerLocked || dragLooking) {
      applyLook(e.movementX || 0, e.movementY || 0);
    }
  }
  function onLockChange() {
    pointerLocked = document.pointerLockElement === domElement;
    engaged = engaged || pointerLocked;
  }
  function onPointerDown(e) {
    if (e.button !== 0) return;
    engaged = true;
    if (!pointerLocked) dragLooking = true;
  }
  function onPointerUp() { dragLooking = false; }

  domElement.addEventListener('click', () => {
    engaged = true;
    const p = domElement.requestPointerLock();
    if (p && typeof p.catch === 'function') p.catch(() => {});
  });
  domElement.addEventListener('pointerdown', onPointerDown);
  document.addEventListener('pointerup', onPointerUp);
  document.addEventListener('pointerlockchange', onLockChange);
  document.addEventListener('keydown', onKeyDown);
  document.addEventListener('keyup', onKeyUp);
  document.addEventListener('mousemove', onMouseMove);

  function blocked(originVec, dirVec, dist, walls) {
    if (dist <= 0) return false;
    raycaster.set(originVec, dirVec);
    raycaster.far = dist;
    const hits = raycaster.intersectObjects(walls, false);
    return hits.length > 0 && hits[0].distance < dist;
  }

  function tryMove(delta) {
    if (moveVec.lengthSq() === 0) return;
    moveVec.normalize().multiplyScalar(MOVE_SPEED * delta);
    const { walls } = getCollidables();

    // Move on each horizontal axis independently so sliding along a wall works.
    // Collision rays run 1.2 m above the player's feet (not at absolute y=1.2), so walls
    // on upper floors collide and ground-floor walls below them don't.
    const rayY = camera.position.y - EYE_HEIGHT + 1.2;
    if (Math.abs(moveVec.x) > 0) {
      rayOrigin.set(camera.position.x, rayY, camera.position.z);
      const d = new THREE.Vector3(Math.sign(moveVec.x), 0, 0);
      if (!blocked(rayOrigin, d, Math.abs(moveVec.x) + COLLIDE_RADIUS, walls)) {
        camera.position.x += moveVec.x;
      }
    }
    if (Math.abs(moveVec.z) > 0) {
      rayOrigin.set(camera.position.x, rayY, camera.position.z);
      const d = new THREE.Vector3(0, 0, Math.sign(moveVec.z));
      if (!blocked(rayOrigin, d, Math.abs(moveVec.z) + COLLIDE_RADIUS, walls)) {
        camera.position.z += moveVec.z;
      }
    }
  }

  function followFloor() {
    const { floors } = getCollidables();
    if (!floors || floors.length === 0) return;
    const feetY = camera.position.y - EYE_HEIGHT;
    rayOrigin.set(camera.position.x, feetY + STEP_UP, camera.position.z);
    raycaster.set(rayOrigin, DOWN);
    raycaster.far = STEP_UP + STEP_DOWN;
    const hits = raycaster.intersectObjects(floors, false);
    if (hits.length > 0) {
      camera.position.y = hits[0].point.y + EYE_HEIGHT;
    }
  }

  function update(delta) {
    camera.getWorldDirection(forwardVec);
    forwardVec.y = 0;
    forwardVec.normalize();
    rightVec.crossVectors(forwardVec, camera.up).normalize();

    moveVec.set(0, 0, 0);
    if (keys.forward) moveVec.add(forwardVec);
    if (keys.back) moveVec.sub(forwardVec);
    if (keys.right) moveVec.add(rightVec);
    if (keys.left) moveVec.sub(rightVec);

    tryMove(delta);
    followFloor();
  }

  function isLocked() { return engaged; }
  function setPosition(x, y, z) { camera.position.set(x, y, z); }
  function engage() {
    engaged = true;
    const p = domElement.requestPointerLock();
    if (p && typeof p.catch === 'function') p.catch(() => {});
  }

  function dispose() {
    document.removeEventListener('pointerlockchange', onLockChange);
    document.removeEventListener('keydown', onKeyDown);
    document.removeEventListener('keyup', onKeyUp);
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('pointerup', onPointerUp);
    domElement.removeEventListener('pointerdown', onPointerDown);
  }

  return { update, isLocked, setPosition, engage, dispose, EYE_HEIGHT };
}
