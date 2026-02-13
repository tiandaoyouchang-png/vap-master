#!/usr/bin/env python3

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast


DEFAULT_JAVA = "/Users/cqca202110203/.opencode/tools/java/temurin17/Contents/Home/bin/java"
DEFAULT_VAPTOOL_HOME = "/Users/cqca202110203/.opencode/tools/vaptool/tool2.0.6"


def die(msg: str, code: int = 2) -> None:
    print(msg, file=sys.stderr, flush=True)
    raise SystemExit(code)


def run_cmd(cmd: list[str], desc: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        msg = (
            f"{desc} failed with exit {result.returncode}\n"
            + f"cmd: {' '.join(cmd)}\n"
            + f"stdout:\n{result.stdout}\n"
            + f"stderr:\n{result.stderr}"
        )
        raise RuntimeError(msg)
    return result


def ensure_executable(path: Path) -> None:
    try:
        st = path.stat()
        mode = st.st_mode
        path.chmod(mode | 0o100)
    except Exception:
        return


def get_suffix(filename: str) -> int:
    m = re.search(r"(\d+)\.png$", filename, re.IGNORECASE)
    return int(m.group(1)) if m else -1


def list_png_frames(folder: Path) -> list[str]:
    files = [p.name for p in folder.iterdir() if p.is_file() and p.name.lower().endswith(".png")]
    files = [f for f in files if get_suffix(f) != -1]
    files.sort(key=get_suffix)
    return files


def read_png_size(file_path: Path) -> tuple[int, int]:
    with file_path.open("rb") as f:
        sig = f.read(8)
        if sig != b"\x89PNG\r\n\x1a\n":
            raise RuntimeError(f"Not a PNG file: {file_path}")
        ihdr_len = int.from_bytes(f.read(4), "big", signed=False)
        chunk_type = f.read(4)
        if chunk_type != b"IHDR" or ihdr_len < 8:
            raise RuntimeError(f"Invalid PNG header: {file_path}")
        width = int.from_bytes(f.read(4), "big", signed=False)
        height = int.from_bytes(f.read(4), "big", signed=False)
    return width, height


def normalize_frames(src_folder: Path, png_files: list[str], normalized_dir: Path, ffmpeg: str) -> None:
    normalized_dir.mkdir(parents=True, exist_ok=True)
    for idx, frame_name in enumerate(png_files):
        src = src_folder / frame_name
        dst = normalized_dir / f"{idx:03d}.png"
        width, height = read_png_size(src)
        if width != 1008:
            raise RuntimeError(f"Frame width must be 1008, got {width} for {src}")
        if height == 1334:
            try:
                os.symlink(src, dst)
            except OSError:
                _ = shutil.copy2(src, dst)
        elif height == 1344:
            _ = run_cmd(
                [
                    ffmpeg,
                    "-y",
                    "-i",
                    str(src),
                    "-vf",
                    "crop=1008:1334:0:0",
                    "-frames:v",
                    "1",
                    str(dst),
                ],
                f"crop frame {src.name}",
            )
        else:
            raise RuntimeError(f"Frame height must be 1334 or 1344, got {height} for {src}")


def list_top_level_atoms(mp4_path: Path) -> list[str]:
    atoms: list[str] = []
    data = mp4_path.read_bytes()
    size_total = len(data)
    pos = 0
    while pos + 8 <= size_total:
        atom_size = int.from_bytes(data[pos : pos + 4], "big", signed=False)
        atom_type = data[pos + 4 : pos + 8].decode("latin1")
        header_size = 8
        if atom_size == 1:
            if pos + 16 > size_total:
                break
            atom_size = int.from_bytes(data[pos + 8 : pos + 16], "big", signed=False)
            header_size = 16
        elif atom_size == 0:
            atom_size = size_total - pos
        if atom_size < header_size:
            break
        atoms.append(atom_type)
        pos += atom_size
    return atoms


def has_top_level_vapc(mp4_path: Path) -> bool:
    return "vapc" in list_top_level_atoms(mp4_path)


def is_valid_mp4(mp4_path: Path, min_size_bytes: int = 1024) -> bool:
    if not mp4_path.exists() or mp4_path.stat().st_size < min_size_bytes:
        return False
    atoms = list_top_level_atoms(mp4_path)
    if not atoms:
        return False
    if atoms[0] != "ftyp" and "moov" not in atoms:
        return False
    if "moov" not in atoms or "mdat" not in atoms:
        return False
    return True


def is_playable_mp4(mp4_path: Path, ffprobe: str) -> bool:
    if not is_valid_mp4(mp4_path):
        return False
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1",
            str(mp4_path),
        ],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _require_dict(obj: object, ctx: str) -> dict[str, object]:
    if not isinstance(obj, dict):
        raise RuntimeError(f"Expected dict for {ctx}")
    return cast(dict[str, object], obj)


