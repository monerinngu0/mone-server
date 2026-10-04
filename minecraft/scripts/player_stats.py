#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path
from typing import Any


TICKS_PER_SECOND = 20
CM_PER_KM = 100_000


def normalize_uuid(value: str) -> str:
    """UUIDをハイフンなし・小文字に統一する。"""
    return value.replace("-", "").lower()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"JSONのルートがオブジェクトではありません: {path}")

    return data


def load_usercache(path: Path) -> dict[str, str]:
    """
    usercache.jsonから
    UUID（ハイフンなし） -> プレイヤー名
    の辞書を作る。
    """
    if not path.exists():
        print(
            f"警告: {path} が見つかりません。名前の代わりにUUIDを表示します。",
            file=sys.stderr,
        )
        return {}

    try:
        with path.open("r", encoding="utf-8") as file:
            entries = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        print(f"警告: usercache.jsonを読めません: {error}", file=sys.stderr)
        return {}

    result: dict[str, str] = {}

    if not isinstance(entries, list):
        return result

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        uuid = entry.get("uuid")
        name = entry.get("name")

        if isinstance(uuid, str) and isinstance(name, str):
            result[normalize_uuid(uuid)] = name

    return result


def custom_stat(data: dict[str, Any], key: str) -> int:
    value = (
        data.get("stats", {})
        .get("minecraft:custom", {})
        .get(f"minecraft:{key}", 0)
    )

    return value if isinstance(value, int) else 0


def category(data: dict[str, Any], name: str) -> dict[str, int]:
    values = data.get("stats", {}).get(f"minecraft:{name}", {})

    if not isinstance(values, dict):
        return {}

    return {
        key: value
        for key, value in values.items()
        if isinstance(key, str) and isinstance(value, int)
    }


