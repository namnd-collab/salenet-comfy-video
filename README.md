# SaleNet ComfyUI Serverless — initial I2V worker

Target repository: namnd-collab/salenet-comfy-video.
Build context: repository root. Dockerfile: Dockerfile.

Status: prepared source; image has NOT passed a full build or GPU acceptance.
This worker only enables the derived workflow 02 (Wan 2.2 I2V 14B FP8 + Lightning).
It bypasses optional SageAttention and empty rgthree stacks; originals are preserved separately.
It is not the third-party TI2V 5B template.

Attach the existing Wan2.1 volume in EU-RO-1, only after confirming model paths
against model-manifest.json. No model weights or credentials are bundled.
Volume files are discovered under /runpod-volume/models.

Deploy from GitHub in RunPod. Start with active workers 0 and max workers 1.
Do not submit GPU inference until a short test is explicitly authorized.

Input: input.prompt, input.image_base64 (PNG/JPEG), optional input.seed.
Output: video_base64, mime_type, filename. Inline MP4 limit: 8 MiB.
Longer/larger results require durable output storage integration.

KIT still requires a queue adapter for /run and /status. Its existing direct
ComfyUI Pod URL field cannot be used as a Serverless queue endpoint.

Checks performed: graph link audit, Python syntax, two mocked handler tests.
Remaining: cloud build, actual node/schema/model validation, GPU resource test,
queue payload limits, durable media upload and KIT integration.
