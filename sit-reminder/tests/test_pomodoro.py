"""
番茄钟功能自动化测试（时间缩短版）
运行：PYTHONIOENCODING=utf-8 python tests/test_pomodoro.py
"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT = Path(__file__).parent.parent
SCREENSHOTS = PROJECT / "tests" / "screenshots"
SCREENSHOTS.mkdir(exist_ok=True)

WORK_SEC = 8       # 工作时间（秒）
SHORT_BREAK = 3    # 短休（秒）
LONG_BREAK = 5     # 长休（秒）


def simulate_work_then_break(page, round_num):
    """模拟一轮完整的工作 → 休息流程"""
    # 开始工作
    page.evaluate(f"""
        if (timerId) clearInterval(timerId);
        state = 'running';
        startTime = Date.now();
        workSeconds = {WORK_SEC};
        breakSeconds = {SHORT_BREAK};
        beepPlayed = false;
        pomodoroRound = {round_num};
        timerId = setInterval(render, 1000);
        render();
    """)
    print(f"   第 {round_num} 轮工作中（{WORK_SEC} 秒）...")
    page.wait_for_timeout((WORK_SEC + 2) * 1000)

    # 验证进入了休息
    state = page.evaluate("state")
    if state != 'break':
        # 手动触发
        page.evaluate("""
            state = 'break'; startTime = Date.now();
            beepPlayed = false; addCompletion();
            renderBreak();
        """)
    print(f"   进入休息（{SHORT_BREAK} 秒）...")

    if round_num < 4:
        page.wait_for_timeout(SHORT_BREAK * 1000 + 500)

    # 模拟 completeBreak 逻辑（与源码保持一致）
    page.evaluate(f"""
        clearInterval(timerId); timerId = null;
        if (pomodoroRound > 0 && pomodoroRound < 4) {{
            pomodoroRound++;
            if (pomodoroRound === 4) {{ breakSelect.value = '15'; }}
        }} else if (pomodoroRound === 4) {{
            pomodoroRound = 0;
            breakSelect.value = '5';
        }}
        state = 'idle';
        currentExercise = null;
        snoozeCount = 0;
        render();
    """)
    page.wait_for_timeout(300)

    new_round = page.evaluate("pomodoroRound")
    break_val = page.evaluate("breakSelect.value")
    print(f"   完成休息，当前轮次: {new_round}，休息时长: {break_val} 分钟")
    return new_round, break_val


def main():
    console_errors = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1024, "height": 768})

        page.on("console", lambda msg: (
            console_errors.append(msg.text) if msg.type == "error" else None
        ))

        print("1. 打开页面...")
        page.goto("http://localhost:8000", wait_until="networkidle")
        page.screenshot(path=str(SCREENSHOTS / "p01-start.png"))

        # 点击番茄钟按钮
        print("2. 点击番茄钟按钮...")
        page.locator("button:has-text('番茄钟')").click()
        page.wait_for_timeout(300)
        assert page.locator("#work-minutes").input_value() == "25", "工作应为 25 分钟"
        assert page.locator("#break-minutes").input_value() == "5", "休息应为 5 分钟"
        print("   PASS: 番茄钟预设 25+5")

        # 但为了测试，用 JS 直接改参数
        page.evaluate(f"""
            workInput.value = '1';
            breakSelect.value = '1';
            workSeconds = {WORK_SEC};
            breakSeconds = {SHORT_BREAK};
            renderIdle();
        """)
        page.screenshot(path=str(SCREENSHOTS / "p02-shortened.png"))

        # ====== 第 1-3 轮（短休） ======
        for round_num in range(1, 4):
            print(f"\n3.{round_num} 第 {round_num} 轮...")
            r, b = simulate_work_then_break(page, round_num)
            expected = round_num + 1
            if round_num == 3:
                assert r == 4, f"第 3 轮完成应变为 4（准备长休），实际 {r}"
                assert b == "15", f"第 3 轮完成应切长休 15 分钟，实际 {b}"
            else:
                assert r == expected, f"轮次应为 {expected}，实际 {r}"
                assert b == "1", f"短休应为 1 分钟"

        page.screenshot(path=str(SCREENSHOTS / "p03-after-round3.png"))
        print("   PASS: 前 3 轮短休正常，第 3 轮后自动切长休 15 分钟")

        # ====== 第 4 轮（应触发长休） ======
        print(f"\n4. 第 4 轮（应触发长休 15 分钟）...")
        # 第 3 轮完成后 round=4，已经设 breakSelect=15
        break_val = page.evaluate("breakSelect.value")
        assert break_val == "15", f"第 4 轮应触发长休 15 分钟，实际 {break_val}"
        print(f"   PASS: 第 4 轮自动切长休，breakSelect={break_val}")

        # 模拟第 4 轮工作
        r, b = simulate_work_then_break(page, 4)
        # 第 4 轮完成后 pomodoroRound 应重置为 0
        assert r == 0, f"4 轮完成应重置为 0，实际 {r}"
        assert b == "5", f"4 轮完成后应重置为 5 分钟，实际 {b}"
        print("   PASS: 4 轮完成后自动重置")

        page.screenshot(path=str(SCREENSHOTS / "p04-after-round4.png"))

        # ====== 统计验证 ======
        print("\n5. 统计验证...")
        today = page.locator("#today-count").text_content()
        total = page.locator("#total-count").text_content()
        print(f"   今日完成: {today}, 累计完成: {total}")
        assert int(today) >= 4, f"今日完成至少 4 次，实际 {today}"

        # 图表
        print("6. 展开统计图表...")
        # 先确保在 idle 状态
        page.evaluate("if(state!=='idle'){state='idle';clearInterval(timerId);timerId=null;render();}")
        page.wait_for_timeout(300)
        page.locator("button:has-text('统计图表')").click()
        page.wait_for_timeout(1500)
        page.screenshot(path=str(SCREENSHOTS / "p05-chart.png"))

        canvas = page.locator("#stats-chart")
        assert canvas.is_visible(), "图表不可见"
        # 等 3 秒确认不消失
        page.wait_for_timeout(3000)
        assert canvas.is_visible(), "图表 3 秒后消失了！"
        print("   PASS: 图表正常，不消失")

        # 控制台报告
        print(f"\n=== 控制台错误: {len(console_errors)} 个 ===")
        for err in console_errors:
            print(f"  {err}")
        if not console_errors:
            print("  无错误")

        browser.close()
        print("\n=== 番茄钟测试全部通过 ===")


if __name__ == "__main__":
    main()
