FROM runpod/worker-comfyui:5.10.0-base@sha256:e9d18d3db15839ebb10c10c824109fc2956f31ef7bf21916220c008855b0d538
RUN git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git /comfyui/custom_nodes/ComfyUI-VideoHelperSuite \
    && cd /comfyui/custom_nodes/ComfyUI-VideoHelperSuite \
    && git checkout 4d907bee61e92c2e65af3bd6383a4e4d356126d1 \
    && python -m pip install -r requirements.txt
COPY i2v.json /kit/workflows/i2v.json
COPY video_handler.py /handler.py
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml
RUN python -m py_compile /handler.py \
    && cd /comfyui && python main.py --quick-test-for-ci --cpu

