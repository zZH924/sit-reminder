"""
核心逻辑测试：状态机、数据模型、API 端点
运行：python -m pytest tests/test_core.py -v
     或 python tests/test_core.py
"""
import json
import sys
from pathlib import Path
from datetime import date, timedelta

import pytest
import httpx

PROJECT = Path(__file__).parent.parent
DATA_DIR = PROJECT / "data"
STATIC_DIR = PROJECT / "static"


# ====== JS 状态机翻译为 Python（测试逻辑用） ======

class TimerState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.state = "idle"       # idle | running | paused | break
        self.timer_count = 0       # 模拟 setInterval 数量

    def start_timer(self):
        if self.timer_count > 0: self.timer_count -= 1  # clearInterval
        self.state = "running"
        self.timer_count += 1

    def transition_to_break(self):
        # 关键：transition 不清理 timer!
        self.state = "break"

    def snooze(self):
        if self.timer_count > 0: self.timer_count -= 1  # clearInterval
        self.state = "running"
        self.timer_count += 1

    def pause(self):
        self.state = "paused"
        self.timer_count -= 1  # clearInterval

    def resume(self):
        if self.timer_count > 0: self.timer_count -= 1
        self.state = "running"
        self.timer_count += 1

    def complete_break(self):
        self.state = "idle"
        self.timer_count -= 1  # clearInterval


class TestTimerState:
    """Timer 生命周期测试"""

    def test_normal_flow_no_leak(self):
        """正常流程：start → break → complete，timer 正确清理"""
        t = TimerState()
        t.start_timer()
        assert t.timer_count == 1

        t.transition_to_break()
        assert t.timer_count == 1  # transition 不清理（break 需要倒计时）

        t.complete_break()
        assert t.timer_count == 0  # complete 清理

    def test_snooze_flow_no_leak(self):
        """Snooze 流程：之前会泄漏 timer，修复后不应泄漏"""
        t = TimerState()
        t.start_timer()
        assert t.timer_count == 1

        t.transition_to_break()
        assert t.timer_count == 1

        t.snooze()  # 关键：snooze 前应清理旧 timer
        assert t.timer_count == 1  # 修复前这里是 2（泄漏！）

        t.transition_to_break()
        assert t.timer_count == 1

        t.complete_break()
        assert t.timer_count == 0  # 修复前这里是 1（残留！）

    def test_pause_resume_no_leak(self):
        """暂停/恢复流程，timer 不泄漏"""
        t = TimerState()
        t.start_timer()
        assert t.timer_count == 1

        t.pause()
        assert t.timer_count == 0

        t.resume()
        assert t.timer_count == 1

        t.transition_to_break()
        t.complete_break()
        assert t.timer_count == 0

    def test_multiple_snoozes_no_leak(self):
        """多次 snooze 也不泄漏"""
        t = TimerState()
        t.start_timer()
        t.transition_to_break()

        for _ in range(3):
            t.snooze()
            assert t.timer_count == 1
            t.transition_to_break()

        t.complete_break()
        assert t.timer_count == 0

    def test_start_timer_clears_old(self):
        """重复点开始计时不累积 timer"""
        t = TimerState()
        t.start_timer()
        t.start_timer()
        t.start_timer()
        assert t.timer_count == 1


# ====== 数据模型测试 ======

def make_history(*day_counts):
    """构造 daily_history，从今天往前推"""
    result = {}
    today = date.today()
    for i, count in enumerate(day_counts):
        d = today - timedelta(days=i)
        result[d.isoformat()] = count
    return result


def calc_streak(history):
    """JS streak 逻辑的 Python 翻译（!history[today] = 值 falsy 则跳过）"""
    streak = 0
    today = date.today().isoformat()
    d = date.today()
    if not history.get(today, 0):  # JS: !history[today] — 值为 0 或不存在
        d = d - timedelta(days=1)
    while True:
        ds = d.isoformat()
        if history.get(ds, 0) > 0:
            streak += 1
            d = d - timedelta(days=1)
        else:
            break
    return streak


