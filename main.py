"""精确匹配回复插件。

消息内容与触发词完全一致时才回复，避免子串误触。
规则按“触发词 + 回复”的组维护，每组包含一个触发词和对应的回复；
插件直接发送回复，不会调用模型。私聊直接匹配；群聊默认需要 @机器人 或使用唤醒词，可在配置中关闭。

作者：Slime
版本：1.0.1
"""

import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star


class ExactMatchPlugin(Star):
    """消息与触发词完全一致时回复对应内容；群聊是否需先触发机器人可配置。"""

    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context)
        self.config = config if config is not None else {}
        self.rules = self._load_rules(self.config.get("rules", []))

        if self.rules:
            logger.info(f"精确匹配插件已加载，共 {len(self.rules)} 条规则")
        else:
            logger.warning("精确匹配插件已加载，但没有可用的匹配规则")

    @staticmethod
    def _load_rules(raw_rules) -> list[dict[str, str | bool]]:
        """把配置中的规则组转换为可匹配的规则列表。"""
        if not isinstance(raw_rules, list):
            return []

        rules: list[dict[str, str | bool]] = []
        for item in raw_rules:
            if not isinstance(item, dict):
                continue

            trigger = item.get("trigger")
            response = item.get("response")
            if not isinstance(trigger, str) or not isinstance(response, str):
                continue

            trigger = trigger.strip()
            if not trigger or not response.strip():
                continue

            bot_id = item.get("bot_id")
            bot_id = str(bot_id).strip() if bot_id is not None else ""

            require_wake = item.get("require_wake", True)
            if not isinstance(require_wake, bool):
                require_wake = True

            rules.append(
                {
                    "trigger": trigger,
                    "response": response,
                    "bot_id": bot_id,
                    "require_wake": require_wake,
                }
            )

        return rules

    @staticmethod
    def _get_self_id(event: AstrMessageEvent) -> str:
        """获取机器人自身的账号 ID。"""
        getter = getattr(event, "get_self_id", None)
        self_id = getter() if callable(getter) else ""
        if not self_id:
            self_id = getattr(event.message_obj, "self_id", "")
        return str(self_id) if self_id is not None else ""

    @staticmethod
    def _get_platform_id(event: AstrMessageEvent) -> str:
        """获取平台实例 ID，即平台设置中的 Bot ID。"""
        getter = getattr(event, "get_platform_id", None)
        platform_id = getter() if callable(getter) else ""
        if not platform_id:
            platform_id = getattr(getattr(event, "platform_meta", None), "id", "")
        return str(platform_id) if platform_id is not None else ""

    @staticmethod
    def _read_meta(meta, key: str):
        """兼容 PlatformMetadata 对象和 dict。"""
        if isinstance(meta, dict):
            return meta.get(key)
        return getattr(meta, key, None)

    def _bot_aliases(self, event: AstrMessageEvent) -> set[str]:
        """收集当前机器人的可用标识：平台实例 ID、账号 ID 和实例名称。"""
        platform_id = self._get_platform_id(event)
        aliases = {
            value
            for value in (platform_id, self._get_self_id(event))
            if value
        }

        manager = getattr(self.context, "platform_manager", None)
        getter = getattr(manager, "get_insts", None)
        if not platform_id or not callable(getter):
            return aliases

        try:
            instances = getter() or []
        except Exception:  # noqa: BLE001
            return aliases

        for instance in instances:
            meta_getter = getattr(instance, "meta", None)
            meta = meta_getter() if callable(meta_getter) else None
            config = getattr(instance, "config", None)
            if not isinstance(config, dict):
                config = {}

            instance_id = (
                self._read_meta(meta, "id")
                or getattr(instance, "platform_id", None)
                or getattr(instance, "id", None)
                or config.get("id")
            )
            if str(instance_id) != platform_id:
                continue

            if config.get("name"):
                aliases.add(str(config["name"]))
            break

        return aliases

    @staticmethod
    def _is_woken(event: AstrMessageEvent) -> bool:
        """私聊视为已触发；群聊判断是否 @机器人 或使用了唤醒词。"""
        is_private_chat = getattr(event, "is_private_chat", None)
        if callable(is_private_chat) and is_private_chat():
            return True
        return bool(getattr(event, "is_at_or_wake_command", False))

    @staticmethod
    def _extract_content(event: AstrMessageEvent) -> str:
        """提取用户实际发送的文本，忽略 @机器人 本身。"""
        message_chain = getattr(event.message_obj, "message", None) or []
        self_id = ExactMatchPlugin._get_self_id(event)

        if any(
            isinstance(seg, Comp.At) and str(seg.qq) == self_id
            for seg in message_chain
        ):
            text_parts = [
                seg.text for seg in message_chain if isinstance(seg, Comp.Plain)
            ]
            return "".join(text_parts).strip()

        return (event.message_str or "").strip()

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        """消息与触发词完全一致时发送对应的回复。"""
        content = self._extract_content(event)
        if not content:
            return

        aliases = (
            self._bot_aliases(event)
            if any(rule["bot_id"] for rule in self.rules)
            else set()
        )
        woken = self._is_woken(event)
        for rule in self.rules:
            if rule["bot_id"] and rule["bot_id"] not in aliases:
                continue
            if rule["require_wake"] and not woken:
                continue
            if content == rule["trigger"]:
                yield event.plain_result(rule["response"])
                return

    async def terminate(self):
        """插件卸载时无需额外清理。"""
        pass
