"""
joinMOTD
Base Repo: https://github.com/TISUnion/joinMOTD
Author: Fallen-Breath
Edited by: Eric_Yang, a3510377
"""

import collections
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Union

from mcdreforged.api.all import (
    CommandContext,
    Info,
    Integer,
    PlayerCommandSource,
    PluginServerInterface,
    RAction,
    RColor,
    RText,
    RTextBase,
    RTextList,
    Serializable,
    ServerInterface,
    SimpleCommandBuilder,
    Text,
    new_thread,
)


class ServerInfo(Serializable):
    name: str
    description: Optional[str] = None
    category: str = ""

    @classmethod
    def from_object(cls, obj) -> "ServerInfo":
        if isinstance(obj, cls):
            return obj
        return ServerInfo(name=str(obj))


class APIPlayerListQueryResult(NamedTuple):
    amount: int
    limit: int
    players: List[str]


class Config(Serializable):
    serverName: str = "Survival Server"
    mainServerName: str = "My Server"
    serverList: List[Union[str, ServerInfo]] = [
        "survival",
        "lobby",
        ServerInfo(name="creative1", description="CMP Server#1", category="CMP"),
        ServerInfo(name="creative2", description="CMP Server#2", category="CMP"),
    ]
    start_day: Optional[str] = None
    daycount_plugin_ids: List[str] = ["mcd_daycount", "day_count_reforged", "daycount_nbt"]
    # 2 天內上線很活躍
    active: int = 2
    # 7 天內上線很普通
    normal: int = 7
    # 14 天內上線很不活躍
    inactive: int = 14

    ignore_player_regex: List[str] = ["^bot_.*$", "^Bot_.*$", "^\\[bot\\].*$"]


config: Config
manager: Optional["PluginManager"] = None

LAST_UP_PREFIX = "!!up"
JOIN_MOTD_PREFIX = "!!joinMOTD"
TIME_FORMAT = "%Y-%m-%d_%H:%M:%S"
LAST_UP_LIST_PAGE_SIZE = 5
CONFIG_FILE_PATH = Path("config/joinMOTD.json")
LAST_PIN_TIME_PATH = Path("config/last_join_time.json")