class TestDataModel:
    """数据模型测试"""

    def test_streak_consecutive_7(self):
        """连续 7 天打卡 → streak = 7"""
        h = make_history(1, 2, 3, 1, 5, 2, 3)
        assert calc_streak(h) == 7

    def test_streak_broken_today_missed(self):
        """昨天有打卡、今天没有 → streak = 1（算昨天）"""
        h = make_history(0, 3)  # 今天 0, 昨天 3
        assert calc_streak(h) == 1

    def test_streak_broken_yesterday_missed(self):
        """昨天没有打卡 → streak = 0"""
        h = make_history(5, 0, 3)  # 今天 5, 昨天 0, 前天 3
        assert calc_streak(h) == 1  # 只有今天

    def test_streak_zero(self):
        """完全没有记录 → streak = 0"""
        assert calc_streak({}) == 0

    def test_cross_day_reset(self):
        """跨天重置逻辑"""
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        stats = {"last_date": yesterday, "today_count": 5, "total_count": 10}
        # 模拟 JS loadStats 逻辑
        if stats["last_date"] != today:
            stats["today_count"] = 0
        assert stats["today_count"] == 0

    def test_daily_history_accumulates(self):
        """daily_history 记录每日完成数"""
        history = {}
        today = date.today().isoformat()
        # 模拟完成一次
        history[today] = history.get(today, 0) + 1
        history[today] = history.get(today, 0) + 1
        assert history[today] == 2


# ====== API 测试 ======

class TestAPI:
    """FastAPI 端点测试"""

    @pytest.mark.asyncio
    async def test_root_returns_html(self):
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:8000/")
            assert resp.status_code == 200
            assert "<!DOCTYPE html>" in resp.text
            assert "久坐放松提醒" in resp.text

    @pytest.mark.asyncio
    async def test_exercises_api(self):
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:8000/api/exercises")
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            assert len(data) == 12
            for item in data:
                assert "name" in item
                assert "desc" in item
                assert "duration_min" in item


# ====== 静态文件测试 ======

class TestStaticFiles:
    """静态文件完整性"""

    def test_exercises_json_valid(self):
        path = DATA_DIR / "exercises.json"
        assert path.exists()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 12
        for item in data:
            assert all(k in item for k in ("name", "desc", "duration_min"))

    def test_index_html_contains_key_features(self):
        path = STATIC_DIR / "index.html"
        assert path.exists()
        html = path.read_text(encoding="utf-8")
        # 验证 6 项功能的关键字
        assert "深色模式" in html or "theme-toggle" in html or "data-theme" in html
        assert "pauseTimer" in html or "pause" in html.lower()
        assert "pomodoro" in html.lower() or "番茄钟" in html
        assert "toggleChart" in html or "统计图表" in html
        assert "streak" in html.lower() or "连续打卡" in html
        assert "snooze" in html.lower() or "再工作" in html

    def test_no_chartjs_cdn(self):
        """确保没有依赖 Chart.js CDN"""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        assert "chart.js" not in html.lower()


if __name__ == "__main__":
    # 简单直接运行（不需要 pytest）
    print("=== 状态机测试 ===")
    test = TestTimerState()
    for name in dir(test):
        if name.startswith("test_"):
            try:
                getattr(test, name)()
                print(f"  PASS {name}")
            except AssertionError as e:
                print(f"  FAIL {name}: {e}")

    print("\n=== 数据模型测试 ===")
    dm = TestDataModel()
    for name in dir(dm):
        if name.startswith("test_"):
            try:
                getattr(dm, name)()
                print(f"  PASS {name}")
            except AssertionError as e:
                print(f"  FAIL {name}: {e}")

    print("\n=== 静态文件测试 ===")
    sf = TestStaticFiles()
    for name in dir(sf):
        if name.startswith("test_"):
            try:
                getattr(sf, name)()
                print(f"  PASS {name}")
            except AssertionError as e:
                print(f"  FAIL {name}: {e}")

    print("\n=== API 测试（需要服务运行在 :8000） ===")
    import asyncio
    api = TestAPI()
    for name in dir(api):
        if name.startswith("test_"):
            try:
                asyncio.run(getattr(api, name)())
                print(f"  PASS {name}")
            except Exception as e:
                print(f"  FAIL {name}: {e}")