def _require_list(obj: object, ctx: str) -> list[object]:
    if not isinstance(obj, list):
        raise RuntimeError(f"Expected list for {ctx}")
    return cast(list[object], obj)


def _require_int(obj: object, ctx: str) -> int:
    if isinstance(obj, bool) or not isinstance(obj, int):
        raise RuntimeError(f"Expected int for {ctx}")
    return int(obj)


def _require_float(obj: object, ctx: str) -> float:
    if isinstance(obj, bool):
        raise RuntimeError(f"Expected number for {ctx}")
    if isinstance(obj, (int, float)):
        return float(obj)
    raise RuntimeError(f"Expected number for {ctx}")


@dataclass(frozen=True)
class VapcParsed:
    vapc_json: dict[str, object]
    frame_count: int
    fps: float
    a_frame: tuple[int, int, int, int]
    rgb_frame: tuple[int, int, int, int]


def parse_vapc_json(vapc_path: Path) -> VapcParsed:
    with vapc_path.open("r", encoding="utf-8") as f:
        vapc_obj = cast(object, json.load(f))
    vapc_json = _require_dict(vapc_obj, "vapc.json")
    info = _require_dict(vapc_json.get("info"), "vapc.json.info")

    frame_count = _require_int(info.get("f"), "vapc.json.info.f")
    fps = _require_float(info.get("fps"), "vapc.json.info.fps")

    a_frame_raw = _require_list(info.get("aFrame"), "vapc.json.info.aFrame")
    rgb_frame_raw = _require_list(info.get("rgbFrame"), "vapc.json.info.rgbFrame")
    if len(a_frame_raw) != 4 or len(rgb_frame_raw) != 4:
        raise RuntimeError(f"Invalid aFrame/rgbFrame in {vapc_path}")

    a_frame = (
        _require_int(a_frame_raw[0], "vapc.json.info.aFrame[0]"),
        _require_int(a_frame_raw[1], "vapc.json.info.aFrame[1]"),
        _require_int(a_frame_raw[2], "vapc.json.info.aFrame[2]"),
        _require_int(a_frame_raw[3], "vapc.json.info.aFrame[3]"),
    )
    rgb_frame = (
        _require_int(rgb_frame_raw[0], "vapc.json.info.rgbFrame[0]"),
        _require_int(rgb_frame_raw[1], "vapc.json.info.rgbFrame[1]"),
        _require_int(rgb_frame_raw[2], "vapc.json.info.rgbFrame[2]"),
        _require_int(rgb_frame_raw[3], "vapc.json.info.rgbFrame[3]"),
    )

    return VapcParsed(vapc_json=vapc_json, frame_count=frame_count, fps=fps, a_frame=a_frame, rgb_frame=rgb_frame)


