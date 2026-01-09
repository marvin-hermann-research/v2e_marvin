import os
import subprocess

class GenerateEvents:
    def __init__(self, device: int = 0):
        self.device = device

    def upsample(self, input_dir: str, output_dir: str):
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = str(self.device) if self.device >= 0 else ""

        cmd = [
            "conda", "run", "-n", "vid2e", "--no-capture-output",
            "python", "upsampling/upsample.py",
            "--input_dir", input_dir,
            "--output_dir", output_dir,
        ]
        print(f"[INFO] Starting upsampling: {input_dir} -> {output_dir}")
        subprocess.run(cmd, check=True, env=env)
        print("[INFO] Upsampling finished.")

    def generate_events(self, input_dir: str, output_dir: str,
                        contrast_threshold_pos: float = 0.2,
                        contrast_threshold_neg: float = 0.2,
                        refractory_period_ns: int = 0):
        cmd = [
            "conda", "run", "-n", "vid2e_torch", "--no-capture-output",
            "python", "esim_torch/scripts/generate_events.py",
            "--input_dir", input_dir,
            "--output_dir", output_dir,
            "--contrast_threshold_pos", str(contrast_threshold_pos),
            "--contrast_threshold_neg", str(contrast_threshold_neg),
            "--refractory_period_ns", str(refractory_period_ns),
        ]
        print(f"[INFO] Starting event generation: {input_dir} -> {output_dir}")
        subprocess.run(cmd, check=True)
        print("[INFO] Event generation finished.")


    def run_pipeline(self, video_input_dir: str, upsample_output_dir: str, events_output_dir: str,
                     contrast_threshold_pos: float = 0.2, contrast_threshold_neg: float = 0.2,
                     refractory_period_ns: int = 0):
        self.upsample(video_input_dir, upsample_output_dir)
        self.generate_events(upsample_output_dir, events_output_dir,
                             contrast_threshold_pos, contrast_threshold_neg, refractory_period_ns)
        print("[INFO] Pipeline finished successfully.")

def main():
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--video_input_dir", required=True)
    p.add_argument("--upsample_output_dir", required=True)
    p.add_argument("--events_output_dir", required=True)
    p.add_argument("--device", type=int, default=0, help="GPU id, -1 for CPU")
    p.add_argument("--ct_pos", type=float, default=0.2)
    p.add_argument("--ct_neg", type=float, default=0.2)
    p.add_argument("--refractory_period_ns", type=int, default=0)

    args = p.parse_args()

    pipeline = GenerateEvents(device=args.device)
    pipeline.run_pipeline(
        video_input_dir=args.video_input_dir,
        upsample_output_dir=args.upsample_output_dir,
        events_output_dir=args.events_output_dir,
        contrast_threshold_pos=args.ct_pos,
        contrast_threshold_neg=args.ct_neg,
        refractory_period_ns=args.refractory_period_ns,
    )

if __name__ == "__main__":
    main()
