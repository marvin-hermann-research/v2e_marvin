import argparse
import os
import subprocess
import sys
import tempfile


def run_cmd(cmd, cwd=None):
    subprocess.run(cmd, check=True, cwd=cwd)  # cwd controls how ../ paths are resolved



def main():
    ap = argparse.ArgumentParser()

    # script paths (optional)
    ap.add_argument("--render_script", default="render_events.py")
    ap.add_argument("--sbs_script", default="side_by_side.py")

    # input videos
    ap.add_argument("--original_dir", required=True, help="First video (e.g. RGB/base video)")
    ap.add_argument("--events_dir", required=True)
    ap.add_argument("--timestamps_dir", default=None)

    # event render settings
    ap.add_argument("--sensor_w", type=int, default=320)
    ap.add_argument("--sensor_h", type=int, default=256)
    ap.add_argument("--fps", type=float, default=120.0)
    ap.add_argument("--tau_ms", type=float, default=30.0)
    ap.add_argument("--max_frames", type=int, default=None)

    # side-by-side settings
    ap.add_argument("--output_dir", required=True, help="Final output (1920x1080) mp4")
    ap.add_argument("--gap", type=int, default=15)
    ap.add_argument("--bg", type=int, default=0)
    ap.add_argument("--codec", default="mp4v")
    ap.add_argument("--fps_out", type=float, default=None)
    ap.add_argument("--end_mode", choices=["min", "hold"], default="min")

    # temp handling
    ap.add_argument("--keep_temp", action="store_true", help="Keep intermediate rendered events video")
    ap.add_argument("--temp_out", default=None, help="Optional fixed path for intermediate events mp4")

    args = ap.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    render_script = os.path.join(script_dir, args.render_script)
    sbs_script = os.path.join(script_dir, args.sbs_script)

    child_cwd = script_dir


    # Pick intermediate output path
    temp_path = args.temp_out
    temp_file = None

    if temp_path is None:
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        temp_path = temp_file.name
        temp_file.close()

    try:
        # 1) Render events video (video2 for the comparison)
        cmd_render = [
            sys.executable, render_script,
            "--events_dir", "../" + args.events_dir,
            "--out", temp_path,
            "--sensor_w", str(args.sensor_w),
            "--sensor_h", str(args.sensor_h),
            "--fps", str(args.fps),
            "--tau_ms", str(args.tau_ms),
        ]
        if args.timestamps_dir is not None:
            cmd_render += ["--timestamps", "../" + args.timestamps_dir]
        if args.max_frames is not None:
            cmd_render += ["--max_frames", str(args.max_frames)]

        run_cmd(cmd_render, cwd=child_cwd)

        # 2) Side-by-side composition to 1920x1080
        cmd_sbs = [
            sys.executable, sbs_script,
            "--video1", "../" + args.original_dir,
            "--video2", temp_path,
            "--out", "../" + args.output_dir,
            "--gap", str(args.gap),
            "--bg", str(args.bg),
            "--codec", args.codec,
            "--end_mode", args.end_mode,
        ]
        if args.fps_out is not None:
            cmd_sbs += ["--fps_out", str(args.fps_out)]

        run_cmd(cmd_sbs, cwd=child_cwd)

    finally:
        if (not args.keep_temp) and (args.temp_out is None):
            try:
                os.remove(temp_path)
            except OSError:
                pass


if __name__ == "__main__":
    main()