def format_duration(ticks: int) -> str:
    total_seconds = ticks // TICKS_PER_SECOND

    days, remainder = divmod(total_seconds, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes, seconds = divmod(remainder, 60)

    if days:
        return f"{days}日 {hours:02}:{minutes:02}:{seconds:02}"

    return f"{hours:02}:{minutes:02}:{seconds:02}"


def cm_to_km(cm: int) -> float:
    return cm / CM_PER_KM


def strip_namespace(value: str) -> str:
    return value.removeprefix("minecraft:")


def make_player_record(
    path: Path,
    uuid_to_name: dict[str, str],
) -> dict[str, Any]:
    data = load_json(path)

    uuid = path.stem
    normalized_uuid = normalize_uuid(uuid)
    name = uuid_to_name.get(normalized_uuid, uuid)

    return {
        "name": name,
        "uuid": uuid,
        "path": path,
        "data": data,
        "play_time": custom_stat(data, "play_time"),
        "deaths": custom_stat(data, "deaths"),
        "mob_kills": custom_stat(data, "mob_kills"),
        "player_kills": custom_stat(data, "player_kills"),
        "leave_game": custom_stat(data, "leave_game"),
        "jump": custom_stat(data, "jump"),
        "walk_cm": custom_stat(data, "walk_one_cm"),
        "sprint_cm": custom_stat(data, "sprint_one_cm"),
        "fly_cm": custom_stat(data, "fly_one_cm"),
        "swim_cm": custom_stat(data, "swim_one_cm"),
        "boat_cm": custom_stat(data, "boat_one_cm"),
    }


def load_players(
    stats_dir: Path,
    uuid_to_name: dict[str, str],
) -> list[dict[str, Any]]:
    if not stats_dir.is_dir():
        raise FileNotFoundError(
            f"統計ディレクトリが見つかりません: {stats_dir}"
        )

    players: list[dict[str, Any]] = []

    for path in sorted(stats_dir.glob("*.json")):
        try:
            players.append(make_player_record(path, uuid_to_name))
        except (OSError, json.JSONDecodeError, ValueError) as error:
            print(f"警告: {path.name} を読み飛ばしました: {error}", file=sys.stderr)

    return players

##################################
def format_time_per_death(player: dict[str, Any]) -> str:
    deaths = player["deaths"]

    if deaths == 0:
        return "死亡なし"

    return format_duration(player["play_time"] // deaths)


COLUMN_DEFINITIONS = {
    "name": {
        "title": "名前",
        "width": 20,
        "align": "<",
        "value": lambda player: player["name"],
    },
    "play_time": {
        "title": "プレイ時間",
        "width": 15,
        "align": ">",
        "value": lambda player: format_duration(player["play_time"]),
    },
    "deaths": {
        "title": "死亡",
        "width": 6,
        "align": ">",
        "value": lambda player: str(player["deaths"]),
    },
    "time_per_death": {
        "title": "時間/死亡",
        "width": 15,
        "align": ">",
        "value": format_time_per_death,
    },
    "mob_kills": {
        "title": "Mob討伐",
        "width": 8,
        "align": ">",
        "value": lambda player: str(player["mob_kills"]),
    },
    "player_kills": {
        "title": "対人キル",
        "width": 8,
        "align": ">",
        "value": lambda player: str(player["player_kills"]),
    },
    "walk_km": {
        "title": "徒歩km",
        "width": 10,
        "align": ">",
        "value": lambda player: f"{cm_to_km(player['walk_cm']):.2f}",
    },
    "sprint_km": {
        "title": "走行km",
        "width": 10,
        "align": ">",
        "value": lambda player: f"{cm_to_km(player['sprint_cm']):.2f}",
    },
    "fly_km": {
        "title": "飛行km",
        "width": 10,
        "align": ">",
        "value": lambda player: f"{cm_to_km(player['fly_cm']):.2f}",
    },
}
###########################################

def print_player_list(
    players: list[dict[str, Any]],
    column_names: list[str],
) -> None:
    players.sort(key=lambda player: player["play_time"], reverse=True)

    columns = [COLUMN_DEFINITIONS[name] for name in column_names]

    header = " ".join(
        f"{column['title']:{column['align']}{column['width']}}"
        for column in columns
    )

    print(header)
    print("-" * len(header))

    for player in players:
        row = " ".join(
            f"{str(column['value'](player)):{column['align']}{column['width']}}"
            for column in columns
        )
        print(row)

def print_top_values(
    title: str,
    values: dict[str, int],
    limit: int = 10,
) -> None:
    print(f"\n{title}")

    sorted_values = sorted(
        values.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    if not sorted_values:
        print("  記録なし")
        return

    for key, value in sorted_values[:limit]:
        print(f"  {strip_namespace(key):<30} {value:>10}")


def print_player_detail(player: dict[str, Any]) -> None:
    data = player["data"]

    print(f"名前:             {player['name']}")
    print(f"UUID:             {player['uuid']}")
    print(f"プレイ時間:       {format_duration(player['play_time'])}")
    print(f"プレイ時間tick:   {player['play_time']}")
    print(f"退出回数:         {player['leave_game']}")
    print(f"死亡回数:         {player['deaths']}")
    print(f"Mob討伐数:        {player['mob_kills']}")
    print(f"プレイヤー討伐数: {player['player_kills']}")
    print(f"ジャンプ回数:     {player['jump']}")
    print(f"歩行距離:         {cm_to_km(player['walk_cm']):.2f} km")
    print(f"走行距離:         {cm_to_km(player['sprint_cm']):.2f} km")
    print(f"飛行距離:         {cm_to_km(player['fly_cm']):.2f} km")
    print(f"泳いだ距離:       {cm_to_km(player['swim_cm']):.2f} km")
    print(f"ボート移動距離:   {cm_to_km(player['boat_cm']):.2f} km")

    print_top_values(
        "採掘したブロック 上位10件",
        category(data, "mined"),
    )
    print_top_values(
        "倒したMob 上位10件",
        category(data, "killed"),
    )
    print_top_values(
        "使用したアイテム 上位10件",
        category(data, "used"),
    )
    print_top_values(
        "クラフトしたアイテム 上位10件",
        category(data, "crafted"),
    )


def find_player(
    players: list[dict[str, Any]],
    query: str,
) -> dict[str, Any] | None:
    normalized_query = normalize_uuid(query)
    lower_query = query.lower()

    exact_matches = [
        player
        for player in players
        if player["name"].lower() == lower_query
        or normalize_uuid(player["uuid"]) == normalized_query
    ]

    if exact_matches:
        return exact_matches[0]

    partial_matches = [
        player
        for player in players
        if lower_query in player["name"].lower()
        or normalized_query in normalize_uuid(player["uuid"])
    ]

    if len(partial_matches) == 1:
        return partial_matches[0]

    if len(partial_matches) > 1:
        print("複数のプレイヤーが一致しました:", file=sys.stderr)
        for player in partial_matches:
            print(f"  {player['name']} ({player['uuid']})", file=sys.stderr)

    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Minecraftのプレイヤー統計を表示します。"
    )
    parser.add_argument(
        "player",
        nargs="?",
        help="詳しく表示するプレイヤー名またはUUID",
    )
    parser.add_argument(
        "--stats-dir",
        type=Path,
        default=Path("/data/world/players/stats"),
        help="統計JSONが入ったディレクトリ",
    )
    parser.add_argument(
        "--usercache",
        type=Path,
        default=Path("/data/usercache.json"),
        help="usercache.jsonのパス",
    )
    parser.add_argument(
        "--columns",
        default=(
            "name,play_time,deaths,time_per_death,"
            "mob_kills,player_kills,walk_km,fly_km"
        ),
        help=(
            "一覧に表示する列をカンマ区切りで指定します。"
            "利用可能な列: "
            + ", ".join(COLUMN_DEFINITIONS)
        ),
    )

    args = parser.parse_args()

    column_names = [
        name.strip()
        for name in args.columns.split(",")
        if name.strip()
    ]

    if not column_names:
        print(
            "エラー: 表示する列を1つ以上指定してください。",
            file=sys.stderr,
        )
        return 1

    unknown_columns = [
        name
        for name in column_names
        if name not in COLUMN_DEFINITIONS
    ]

    if unknown_columns:
        print(
            "エラー: 不明な列: " + ", ".join(unknown_columns),
           file=sys.stderr,
        )
        print(
            "利用可能な列: " + ", ".join(COLUMN_DEFINITIONS),
            file=sys.stderr,
        )
        return 1

    try:
        uuid_to_name = load_usercache(args.usercache)
        players = load_players(args.stats_dir, uuid_to_name)
    except (OSError, ValueError) as error:
        print(f"エラー: {error}", file=sys.stderr)
        return 1

    if not players:
        print("プレイヤー統計が見つかりません。", file=sys.stderr)
        return 1

    if args.player is None:
        print_player_list(players, column_names)
        return 0

    player = find_player(players, args.player)

    if player is None:
        print(f"プレイヤーが見つかりません: {args.player}", file=sys.stderr)
        return 1

    print_player_detail(player)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
