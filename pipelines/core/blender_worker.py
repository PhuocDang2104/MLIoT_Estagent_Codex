"""Bounded local geometry worker. Executes only the repository-owned builder."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def configured_worker(env, root):
    # Explicit off also keeps existing keyless/external-worker deployments unchanged.
    mode = env.get('STUDIO_GEOMETRY', 'auto')
    if mode not in ('auto','off','blender'):
        raise ValueError('STUDIO_GEOMETRY must be auto, off or blender')
    if mode == 'off':
        return None
    executable = env.get('STUDIO_BLENDER_EXECUTABLE') or shutil.which('blender')
    if not executable and os.name == 'nt':
        candidates = sorted(Path(os.environ.get('ProgramFiles', 'C:/Program Files')).glob('Blender Foundation/Blender */blender.exe'))
        executable = str(candidates[-1]) if candidates else None
    if not executable:
        if mode == 'blender':
            raise ValueError('STUDIO_BLENDER_EXECUTABLE is required when Blender is not on PATH')
        return None
    return BlenderWorker(executable, Path(root)/'geometry', int(env.get('STUDIO_BLENDER_TIMEOUT', '180')))


class BlenderWorker:
    requires_scene_plan = True

    def __init__(self, executable, root, timeout=180):
        self.executable = str(Path(executable).resolve())
        if not Path(self.executable).is_file():
            raise ValueError('Blender executable does not exist')
        self.root = Path(root)
        self.timeout = max(10, min(600, timeout))
        self.builder = Path(__file__).with_name('build_house.py')

    def build(self, project, rooms, connections, assets):
        plan = project['modeling_plan']  # validated in the graph before entering this boundary
        if plan['status'] == 'needs_clarification':
            raise ValueError('Layout clarification is required')
        payload = json.dumps(plan, sort_keys=True, ensure_ascii=False).encode()
        digest = hashlib.sha256(payload+self.builder.read_bytes()).hexdigest()
        # No user-provided path component reaches the filesystem.
        identity = hashlib.sha256(str(project['generation_id']).encode()).hexdigest()[:24]
        directory = self.root/identity/digest
        directory.mkdir(parents=True, exist_ok=True)
        spec = directory/'scene.json'
        glb, blend = directory/'house.glb', directory/'house.blend'
        complete = directory/'complete.json'
        spec.write_bytes(payload)
        cached = None
        if complete.is_file() and glb.is_file() and blend.is_file():
            try:
                cached = json.loads(complete.read_text())
                if cached['glb_sha256'] != hashlib.sha256(glb.read_bytes()).hexdigest():
                    cached = None
            except (ValueError, KeyError):
                cached = None
        if cached is None:
            # Completed marker is written last; partial exports are never accepted as cache hits.
            with (directory/'blender.log').open('wb') as log:
                process = subprocess.run([self.executable, '--background', '--factory-startup',
                    '--disable-autoexec', '--threads', '2', '--python-exit-code', '1',
                    '--python', str(self.builder), '--', str(spec.resolve()), str(directory.resolve())],
                    stdout=log, stderr=subprocess.STDOUT, timeout=self.timeout,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                    env={k:v for k,v in os.environ.items() if not any(s in k.upper() for s in ('KEY','TOKEN','SECRET','PASSWORD'))})
            if process.returncode or not glb.is_file() or not blend.is_file():
                raise ValueError('Blender build failed; inspect the private worker log')
            if not 100 <= glb.stat().st_size <= 20*1024*1024:
                raise ValueError('Blender output exceeds the model size budget')
            complete.write_text(json.dumps({'glb_sha256': hashlib.sha256(glb.read_bytes()).hexdigest()}))
        anchors = {}
        representatives = set()
        for space in plan['spaces']:
            points = space['polygon']
            cx,cz = sum(p['x'] for p in points)/len(points),sum(p['z'] for p in points)/len(points)
            captures = sorted([c for c in plan['captures'] if c['room_id'] == space['id']],
                              key=lambda c:(c['position']['x']-cx)**2+(c['position']['z']-cz)**2)
            representatives.update(c['checkpoint_id'] for c in captures[:2 if len(captures)>3 else 1])
        for c in plan['captures']:
            p = c['position']
            anchors[c['checkpoint_id']] = {'room_id': c['room_id'], 'position': [p['x'],p['y'],p['z']],
                'heading': c['heading'], 'accuracy': c['accuracy'],
                'dollhouse_visible': c['checkpoint_id'] in representatives}
        (directory/'checkpoints.json').write_text(json.dumps(anchors,indent=2))
        return {'glb': glb.read_bytes(), 'anchors': anchors,
                'metadata': {'units':'meters', 'up_axis':'Y', 'scale':plan['scale'],
                             'builder':'blender-house-v1', 'plan_sha256':hashlib.sha256(payload).hexdigest()}}
