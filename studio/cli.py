"""drop-studio CLI: python -m studio <command>

  setup       --fonts / --models / --check
  storyboard  build storyboard.json from a daily-drop output.json post
  voice       synthesize per-scene VO wavs (kokoro | piper | openai | none)
  render      storyboard (+ VO manifest) -> final.mp4 + thumb.jpg
  qa          run the QA gates on a rendered video
  video       full chain: storyboard -> voice -> render -> qa
  demo        full chain on the committed sample fixtures (work/demo/)
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .config import DEFAULT_TEMPLATE, WORK_DIR
from .schema import validate
from .theme import load_theme


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="studio", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("setup", help="one-time environment setup")
    sp.add_argument("--fonts", action="store_true", help="convert Figtree woff2 -> ttf")
    sp.add_argument("--models", action="store_true", help="download Kokoro model files (~340 MB)")
    sp.add_argument("--check", action="store_true", help="report environment status")

    sp = sub.add_parser("storyboard", help="build storyboard.json from daily-drop output.json")
    sp.add_argument("--post", required=True, help="path to output.json (or single-post json)")
    sp.add_argument("--index", type=int, default=0, help="review index within the file")
    sp.add_argument("--image", action="append", default=[], help="product image path (repeatable)")
    sp.add_argument("--price", help="price feed json (see storyboard.py docstring)")
    sp.add_argument("--creative", help="creative overrides json (hook, VO lines, ...)")
    sp.add_argument("--out", help="output path (default work/<today>/storyboard.json)")

    sp = sub.add_parser("voice", help="synthesize VO")
    sp.add_argument("--storyboard", required=True)
    sp.add_argument("--backend", choices=["kokoro", "piper", "openai", "none"])
    sp.add_argument("--out-dir", help="default: <storyboard dir>/vo")

    sp = sub.add_parser("render", help="render final.mp4")
    sp.add_argument("--storyboard", required=True)
    sp.add_argument("--vo-dir", help="default: <storyboard dir>/vo (used if manifest.json exists)")
    sp.add_argument("--out", help="default: <storyboard dir>/final.mp4")

    sp = sub.add_parser("qa", help="run QA gates")
    sp.add_argument("--video", required=True)
    sp.add_argument("--storyboard", required=True)
    sp.add_argument("--min-duration", type=float)
    sp.add_argument("--max-duration", type=float)

    for name in ("video", "demo"):
        sp = sub.add_parser(name, help="full pipeline")
        if name == "video":
            sp.add_argument("--post", required=True)
            sp.add_argument("--index", type=int, default=0)
            sp.add_argument("--image", action="append", default=[])
            sp.add_argument("--price")
            sp.add_argument("--creative")
            sp.add_argument("--date", default=date.today().isoformat(), help="work/ subdir name")
        else:
            sp.add_argument("--image", action="append", default=[])
        sp.add_argument("--voice-backend", choices=["kokoro", "piper", "openai", "none"],
                        default="kokoro")

    sp = sub.add_parser("golden", help="generate golden test frames")
    sp.add_argument("--update", action="store_true", help="overwrite existing goldens")

    args = p.parse_args(argv)
    return COMMANDS[args.cmd](args)


def cmd_setup(args) -> int:
    did = False
    if args.fonts:
        from .fonts import convert_fonts

        for path in convert_fonts():
            print(f"font: {path.name}")
        did = True
    if args.models:
        from .voice import download_models

        download_models()
        did = True
    if args.check or not did:
        from .ffmpeg import ffmpeg_exe
        from .fonts import fonts_ready
        from .voice import models_present

        print(f"ffmpeg:        {ffmpeg_exe()}")
        print(f"fonts ready:   {fonts_ready()}")
        print(f"kokoro models: {models_present()}")
        try:
            import kokoro_onnx  # noqa: F401

            print("kokoro-onnx:   importable")
        except Exception as e:  # pragma: no cover
            print(f"kokoro-onnx:   NOT importable ({e})")
    return 0


def cmd_storyboard(args) -> int:
    from .storyboard import build_from_files

    sb = build_from_files(Path(args.post), args.index, args.image,
                          Path(args.price) if args.price else None,
                          Path(args.creative) if args.creative else None)
    out = Path(args.out) if args.out else WORK_DIR / date.today().isoformat() / "storyboard.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sb, indent=2), encoding="utf-8")
    print(f"storyboard: {out}")
    return 0


def _load_storyboard(path: str) -> dict:
    sb = json.loads(Path(path).read_text(encoding="utf-8"))
    errors, warnings = validate(sb)
    for w in warnings:
        print(f"WARN: {w}")
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit(2)
    return sb


def cmd_voice(args) -> int:
    from .voice import synthesize_scenes

    sb = _load_storyboard(args.storyboard)
    out_dir = Path(args.out_dir) if args.out_dir else Path(args.storyboard).parent / "vo"
    manifest = synthesize_scenes(sb, out_dir, backend=args.backend)
    total = sum(s["duration"] for s in manifest["scenes"])
    print(f"vo: backend={manifest['backend']} scenes={len(manifest['scenes'])} speech={total:.1f}s")
    return 0


def _render(storyboard_path: str, vo_dir: str | None, out: str | None) -> tuple[Path, dict, "object"]:
    from .renderer import RenderContext, build_mix, export_thumbnail, render_video
    from .timeline import build_timeline

    sb = _load_storyboard(storyboard_path)
    sb_dir = Path(storyboard_path).parent
    vo_path = Path(vo_dir) if vo_dir else sb_dir / "vo"
    manifest = None
    if (vo_path / "manifest.json").is_file():
        manifest = json.loads((vo_path / "manifest.json").read_text(encoding="utf-8"))
    theme = load_theme(sb.get("template", DEFAULT_TEMPLATE))
    tl = build_timeline(sb, manifest, max_words=theme.caption["max_words"])
    ctx = RenderContext(sb, theme, tl)

    out_mp4 = Path(out) if out else sb_dir / "final.mp4"
    if theme.audio:
        mix_wav = sb_dir / "mix.wav"
        provenance = build_mix(tl, manifest, sb, vo_path if manifest else None, mix_wav)
        print(f"audio: {tl.duration:.1f}s, music={provenance}")
    else:
        mix_wav = None
        print(f"audio: none ({theme.format} format is silent by design)")
    stats = render_video(ctx, mix_wav, out_mp4)
    export_thumbnail(ctx, out_mp4.with_name("thumb.jpg"))
    print(f"video: {out_mp4} ({stats['frames']} frames, {stats['duration']:.1f}s)")
    return out_mp4, sb, theme


def cmd_render(args) -> int:
    _render(args.storyboard, args.vo_dir, args.out)
    return 0


def cmd_qa(args) -> int:
    from .qa import gates, write_report

    sb = _load_storyboard(args.storyboard)
    theme = load_theme(sb.get("template", DEFAULT_TEMPLATE))
    override = None
    if args.min_duration or args.max_duration:
        override = (args.min_duration or theme.qa["min_duration_s"],
                    args.max_duration or theme.qa["max_duration_s"])
    report = gates(Path(args.video), sb, theme, duration_override=override)
    write_report(report, Path(args.video).with_name("qa_report.json"))
    for c in report["checks"]:
        print(f"  [{'PASS' if c['ok'] else 'FAIL'}] {c['name']}: {c['detail']}")
    print("QA PASSED" if report["passed"] else "QA FAILED")
    return 0 if report["passed"] else 1


def cmd_video(args) -> int:
    from .storyboard import build_from_files

    work = WORK_DIR / args.date
    work.mkdir(parents=True, exist_ok=True)
    sb = build_from_files(Path(args.post), args.index, args.image,
                          Path(args.price) if args.price else None,
                          Path(args.creative) if args.creative else None)
    sb_path = work / "storyboard.json"
    sb_path.write_text(json.dumps(sb, indent=2), encoding="utf-8")
    return _voice_render_qa(sb_path, args.voice_backend)


def cmd_demo(args) -> int:
    from .storyboard import build

    fixtures = Path(__file__).parent.parent / "tests" / "fixtures"
    post = json.loads((fixtures / "sample_post.json").read_text(encoding="utf-8"))
    price = json.loads((fixtures / "sample_price.json").read_text(encoding="utf-8"))
    creative = json.loads((fixtures / "sample_creative.json").read_text(encoding="utf-8"))
    work = WORK_DIR / "demo"
    work.mkdir(parents=True, exist_ok=True)
    sb = build(post, images=args.image, price=price, creative=creative)
    sb_path = work / "storyboard.json"
    sb_path.write_text(json.dumps(sb, indent=2), encoding="utf-8")
    return _voice_render_qa(sb_path, args.voice_backend)


def _voice_render_qa(sb_path: Path, voice_backend: str) -> int:
    from .qa import gates, write_report
    from .voice import synthesize_scenes

    sb = _load_storyboard(str(sb_path))
    synthesize_scenes(sb, sb_path.parent / "vo", backend=voice_backend)
    out_mp4, sb, theme = _render(str(sb_path), None, None)
    report = gates(out_mp4, sb, theme)
    write_report(report, out_mp4.with_name("qa_report.json"))
    for c in report["checks"]:
        print(f"  [{'PASS' if c['ok'] else 'FAIL'}] {c['name']}: {c['detail']}")
    print("QA PASSED" if report["passed"] else "QA FAILED")
    return 0 if report["passed"] else 1


def cmd_golden(args) -> int:
    from .golden import generate

    for path in generate(update=args.update):
        print(f"golden: {path.name}")
    return 0


COMMANDS = {
    "setup": cmd_setup,
    "storyboard": cmd_storyboard,
    "voice": cmd_voice,
    "render": cmd_render,
    "qa": cmd_qa,
    "video": cmd_video,
    "demo": cmd_demo,
    "golden": cmd_golden,
}
