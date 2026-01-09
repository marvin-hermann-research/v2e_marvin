from typing import Optional, Tuple

import os
import glob
import math
import numpy as np
import cv2


class EventVideoRenderer:
    """
    Render events (x,y,t,p) into a constant-FPS MP4.

    - timestamps.txt contains seconds (float) -> converted to ns internally.
    - event t is already nanoseconds (int64).
    - p can be 0/1 or -1/+1; positive means p > 0.
    """

    def __init__(
        self,
        events_dir: str,
        out_path: str,
        sensor_size: Tuple[int, int],
        timestamps_path: Optional[str] = None,
        fps: float = 120.0,
        tau_ms: float = 30.0,
        background: int = 0,
        codec: str = "mp4v",
        pos_bgr: Tuple[int, int, int] = (255, 150, 4),     # blue-ish
        neg_bgr: Tuple[int, int, int] = (105, 91, 244),    # red-ish
        overlap_bgr: Tuple[int, int, int] = (204, 0, 204), # magenta
    ):
        self.events_dir = events_dir
        self.out_path = out_path
        self.timestamps_path = timestamps_path

        self.w, self.h = int(sensor_size[0]), int(sensor_size[1])

        if fps <= 0:
            raise ValueError("fps must be > 0")
        self.fps = float(fps)
        self.dt_ns = int(round(1e9 / self.fps))

        if tau_ms <= 0:
            raise ValueError("tau_ms must be > 0")
        self.tau_ns = float(tau_ms) * 1e6

        self.background = int(background)
        self.codec = str(codec)

        self.pos_bgr = np.array(pos_bgr, dtype=np.float32)
        self.neg_bgr = np.array(neg_bgr, dtype=np.float32)
        self.ovl_bgr = np.array(overlap_bgr, dtype=np.float32)

        self.pos_surf = np.zeros((self.h, self.w), dtype=np.float32)
        self.neg_surf = np.zeros((self.h, self.w), dtype=np.float32)

        self.files = sorted(glob.glob(os.path.join(events_dir, "*.npz")))
        if len(self.files) == 0:
            raise FileNotFoundError("No .npz files found in {}".format(events_dir))

        self.frame_times_ns = self._read_timestamps_seconds_as_ns(timestamps_path)

        # streaming cursor
        self.file_idx = 0
        self.cur = self._load_npz(self.files[0])
        self.ptr = 0

        self.t0_ns, self.t1_ns = self._compute_render_range()

    # ---------- public ----------

    def render(self, max_frames: Optional[int] = None):
        writer = self._open_writer()

        self._seek_to_time(self.t0_ns)

        start_frame = self.t0_ns // self.dt_ns
        end_frame = (self.t1_ns + self.dt_ns - 1) // self.dt_ns
        n_frames = int(end_frame - start_frame)

        if max_frames is not None:
            n_frames = min(n_frames, int(max_frames))

        for i in range(n_frames):
            frame_start = (start_frame + i) * self.dt_ns
            frame_end = frame_start + self.dt_ns

            self._decay()

            x, y, t_ns, p01 = self._pop_events_until(frame_end)
            if t_ns.size != 0:
                keep = (t_ns >= frame_start)
                x, y, t_ns, p01 = x[keep], y[keep], t_ns[keep], p01[keep]

            self._accumulate(x, y, t_ns, p01, frame_end)

            frame = self._compose_frame()
            writer.write(frame)

            if self.file_idx >= len(self.files):
                break

        writer.release()
        return self.out_path

    # ---------- setup helpers ----------

    def _open_writer(self):
        fourcc = cv2.VideoWriter_fourcc(*self.codec)
        writer = cv2.VideoWriter(self.out_path, fourcc, self.fps, (self.w, self.h))
        if not writer.isOpened():
            raise RuntimeError("Could not open VideoWriter (codec/path issue).")
        return writer

    def _compute_render_range(self):
        # event range (ns)
        t0e, t1e = self._event_range_ns(self.files[0], self.files[-1])

        # if timestamps exist, prefer them
        if self.frame_times_ns is not None and self.frame_times_ns.size >= 2:
            t0 = int(self.frame_times_ns[0])
            diffs = np.diff(self.frame_times_ns)
            diffs = diffs[diffs > 0]
            dt = int(np.median(diffs)) if diffs.size else self.dt_ns
            t1 = int(self.frame_times_ns[-1] + dt)
            return t0, t1

        return int(t0e), int(t1e)

    # ---------- IO ----------

    @staticmethod
    def _read_timestamps_seconds_as_ns(path: Optional[str]):
        if path is None:
            return None
        if not os.path.exists(path):
            raise FileNotFoundError("timestamps file not found: {}".format(path))

        vals = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                vals.append(float(s.split()[0]))

        if len(vals) == 0:
            return None

        return np.rint(np.asarray(vals, dtype=np.float64) * 1e9).astype(np.int64)

    @staticmethod
    def _p_to_01(p):
        p = np.asarray(p).reshape(-1)
        return (p > 0).astype(np.int8)

    def _load_npz(self, path: str):
        z = np.load(path)
        x = np.asarray(z["x"]).reshape(-1).astype(np.int32)
        y = np.asarray(z["y"]).reshape(-1).astype(np.int32)
        t = np.asarray(z["t"]).reshape(-1).astype(np.int64)   # ns
        p01 = self._p_to_01(z["p"])
        return {"x": x, "y": y, "t": t, "p": p01}

    @staticmethod
    def _event_range_ns(first_file: str, last_file: str):
        z0 = np.load(first_file)
        z1 = np.load(last_file)
        t0 = np.asarray(z0["t"]).reshape(-1)
        t1 = np.asarray(z1["t"]).reshape(-1)
        if t0.size == 0 or t1.size == 0:
            raise RuntimeError("Empty t arrays in event files.")
        return int(t0[0]), int(t1[-1])

    # ---------- streaming ----------

    def _seek_to_time(self, t0_ns: int):
        self.file_idx = 0
        self.cur = self._load_npz(self.files[0])
        self.ptr = int(np.searchsorted(self.cur["t"], t0_ns, side="left"))

        # if t0 is beyond the first file, walk forward
        while self.ptr >= self.cur["t"].size:
            self.file_idx += 1
            if self.file_idx >= len(self.files):
                return
            self.cur = self._load_npz(self.files[self.file_idx])
            self.ptr = int(np.searchsorted(self.cur["t"], t0_ns, side="left"))

    def _pop_events_until(self, t_end_ns: int):
        xs, ys, ts, ps = [], [], [], []

        while True:
            if self.file_idx >= len(self.files):
                break

            if self.ptr >= self.cur["t"].size:
                self.file_idx += 1
                if self.file_idx >= len(self.files):
                    break
                self.cur = self._load_npz(self.files[self.file_idx])
                self.ptr = 0
                continue

            t_arr = self.cur["t"]
            j = int(np.searchsorted(t_arr, t_end_ns, side="left"))
            if j <= self.ptr:
                break

            xs.append(self.cur["x"][self.ptr:j])
            ys.append(self.cur["y"][self.ptr:j])
            ts.append(t_arr[self.ptr:j])
            ps.append(self.cur["p"][self.ptr:j])
            self.ptr = j

        if len(xs) == 0:
            return (
                np.empty((0,), np.int32),
                np.empty((0,), np.int32),
                np.empty((0,), np.int64),
                np.empty((0,), np.int8),
            )

        return (
            np.concatenate(xs),
            np.concatenate(ys),
            np.concatenate(ts).astype(np.int64),
            np.concatenate(ps).astype(np.int8),
        )

    # ---------- math / rendering ----------

    def _decay(self):
        a = math.exp(-float(self.dt_ns) / float(self.tau_ns))
        self.pos_surf *= a
        self.neg_surf *= a

    def _accumulate(self, x, y, t_ns, p01, frame_end_ns: int):
        if x.size == 0:
            return

        inside = (x >= 0) & (x < self.w) & (y >= 0) & (y < self.h)
        if not np.any(inside):
            return

        x = x[inside]
        y = y[inside]
        t_ns = t_ns[inside]
        p01 = p01[inside]

        age = (frame_end_ns - t_ns).astype(np.float64)
        w = np.exp(-age / float(self.tau_ns)).astype(np.float32)

        pos = (p01 == 1)
        if np.any(pos):
            np.maximum.at(self.pos_surf, (y[pos], x[pos]), w[pos])

        neg = ~pos
        if np.any(neg):
            np.maximum.at(self.neg_surf, (y[neg], x[neg]), w[neg])

    def _compose_frame(self):
        pos_u8 = np.clip(self.pos_surf * 255.0, 0, 255).astype(np.uint8)
        neg_u8 = np.clip(self.neg_surf * 255.0, 0, 255).astype(np.uint8)

        mpos = pos_u8.astype(np.float32) / 255.0
        mneg = neg_u8.astype(np.float32) / 255.0

        movl = np.minimum(mpos, mneg)
        mpos = mpos - movl
        mneg = mneg - movl

        img = np.full((self.h, self.w, 3), self.background, dtype=np.float32)
        img += mpos[..., None] * self.pos_bgr[None, None, :]
        img += mneg[..., None] * self.neg_bgr[None, None, :]
        img += movl[..., None] * self.ovl_bgr[None, None, :]

        np.clip(img, 0, 255, out=img)
        return img.astype(np.uint8)


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--events_dir", required=True)
    ap.add_argument("--timestamps", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sensor_w", type=int, default=320)
    ap.add_argument("--sensor_h", type=int, default=256)
    ap.add_argument("--fps", type=float, default=120.0)
    ap.add_argument("--tau_ms", type=float, default=30.0)
    ap.add_argument("--max_frames", type=int, default=None)
    args = ap.parse_args()

    r = EventVideoRenderer(
        events_dir=args.events_dir,
        out_path=args.out,
        sensor_size=(args.sensor_w, args.sensor_h),
        timestamps_path=args.timestamps,
        fps=args.fps,
        tau_ms=args.tau_ms,
    )
    r.render(max_frames=args.max_frames)


if __name__ == "__main__":
    main()
