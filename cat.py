# -*- coding: utf-8 -*-
"""小猫情绪系统

忠实保留原 C 版的小猫字符画（show_cat / show_cat_mood），
同时为图形界面提供 emoji 映射（GUI 里用 emoji 更清晰）。
"""
from enum import Enum


class CatMood(Enum):
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SLEEPY = "sleepy"
    CONFUSED = "confused"


# 图形界面用的 emoji
MOOD_EMOJI = {
    CatMood.HAPPY: "😺",
    CatMood.SAD: "😿",
    CatMood.ANGRY: "😾",
    CatMood.SLEEPY: "😴",
    CatMood.CONFUSED: "😕",
}

# 默认情绪话术
MOOD_DEFAULT_MSG = {
    CatMood.HAPPY: "喵~ 好开心！",
    CatMood.SAD: "喵... 有点难过",
    CatMood.ANGRY: "哼！喵生气了！",
    CatMood.SLEEPY: "喵~ 好困...",
    CatMood.CONFUSED: "喵？这是什么？",
}


def show_cat() -> str:
    """大猫字符画（对应原 C 的 show_cat）"""
    return (
        "    ______\n"
        "   ／＞　　フ\n"
        "  |  _  _ |\n"
        " ／` ミw ノ\n"
        " /　　　   |\n"
        "/　 ヽ　  ）\n"
        "│　　|　|　|\n"
        "／￣|　　|　|　|\n"
        "| (￣ヽ＿ヽ)__)\n"
        "＼二つ\n"
    )


def mood_text(mood: CatMood, message: str = "") -> str:
    """返回情绪提示（GUI 用）：emoji + 话术"""
    emoji = MOOD_EMOJI.get(mood, "🐱")
    msg = message or MOOD_DEFAULT_MSG.get(mood, "喵~")
    return f"{emoji} {msg}"
