import argparse
import cv2
import numpy as np

OUT_W = 1920
OUT_H = 1080


def open_video(path):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError("Could not open: {}".format(path))
    return cap


def get_size(cap):
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    return w, h


def get_fps(cap, name):
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    if fps <= 0:
        raise RuntimeError("Could not read FPS for {} (maybe variable FPS file).".format(name))
    return fps


def compute_layout(in_w, in_h, gap):
    max_w_each = (OUT_W - gap) / 2.0
    max_h = OUT_H

    scale_w = max_w_each / float(in_w)
    scale_h = max_h / float(in_h)
    scale = min(scale_w, scale_h, 1.0)  # never upscale

    rw = int(round(in_w * scale))
    rh = int(round(in_h * scale))

    total_w = 2 * rw + gap
    x_left = int((OUT_W - total_w) / 2)
    x_right = x_left + rw + gap
    y_top = int((OUT_H - rh) / 2)

    return scale, rw, rh, x_left, x_right, y_top


def read_next(cap):
    ok, frame = cap.read()
    if not ok:
        return None
    return frame


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video1", required=True)
    ap.add_argument("--video2", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--gap", type=int, default=15)
    ap.add_argument("--bg", type=int, default=0)
    ap.add_argument("--codec", default="mp4v")
    ap.add_argument("--fps_out", type=float, default=None)
    ap.add_argument("--end_mode", choices=["min", "hold"], default="min")
    args = ap.parse_args()

    cap1 = open_video(args.video1)
    cap2 = open_video(args.video2)

    w1, h1 = get_size(cap1)
    w2, h2 = get_size(cap2)
    if (w1 != w2) or (h1 != h2):
        raise ValueError("Both videos must have the same size (got {}x{} and {}x{}).".format(w1, h1, w2, h2))

    fps1 = get_fps(cap1, "video1")
    fps2 = get_fps(cap2, "video2")
    fps_out = args.fps_out if args.fps_out is not None else max(fps1, fps2)

    scale, rw, rh, x_left, x_right, y_top = compute_layout(w1, h1, args.gap)
    interp = cv2.INTER_AREA

    fourcc = cv2.VideoWriter_fourcc(*args.codec)
    writer = cv2.VideoWriter(args.out, fourcc, fps_out, (OUT_W, OUT_H))
    if not writer.isOpened():
        raise RuntimeError("Could not open VideoWriter: {}".format(args.out))

    frame1 = read_next(cap1)
    frame2 = read_next(cap2)
    if frame1 is None or frame2 is None:
        raise RuntimeError("Could not read first frame from both videos.")

    idx1 = 0
    idx2 = 0
    ended1 = False
    ended2 = False
    out_idx = 0

    while True:
        t = out_idx / float(fps_out)

        want1 = int(t * fps1)
        want2 = int(t * fps2)

        while (not ended1) and (idx1 < want1):
            f = read_next(cap1)
            if f is None:
                ended1 = True
                break
            frame1 = f
            idx1 += 1

        while (not ended2) and (idx2 < want2):
            f = read_next(cap2)
            if f is None:
                ended2 = True
                break
            frame2 = f
            idx2 += 1

        if args.end_mode == "min":
            if ended1 or ended2:
                break
        else:
            if ended1 and ended2:
                break

        left = frame1
        right = frame2
        if scale != 1.0:
            left = cv2.resize(left, (rw, rh), interpolation=interp)
            right = cv2.resize(right, (rw, rh), interpolation=interp)

        canvas = np.full((OUT_H, OUT_W, 3), int(args.bg), dtype=np.uint8)
        canvas[y_top:y_top + rh, x_left:x_left + rw] = left
        canvas[y_top:y_top + rh, x_right:x_right + rw] = right

        writer.write(canvas)
        out_idx += 1

    cap1.release()
    cap2.release()
    writer.release()


if __name__ == "__main__":
    main()
