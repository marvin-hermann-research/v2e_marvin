import subprocess

class GenerateEvents:
    def __init__(self, device: int = 0):
        """
        device: GPU id (0,1,...) oder -1 für CPU
        """
        self.device = device

    def upsample(self, input_dir: str, output_dir: str):
        device_env = str(self.device) if self.device >= 0 else ""
        cmd = f"""
        conda activate vid2e && \
        CUDA_VISIBLE_DEVICES={device_env} python upsampling/upsample.py \
            --input_dir {input_dir} \
            --output_dir {output_dir}
        """
        print(f"[INFO] Starting upsampling: {input_dir} -> {output_dir}")
        subprocess.run(cmd, shell=True, check=True, executable="/bin/bash")
        print("[INFO] Upsampling finished.")

    def generate_events(self, input_dir: str, output_dir: str,
                        contrast_threshold_pos: float = 0.2,
                        contrast_threshold_neg: float = 0.2,
                        refractory_period_ns: int = 0):
        cmd = f"""
        conda activate vid2e_torch && \
        python esim_torch/scripts/generate_events.py \
            --input_dir {input_dir} \
            --output_dir {output_dir} \
            --contrast_threshold_pos {contrast_threshold_pos} \
            --contrast_threshold_neg {contrast_threshold_neg} \
            --refractory_period_ns {refractory_period_ns}
        """
        print(f"[INFO] Starting event generation: {input_dir} -> {output_dir}")
        subprocess.run(cmd, shell=True, check=True, executable="/bin/bash")
        print("[INFO] Event generation finished.")

    def run_pipeline(self, video_input_dir: str, upsample_output_dir: str, events_output_dir: str,
                     contrast_threshold_pos: float = 0.2, contrast_threshold_neg: float = 0.2,
                     refractory_period_ns: int = 0):
        self.upsample(video_input_dir, upsample_output_dir)
        self.generate_events(upsample_output_dir, events_output_dir,
                             contrast_threshold_pos, contrast_threshold_neg, refractory_period_ns)
        print("[INFO] Pipeline finished successfully.")
