"""
StylePianoDiff Web 平台 - MIDI 文件解析工具
使用 pretty_midi 解析 MIDI 文件，转换为前端钢琴卷帘需要的 JSON 格式
"""

import json
from pathlib import Path
from typing import Dict, List, Any


def parse_midi_to_json(file_path: str | Path) -> Dict[str, Any]:
    """
    解析 MIDI 文件，提取音符信息并转换为前端钢琴卷帘 JSON 格式

    Args:
        file_path: MIDI 文件路径

    Returns:
        包含 notes、totalTicks、duration 的字典
        {
            "notes": [
                {
                    "pitch": 60,        # MIDI 音高 (0-127)
                    "start": 0.0,       # 开始时间（秒）
                    "duration": 0.5,    # 持续时间（秒）
                    "velocity": 80,     # 力度 (0-127)
                    "startTick": 0,     # 开始时间（tick）
                    "durationTick": 480 # 持续时间（tick）
                },
                ...
            ],
            "totalTicks": 1920,     # 总 tick 数
            "duration": 10.5        # 总时长（秒）
        }
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"MIDI 文件不存在: {file_path}")

    try:
        import pretty_midi
    except ImportError:
        raise ImportError("请先安装 pretty_midi: pip install pretty_midi")

    pm = pretty_midi.PrettyMIDI(str(file_path))

    notes: List[Dict[str, Any]] = []
    total_ticks = 0

    # 获取默认的 ticks per beat（通常是 480 或 960）
    # pretty_midi 内部使用 480 作为标准 tick 分辨率
    ticks_per_beat = 480

    for instrument in pm.instruments:
        # 跳过鼓点轨道（如果需要保留可以注释掉）
        if instrument.is_drum:
            continue

        for note in instrument.notes:
            # 将秒转换为 tick（基于 BPM）
            start_tick = int(pm.time_to_tick(note.start))
            end_tick = int(pm.time_to_tick(note.end))
            duration_tick = end_tick - start_tick

            notes.append({
                "pitch": note.pitch,
                "start": round(note.start, 4),
                "duration": round(note.end - note.start, 4),
                "velocity": note.velocity,
                "startTick": start_tick,
                "durationTick": duration_tick
            })

            if end_tick > total_ticks:
                total_ticks = end_tick

    # 按开始时间排序
    notes.sort(key=lambda x: x["start"])

    result = {
        "notes": notes,
        "totalTicks": total_ticks,
        "duration": round(pm.get_end_time(), 4)
    }

    return result


def midi_to_json_string(file_path: str | Path) -> str:
    """
    将 MIDI 文件解析为 JSON 字符串

    Args:
        file_path: MIDI 文件路径

    Returns:
        JSON 格式字符串
    """
    result = parse_midi_to_json(file_path)
    return json.dumps(result, ensure_ascii=False, indent=2)


def get_midi_info(file_path: str | Path) -> Dict[str, Any]:
    """
    获取 MIDI 文件的基本信息（不解析全部音符）

    Args:
        file_path: MIDI 文件路径

    Returns:
        包含时长、轨道数、BPM 等信息的字典
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"MIDI 文件不存在: {file_path}")

    try:
        import pretty_midi
    except ImportError:
        raise ImportError("请先安装 pretty_midi: pip install pretty_midi")

    pm = pretty_midi.PrettyMIDI(str(file_path))

    # 估算 BPM
    tempo_changes = pm.get_tempo_changes()
    bpm = 120.0
    if len(tempo_changes[1]) > 0:
        bpm = round(tempo_changes[1][0], 2)

    # 统计音符数量
    note_count = sum(len(inst.notes) for inst in pm.instruments)

    return {
        "duration": round(pm.get_end_time(), 4),
        "bpm": bpm,
        "instrument_count": len(pm.instruments),
        "note_count": note_count,
        "time_signature_changes": [
            {"time": round(ts.time, 4), "numerator": ts.numerator, "denominator": ts.denominator}
            for ts in pm.time_signature_changes
        ] if pm.time_signature_changes else [{"time": 0.0, "numerator": 4, "denominator": 4}]
    }
