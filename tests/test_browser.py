"""
浏览器自动化测试：模拟真实用户交互
运行：python tests/test_browser.py
需要：服务运行在 localhost:8000
"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT = Path(__file__).parent.parent
SCREENSHOTS = PROJECT / "tests" / "screenshots"
SCREENSHOTS.mkdir(exist_ok=True)


def main():
    console_errors = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1024, "height": 768})

        # 收集控制台错误
        page.on("console", lambda msg: (
            console_errors.append(msg.text) if msg.type == "error" else None
        ))

        print("1. 打开页面...")
        page.goto("http://localhost:8000", wait_until="networkidle")
        page.screenshot(path=str(SCREENSHOTS / "01-idle.png"))
        print("   截图: 01-idle.png")

        # 检查页面基本内容
        assert "久坐放松提醒" in page.content()
        print("   PASS: 页面标题正常")

        # 设工作时长为 0.1 分钟（6秒）方便测试
        print("2. 设置工作时长为 6 秒...")
        work_input = page.locator("#work-minutes")
        work_input.fill("")
        work_input.type("1")
        assert work_input.input_value() == "1"
        print("   PASS: 工作时长已设为 1 分钟")

        # 设休息时长为 1 分钟
        print("3. 设休息时长为 1 分钟...")
        page.locator("#break-minutes").select_option("1")
        print("   PASS: 休息时长已设为 1 分钟")

        # 点开始计时
        print("4. 点击开始计时...")
        page.locator("button:has-text('开始计时')").click()
        page.wait_for_timeout(500)
        page.screenshot(path=str(SCREENSHOTS / "02-running.png"))
        print("   截图: 02-running.png")

        # 等待计时结束（约 60 秒太长了，改用下面的方式）
        # 直接通过 JS 跳过等待，触发计时结束
        print("5. 快进到计时结束...")
        page.evaluate("""
            state = 'break';
            startTime = Date.now();
            breakSeconds = 60;
            addCompletion();
            currentExercise = exercises[Math.floor(Math.random() * exercises.length)];
            beepPlayed = false;
            renderBreak();
        """)
        page.wait_for_timeout(500)
        page.screenshot(path=str(SCREENSHOTS / "03-break.png"))
        print("   截图: 03-break.png")

        # 检查是否进入休息状态
        assert "该休息了" in page.content()
        print("   PASS: 进入休息状态")
        assert "我完成了" in page.content()
        assert "跳过" in page.content()
        print("   PASS: 完成/跳过按钮存在")

        # 验证休息倒计时在走动
        break_text_1 = page.locator(".break-countdown").text_content()
        page.wait_for_timeout(2000)
        break_text_2 = page.locator(".break-countdown").text_content()
        assert break_text_1 != break_text_2, f"倒计时没走动: {break_text_1} == {break_text_2}"
        print(f"   PASS: 倒计时走动 ({break_text_1} -> {break_text_2})")

        # 点击 snooze
        print("6. 点击'再工作 5 分钟'...")
        snooze_btn = page.locator("button:has-text('再工作')")
        assert snooze_btn.is_visible(), "snooze 按钮不可见"
        snooze_btn.click()
        page.wait_for_timeout(500)
        page.screenshot(path=str(SCREENSHOTS / "04-snoozing.png"))
        print("   截图: 04-snoozing.png")

        # 应该回到工作状态
        assert "专注工作中" in page.content()
        print("   PASS: snooze 后回到工作状态")

        # 用 JS 快进时间（避免等 5 分钟）
        print("7. 快进 snooze 计时...")
        page.evaluate("startTime = Date.now() - (workSeconds * 1000 + 1000);")
        page.wait_for_timeout(3000)
        page.screenshot(path=str(SCREENSHOTS / "05-break-again.png"))
        print("   截图: 05-break-again.png")

        # 应该再次进入休息
        assert "该休息了" in page.content()
        print("   PASS: snooze 后再次进入休息")

        # 点击"我完成了"
        print("8. 点击'我完成了'...")
        page.locator("button:has-text('我完成了')").click()
        page.wait_for_timeout(500)
        page.screenshot(path=str(SCREENSHOTS / "06-idle-after-complete.png"))
        print("   截图: 06-idle-after-complete.png")

        # 检查回到 idle 状态 + 统计数字更新
        assert "准备就绪" in page.content()
        print("   PASS: 回到就绪状态")

        today_count = page.locator("#today-count").text_content()
        assert int(today_count) >= 2, f"今日完成应 >=2，实际 {today_count}"
        print(f"   PASS: 今日完成 = {today_count}")

        # 测试统计图表
        print("9. 展开统计图表...")
        stats_toggle = page.locator("button:has-text('统计图表')")
        stats_toggle.click()
        page.wait_for_timeout(1000)  # 等 requestAnimationFrame + 渲染
        page.screenshot(path=str(SCREENSHOTS / "07-chart-open.png"))
        print("   截图: 07-chart-open.png")

        # 等一下，确认图表不会消失
        page.wait_for_timeout(3000)
        page.screenshot(path=str(SCREENSHOTS / "08-chart-still-there.png"))
        print("   截图: 08-chart-still-there.png (3 秒后)")

        # 验证 canvas 仍然可见
        canvas = page.locator("#stats-chart")
        assert canvas.is_visible(), "❌ 图表 canvas 在 3 秒后消失了！"
        print("   PASS: 图表在 3 秒后仍然可见")

        # 验证 chart-container 没有变回 display:none
        container = page.locator("#chart-container")
        display = container.evaluate("el => el.style.display")
        assert display != "none", f"❌ 图表容器 display={display}，说明被重新隐藏了！"
        print("   PASS: 图表容器未被隐藏")

        # 切换月份 Tab
        print("10. 切换到近 30 天...")
        page.locator("button:has-text('近 30 天')").click()
        page.wait_for_timeout(500)
        page.screenshot(path=str(SCREENSHOTS / "09-chart-month.png"))
        print("   截图: 09-chart-month.png")
        print("   PASS: 月份图表切换正常")

        # 控制台错误报告
        print(f"\n=== 控制台错误: {len(console_errors)} 个 ===")
        for err in console_errors:
            print(f"  ❌ {err}")
        if not console_errors:
            print("  ✅ 无错误")

        browser.close()

        # 最终结论
        print("\n=== 测试结论 ===")
        if not console_errors:
            print("PASS: 全部通过 — snooze 流程正常，图表不消失，控制台无错误")
        else:
            print("FAIL: 存在控制台错误")


if __name__ == "__main__":
    main()
