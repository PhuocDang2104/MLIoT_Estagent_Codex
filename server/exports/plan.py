"""A deterministic edit derived only from an immutable publication."""
import math
from fastapi import HTTPException


def plan(snapshot, aspect):
    if aspect not in {'portrait', 'landscape'}:
        raise HTTPException(422, 'Choose portrait or landscape')
    tracks = snapshot['audio'].get('narration') or []
    scenes = []
    start = 0
    opening = next(i for i,s in enumerate(snapshot['scenes']) if s['id']==snapshot['start_scene_id'])
    ordered = snapshot['scenes'][opening:] + snapshot['scenes'][:opening]
    for scene in ordered:
        narration = next((n for n in tracks if n['scene_id'] == scene['id'] and n['locale'] == snapshot['locale']), None)
        duration = max(3, math.ceil((narration['track']['duration_seconds'] + .3) * 24) / 24) if narration else 3
        scenes.append(dict(scene, start=start, duration=duration, narration=narration))
        start += duration
    if start > 180:
        raise HTTPException(422, 'This snapshot exceeds the 180 second prototype limit; recordings are not truncated.')
    recorded = sum(s['narration'] is not None for s in scenes)
    music = snapshot['audio'].get('music')
    return dict(tour_id=snapshot['id'], title=snapshot['title'], locale=snapshot['locale'], aspect=aspect,
                width=720 if aspect == 'portrait' else 1280, height=1280 if aspect == 'portrait' else 720,
                duration=round(start, 6), scenes=scenes, music=music,
                audio_status='complete' if recorded == len(scenes) else 'partial' if recorded or music else 'silent',
                notice='Editorial sequence of supplied photos/panoramas, not room adjacency or 3D. Audio uses the published snapshot tracks matching its source language, including declared AI-generated narration.')