def create_vapc_atom_file(vapc_json: dict[str, object], out_path: Path) -> None:
    payload = json.dumps(vapc_json, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    size = len(payload) + 8
    _ = out_path.write_bytes(int(size).to_bytes(4, "big", signed=False) + b"vapc" + payload)


def swap_video_regions(
    orig_mp4: Path,
    vapc: VapcParsed,
    swapped_mp4: Path,
    ffmpeg: str,
    out_bitrate_k: int,
) -> None:
    frame_count = int(vapc.frame_count)
    fps = float(vapc.fps)
    if frame_count <= 0 or fps <= 0:
        raise RuntimeError(f"Invalid frame metadata in vapc info: f={frame_count}, fps={fps}")
    dur = frame_count / fps

    ax, ay, aw, ah = vapc.a_frame
    rx, ry, rw, rh = vapc.rgb_frame

    out_w = 2016
    out_h = 1334
    alpha_dst_x, alpha_dst_y = 0, 0
    rgb_dst_x, rgb_dst_y = 1008, 0

    filter_str = (
        f"color=s={out_w}x{out_h}:c=black:d={dur:.6f}[base];"
        f"[0:v]crop={aw}:{ah}:{ax}:{ay}[alpha];"
        f"[0:v]crop={rw}:{rh}:{rx}:{ry}[rgb];"
        f"[base][alpha]overlay={alpha_dst_x}:{alpha_dst_y}[tmp];"
        f"[tmp][rgb]overlay={rgb_dst_x}:{rgb_dst_y}:shortest=1"
    )
    _ = run_cmd(
        [
            ffmpeg,
            "-y",
            "-i",
            str(orig_mp4),
            "-filter_complex",
            filter_str,
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(int(round(fps))),
            "-b:v",
            f"{out_bitrate_k}k",
            "-maxrate",
            f"{out_bitrate_k}k",
            "-bufsize",
            f"{out_bitrate_k * 2}k",
            str(swapped_mp4),
        ],
        "swap video regions",
    )


def write_final_with_vapc(
    swapped_mp4: Path,
    vapc: VapcParsed,
    mp4edit: Path,
    ffprobe: str,
    work_dir: Path,
    final_output: Path,
) -> None:
    updated_json: dict[str, object] = dict(vapc.vapc_json)
    info_obj = updated_json.get("info")
    updated_info: dict[str, object] = dict(_require_dict(info_obj, "vapc.json.info"))

    updated_info["videoW"] = 2016
    updated_info["videoH"] = 1334
    updated_info["aFrame"] = [0, 0, 1008, 1334]
    updated_info["rgbFrame"] = [1008, 0, 1008, 1334]
    updated_json["info"] = updated_info

    vapc_atom_path = work_dir / "vapc.atom"
    create_vapc_atom_file(updated_json, vapc_atom_path)

    no_vapc_mp4 = work_dir / "no_vapc.mp4"
    remove_result = subprocess.run(
        [str(mp4edit), "--remove", "vapc", str(swapped_mp4), str(no_vapc_mp4)],
        capture_output=True,
        text=True,
    )
    if remove_result.returncode != 0 or not is_valid_mp4(no_vapc_mp4):
        _ = shutil.copy2(swapped_mp4, no_vapc_mp4)

    final_tmp = work_dir / "final.mp4"
    _ = run_cmd(
        [str(mp4edit), "--insert", f":{vapc_atom_path}", str(no_vapc_mp4), str(final_tmp)],
        "insert updated vapc atom",
    )
    if not is_valid_mp4(final_tmp):
        raise RuntimeError(f"Final MP4 is invalid after vapc insert: {final_tmp}")
    if not has_top_level_vapc(final_tmp):
        raise RuntimeError(f"Final MP4 missing top-level vapc after insert: {final_tmp}")
    if "moov" not in list_top_level_atoms(final_tmp):
        raise RuntimeError(f"Final MP4 missing moov atom after insert: {final_tmp}")
    if not is_playable_mp4(final_tmp, ffprobe):
        raise RuntimeError(f"Final MP4 is not playable after vapc insert: {final_tmp}")

    final_output.parent.mkdir(parents=True, exist_ok=True)
    _ = shutil.move(final_tmp, final_output)


def compile_vapbatch_if_needed(skill_dir: Path, javac: Path, animtool_jar: Path) -> None:
    java_src = skill_dir / "VapBatch.java"
    java_cls = skill_dir / "VapBatch.class"
    if not java_src.exists():
        raise RuntimeError(f"Missing VapBatch.java in {skill_dir}")

    if java_cls.exists() and java_cls.stat().st_mtime >= java_src.stat().st_mtime:
        return

    if not javac.exists():
        raise RuntimeError(f"javac not found: {javac}")
    if not animtool_jar.exists():
        raise RuntimeError(f"animtool.jar not found: {animtool_jar}")

    _ = run_cmd(
        [
            str(javac),
            "-cp",
            str(animtool_jar),
            str(java_src),
        ],
        "compile VapBatch.java",
    )
    if not java_cls.exists():
        raise RuntimeError(f"Compilation finished but class missing: {java_cls}")


def run_vap_batch(
    java: Path,
    vaptool_home: Path,
    animtool_jar: Path,
    skill_dir: Path,
    frames_dir: Path,
    vap_out_dir: Path,
    fps: int,
    bitrate: int,
    scale: float,
) -> None:
    vap_out_dir.mkdir(parents=True, exist_ok=True)

    classpath = f"{animtool_jar}:{skill_dir}"
    cmd = [
        str(java),
        "-cp",
        classpath,
        "VapBatch",
        str(vaptool_home),
        str(frames_dir),
        str(vap_out_dir),
        str(fps),
        str(bitrate),
        str(scale),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return

    fallback_dir = frames_dir / "output"
    fallback_video = fallback_dir / "video.mp4"
    fallback_vapc = fallback_dir / "vapc.json"
    fallback_md5 = fallback_dir / "md5.txt"
    if fallback_video.exists() and fallback_vapc.exists():
        _ = shutil.copy2(fallback_video, vap_out_dir / "video.mp4")
        _ = shutil.copy2(fallback_vapc, vap_out_dir / "vapc.json")
        if fallback_md5.exists():
            _ = shutil.copy2(fallback_md5, vap_out_dir / "md5.txt")
        return

    msg = (
        f"run VapBatch failed with exit {result.returncode}\n"
        + f"cmd: {' '.join(cmd)}\n"
        + f"stdout:\n{result.stdout}\n"
        + f"stderr:\n{result.stderr}"
    )
    raise RuntimeError(msg)


@dataclass(frozen=True)
class Args:
    input: str
    output: str
    fps: int
    mode: Literal["standard", "mask-left"]
    java: str
    vaptool_home: str
    bitrate: int
    swap_bitrate: int
    keep_work: bool


def parse_args() -> Args:
    parser = argparse.ArgumentParser(description="Generate VAP MP4 from PNG sequence")
    _ = parser.add_argument("--input", required=True, help="Source PNG sequence directory")
    _ = parser.add_argument("--output", required=True, help="Target MP4 file path")
    _ = parser.add_argument("--fps", type=int, default=25, help="Frames per second (default: 25)")
    _ = parser.add_argument(
        "--mode",
        choices=["standard", "mask-left"],
        default="standard",
        help="VAP layout mode",
    )
    _ = parser.add_argument("--java", default=DEFAULT_JAVA, help="Path to java binary")
    _ = parser.add_argument("--vaptool-home", default=DEFAULT_VAPTOOL_HOME, help="Path to VapTool home")
    _ = parser.add_argument("--bitrate", type=int, default=2000, help="VapTool encoding bitrate (kbps)")
    _ = parser.add_argument(
        "--swap-bitrate",
        type=int,
        default=3000,
        help="mask-left swap re-encode bitrate (kbps)",
    )
    _ = parser.add_argument("--keep-work", action="store_true", help="Keep temporary working directory")

    ns = parser.parse_args()
    return Args(
        input=cast(str, ns.input),
        output=cast(str, ns.output),
        fps=int(cast(int, ns.fps)),
        mode=cast(Literal["standard", "mask-left"], ns.mode),
        java=cast(str, ns.java),
        vaptool_home=cast(str, ns.vaptool_home),
        bitrate=int(cast(int, ns.bitrate)),
        swap_bitrate=int(cast(int, ns.swap_bitrate)),
        keep_work=bool(cast(bool, ns.keep_work)),
    )


def main() -> None:
    args = parse_args()

    src_dir = Path(args.input).expanduser().resolve()
    out_mp4 = Path(args.output).expanduser().resolve()
    if not src_dir.is_dir():
        die(f"--input is not a directory: {src_dir}")
    if args.fps <= 0:
        die(f"--fps must be > 0, got {args.fps}")

    skill_dir = Path(__file__).resolve().parent
    java = Path(args.java)
    if not java.exists():
        die(f"java not found: {java}")
    javac = java.with_name("javac")

    vaptool_home = Path(args.vaptool_home)
    animtool_jar = vaptool_home / "animtool.jar"
    mp4edit = vaptool_home / "mac" / "mp4edit"
    ensure_executable(mp4edit)
    ensure_executable(vaptool_home / "mac" / "ffmpeg")

    ffmpeg = shutil.which("ffmpeg") or ""
    if not ffmpeg:
        die("ffmpeg not found in PATH")
    ffprobe = shutil.which("ffprobe") or ""
    if not ffprobe:
        die("ffprobe not found in PATH")

    png_files = list_png_frames(src_dir)
    if not png_files:
        die(f"No valid PNG frames found in {src_dir} (need files like *_00001.png)")

    tmp_root = Path(tempfile.mkdtemp(prefix="vap_master_"))
    work_dir = tmp_root
    success = False
    try:
        frames_dir = work_dir / "frames"
        vap_out_dir = work_dir / "vap_out"
        swapped_mp4 = work_dir / "swapped.mp4"

        normalize_frames(src_dir, png_files, frames_dir, ffmpeg)

        compile_vapbatch_if_needed(skill_dir, javac, animtool_jar)
        run_vap_batch(
            java=java,
            vaptool_home=vaptool_home,
            animtool_jar=animtool_jar,
            skill_dir=skill_dir,
            frames_dir=frames_dir,
            vap_out_dir=vap_out_dir,
            fps=args.fps,
            bitrate=args.bitrate,
            scale=(0.5 if args.mode == "standard" else 1.0),
        )

        orig_mp4 = vap_out_dir / "video.mp4"
        vapc_path = vap_out_dir / "vapc.json"
        if not orig_mp4.exists():
            raise RuntimeError(f"VapTool output missing video.mp4: {orig_mp4}")

        if args.mode == "standard":
            if not is_playable_mp4(orig_mp4, ffprobe):
                raise RuntimeError(f"Generated MP4 is not playable: {orig_mp4}")
            out_mp4.parent.mkdir(parents=True, exist_ok=True)
            _ = shutil.copy2(orig_mp4, out_mp4)
            success = True
            return

        if not vapc_path.exists():
            raise RuntimeError(f"VapTool output missing vapc.json: {vapc_path}")
        vapc = parse_vapc_json(vapc_path)
        swap_video_regions(orig_mp4, vapc, swapped_mp4, ffmpeg, args.swap_bitrate)
        if not is_playable_mp4(swapped_mp4, ffprobe):
            raise RuntimeError(f"Swapped MP4 is not playable: {swapped_mp4}")
        write_final_with_vapc(swapped_mp4, vapc, mp4edit, ffprobe, work_dir, out_mp4)
        if not has_top_level_vapc(out_mp4):
            raise RuntimeError(f"Final output missing vapc atom: {out_mp4}")
        success = True
    finally:
        if not args.keep_work and work_dir.exists() and success:
            shutil.rmtree(work_dir)
        elif not success:
            print(f"Work dir preserved for debugging: {work_dir}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
