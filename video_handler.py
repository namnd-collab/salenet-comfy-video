"""Queue worker: execute bundled I2V graph and return a bounded MP4 result.

Models must already exist on the attached volume. No model download at runtime.
"""
import base64
import copy
import json
import os
import pathlib
import time
import uuid

import requests
import runpod

API = 'http://127.0.0.1:8188'
ROOT = pathlib.Path('/comfyui')
TEMPLATE = pathlib.Path('/kit/workflows/i2v.json')


def handler(job):
    args = job.get('input', {})
    image = args.get('image_base64')
    prompt = args.get('prompt')
    if not isinstance(image, str) or not isinstance(prompt, str) or not prompt.strip():
        raise ValueError('image_base64 and nonempty prompt required')
    if len(image) > 12 * 1024 * 1024 or len(prompt) > 12000:
        raise ValueError('Input too large')
    data = base64.b64decode(image.split(',', 1)[-1], validate=True)
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        extension = '.png'
    elif data.startswith(b'\xff\xd8\xff'):
        extension = '.jpg'
    else:
        raise ValueError('Only PNG/JPEG inputs supported')
    seed = args.get('seed', 1)
    if type(seed) is not int or not 0 <= seed < 2**63:
        raise ValueError('Invalid seed')
    token = uuid.uuid4().hex
    filename = token + extension
    input_path = ROOT / 'input' / filename
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_bytes(data)
    graph = copy.deepcopy(json.loads(TEMPLATE.read_text()))
    graph['227']['inputs']['text'] = prompt
    for node in graph.values():
        kind, inputs = node['class_type'], node['inputs']
        if kind == 'LoadImage':
            inputs['image'] = filename
        if 'noise_seed' in inputs:
            inputs['noise_seed'] = seed
        if kind == 'VHS_VideoCombine':
            inputs['filename_prefix'] = 'kit/' + token
    deadline = time.monotonic() + 1800
    try:
        while True:
            try:
                schema = requests.get(API + '/object_info', timeout=10)
                schema.raise_for_status()
                info = schema.json()
                break
            except requests.RequestException:
                if time.monotonic() > deadline:
                    raise RuntimeError('ComfyUI did not start')
                time.sleep(3)
        missing = sorted({n['class_type'] for n in graph.values()} - info.keys())
        if missing:
            raise RuntimeError('Missing nodes: ' + ', '.join(missing))
        for node in graph.values():
            spec = info[node['class_type']]['input']
            fields = {**spec.get('required', {}), **spec.get('optional', {})}
            for key, value in node['inputs'].items():
                field = fields.get(key)
                if isinstance(value, str) and field and isinstance(field[0], list) and value not in field[0]:
                    raise RuntimeError('Unavailable model/choice: ' + key + '=' + value)
        response = requests.post(API + '/prompt', json={'prompt': graph}, timeout=30)
        response.raise_for_status()
        result = response.json()
        if result.get('node_errors') or not result.get('prompt_id'):
            raise RuntimeError('Workflow validation failed: ' + json.dumps(result)[:3000])
        prompt_id = result['prompt_id']
        while time.monotonic() < deadline:
            response = requests.get(API + '/history/' + prompt_id, timeout=30)
            response.raise_for_status()
            record = response.json().get(prompt_id)
            if not record:
                time.sleep(3)
                continue
            if record.get('status', {}).get('status_str') == 'error':
                raise RuntimeError('ComfyUI execution failed: ' + json.dumps(record['status'])[:3000])
            outputs = record.get('outputs', {})
            for output in outputs.values():
                for item in output.get('gifs', []) + output.get('videos', []):
                    if item.get('type') != 'output' or not item.get('filename', '').endswith('.mp4'):
                        continue
                    output_root = (ROOT / 'output').resolve()
                    path = (output_root / item.get('subfolder', '') / item['filename']).resolve()
                    if not path.is_relative_to(output_root) or not path.is_file():
                        raise RuntimeError('Invalid output path')
                    if path.stat().st_size > 8 * 1024 * 1024:
                        raise RuntimeError('MP4 exceeds inline 8 MiB limit; durable object storage required')
                    return {'video_base64': base64.b64encode(path.read_bytes()).decode(),
                            'mime_type': 'video/mp4', 'filename': token + '.mp4'}
            raise RuntimeError('Completed workflow produced no MP4')
        raise TimeoutError('Render exceeded worker limit')
    finally:
        input_path.unlink(missing_ok=True)


if __name__ == '__main__':
    runpod.serverless.start({'handler': handler})