class PluginManager:
    def __init__(self, server: PluginServerInterface, config: Config):
        self.server = server
        self.config = config
        self.data: Dict[str, datetime] = self.get_all_last_join_time()

    def register(self):
        self.server.register_help_message(JOIN_MOTD_PREFIX, "顯示歡迎消息")
        self.server.register_help_message(LAST_UP_PREFIX, "顯示上次加入伺服器時間")

        builder = SimpleCommandBuilder()
        builder.command(JOIN_MOTD_PREFIX, lambda src: self.display_motd(src.reply))
        builder.command(
            LAST_UP_PREFIX,
            lambda src, ctx: (
                self.display_last_join(src.reply, src.player)
                if isinstance(src, PlayerCommandSource)
                else self.display_last_join_list(src.reply, ctx)  # type: ignore
            ),
        )
        builder.arg("player_name", Text)
        builder.command(
            f"{LAST_UP_PREFIX} get <player_name>",
            lambda src, ctx: self.display_last_join(src.reply, ctx["player_name"]),
        )
        builder.command(
            f"{LAST_UP_PREFIX} list",
            lambda src, ctx: self.display_last_join_list(src.reply, ctx),  # type: ignore
        )
        builder.arg("index", Integer)
        builder.command(
            f"{LAST_UP_PREFIX} list <index>",
            lambda src, ctx: self.display_last_join_list(src.reply, ctx),  # type: ignore
        )
        builder.command(f"{LAST_UP_PREFIX} help", lambda src: self.display_last_join_help(src.reply))
        builder.register(self.server)

    def display_motd(
        self,
        reply: Callable[[Union[str, RTextBase]], Any],
        player: Optional[str] = None,
    ) -> None:
        reply(f"§7§rWelcome back to §e{self.config.serverName}§7§r")
        reply(f"今天是 §e{self.config.mainServerName}§ r開服的第 §e{self.get_day()}§r 天")
        if player is not None:
            self.display_last_join(reply, player, write=True)
        reply("§7-------§r Server List §7-------§r")

        server_dict: Dict[str, List[ServerInfo]] = collections.defaultdict(list)
        for entry in self.config.serverList:
            info = ServerInfo.from_object(entry)
            server_dict[info.category].append(info)
        for category, server_list in server_dict.items():
            header = RText(f"{category}: " if len(category) > 0 else "")
            messages = []
            for info in server_list:
                command = f"/server {info.name}"
                hover_text = command
                if info.description is not None:
                    hover_text = info.description + "\n" + hover_text
                messages.append(RText(f"[{info.name}]").h(hover_text).c(RAction.run_command, command))
            reply(header + RTextBase.join(" ", messages))

    def get_day(self) -> str:
        try:
            if start_day := self.config.start_day:
                startday = datetime.strptime(start_day, "%Y-%m-%d")
                now = datetime.now()
                output = now - startday
                return str(output.days)
        except Exception:
            pass
        for pid in self.config.daycount_plugin_ids:
            api = self.server.get_plugin_instance(pid)
            if hasattr(api, "getday") and callable(api.getday):  # type: ignore
                return api.getday()  # type: ignore
        try:
            import daycount  # type: ignore

            return daycount.getday()
        except Exception:
            return "?"

    def display_last_join(
        self,
        reply: Callable[[Union[str, RTextBase]], Any],
        player: str,
        *,
        write: bool = False,
    ) -> None:
        days = self.get_last_join_time_days(player, write=write)
        reply(f"距離上次加入伺服器已過 §e{days}§r 天")

    def display_last_join_help(self, reply: Callable[[Union[str, RTextBase]], Any]) -> None:
        reply("顯示上次加入伺服器時間:")
        reply(f"- {LAST_UP_PREFIX} get <player_name>")
        reply(f"- {LAST_UP_PREFIX} list")
        reply(f"- {LAST_UP_PREFIX} list <index>")
        reply(f"- {LAST_UP_PREFIX} help")

    @new_thread("join_motd")
    def display_last_join_list(
        self,
        reply: Callable[[Union[str, RTextBase]], Any],
        ctx: CommandContext,
    ) -> None:
        index = ctx.get("index", 1) - 1
        data = self.format_last_join_player_list()
        page_size = math.ceil(len(data) / LAST_UP_LIST_PAGE_SIZE)
        if index < 0 or index >= page_size:
            reply(f"無效的頁碼應為 1 ~ {page_size}")
            return

        start = index * LAST_UP_LIST_PAGE_SIZE
        end = start + LAST_UP_LIST_PAGE_SIZE
        page_data = data[start:end]

        reply("上次加入伺服器時間:")
        reply("-------- 玩家列表 --------")
        # reply("  <<< 第00頁/共00頁 >>>   ")

        for line in page_data:
            reply(line)

        reply(
            RTextList(
                "     ",
                (
                    RText("<<<").c(RAction.run_command, f"{LAST_UP_PREFIX} list {index}").h("上一頁")
                    if index > 0
                    else "   "
                ),
                f" 第{index + 1:02d}頁/共{page_size:02d}頁 ",
                (
                    RText(">>>").c(RAction.run_command, f"{LAST_UP_PREFIX} list {index + 2}").h("下一頁")
                    if index < page_size - 1
                    else ""
                ),
            )
        )

    def save_last_join_time(self, player: str, time: Optional[datetime] = None) -> None:
        if self.player_is_ignore(player):
            return

        try:
            self.server.logger.debug(f"Saving last join time for {player}")
            self.data[player] = datetime.now() if time is None else time

            LAST_PIN_TIME_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = json.dumps({k: v.strftime(TIME_FORMAT) for k, v in self.data.items()})
            LAST_PIN_TIME_PATH.write_text(data, encoding="utf-8")
        except Exception as e:
            self.server.logger.error(f"Error saving last join time: {e}")

    def calc_activity_color(self, days: int) -> RColor:
        if days > self.config.inactive:
            return RColor.red
        if days > self.config.normal:
            return RColor.yellow  # orange
        if days > self.config.active:
            return RColor.yellow
        if days > 0:
            return RColor.green
        return RColor.gray

    # - 1. {} [在 線]
    # - 2. {} [ 20天]
    # - 3. {} [ 30天]
    # - 4. {} [120天]
    def format_last_join_player_list(self):
        import minecraft_data_api as api  # type: ignore

        data: APIPlayerListQueryResult = api.get_server_player_list()
        # amount, limit, online_players = data
        _, _, online_players = data

        index = 1
        result: List[RTextBase] = []
        for player in online_players:
            if self.player_is_ignore(player):
                continue

            result.append(
                RTextList(
                    RText(f"{index:02d}. ", color=RColor.green),
                    RText("[在  線] ", color=RColor.green),
                    f"{player:20}",
                )
            )
            index += 1

        players = [
            (player, self.calc_days(time))
            for player, time in self.data.items()
            if player not in online_players or self.player_is_ignore(player)
        ]
        players.sort(key=lambda x: x[1], reverse=True)
        for player, days in players:
            result.append(
                RTextList(
                    RText(f"{index:02d}. ", color=RColor.green),
                    RText(f"[{days:03d}天] ", color=self.calc_activity_color(days)),
                    f"{player:20}",
                )
            )
            index += 1

        return result

    def player_is_ignore(self, player: str) -> bool:
        return any(re.match(regex, player) for regex in self.config.ignore_player_regex)

    def get_all_last_join_time(self) -> Dict[str, datetime]:
        try:
            if not LAST_PIN_TIME_PATH.exists():
                LAST_PIN_TIME_PATH.parent.mkdir(parents=True, exist_ok=True)
                LAST_PIN_TIME_PATH.write_text("{}", encoding="utf-8")
                return {}

            data = dict[str, str](json.loads(LAST_PIN_TIME_PATH.read_text(encoding="utf-8"))).items()
            return {k: datetime.strptime(v, TIME_FORMAT) for k, v in data}
        except Exception as e:
            self.server.logger.error(f"Error getting last join time: {e}")
            return {}

    def calc_days(self, time: datetime) -> int:
        return (datetime.now() - time).days

    def get_last_join_time_days(self, player: str, write: bool = False) -> int:
        try:
            last_time = self.data.get(player)
            if last_time is None:
                if write:
                    self.save_last_join_time(player)
                    return 0
                return -1  # Not found

            return self.calc_days(last_time)
        except Exception as e:
            self.server.logger.error(f"Error getting last join time: {e}")
            return -1  # Error


def on_player_joined(server: ServerInterface, player: str, info: Info) -> None:
    if manager is not None:
        manager.display_motd(lambda msg: server.tell(player, msg), player)
    else:
        server.logger.error("PluginManager is not initialized")


def on_player_left(server: ServerInterface, player: str) -> None:
    if manager is not None:
        manager.save_last_join_time(player)
    else:
        server.logger.error("PluginManager is not initialized")


def on_load(server: PluginServerInterface, old) -> None:
    global manager

    config: Config = server.load_config_simple(
        file_name=str(CONFIG_FILE_PATH),
        in_data_folder=False,
        target_class=Config,
    )  # type: ignore

    manager = PluginManager(server, config)
    manager.register()
