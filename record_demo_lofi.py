import asyncio
import os
import shutil
import time
from playwright.async_api import async_playwright

ARTIFACT_DIR = "/config/.gemini/antigravity/brain/1596fd6d-4215-4f92-9b21-1ac402f67dc6"
OUTPUT_DIR = os.path.join(ARTIFACT_DIR, "demo_records_lofi")

async def record_demo_lofi():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-gpu",
                "--autoplay-policy=no-user-gesture-required"
            ]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=OUTPUT_DIR,
            record_video_size={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        print("Navigating to Wanderlust AI web app at http://localhost:8080...")
        await page.goto("http://localhost:8080")
        await page.wait_for_selector(".welcome-card", timeout=10000)
        
        # Inject and play upbeat lo-fi background music track
        print("Playing upbeat lo-fi background music track...")
        await page.evaluate("""() => {
            const audio = document.createElement('audio');
            audio.id = 'bg-lofi-music';
            audio.src = '/static/upbeat_lofi.wav';
            audio.loop = true;
            audio.volume = 0.5;
            document.body.appendChild(audio);
            audio.play().catch(e => console.log('Audio autoplay:', e));
        }""")
        await asyncio.sleep(2)

        # 1. Prompt 1: Best feature (3-day Kyoto trip itinerary with database lookup & budget breakdown)
        print("Sending Prompt 1: Plan a 3-day luxury trip to Kyoto...")
        await page.fill("#input", "Plan a 3-day luxury trip to Kyoto")
        await asyncio.sleep(1)
        await page.click("button[type='submit']")

        print("Waiting for Prompt 1 response...")
        await page.wait_for_selector(".msg.agent", timeout=30000)
        await page.wait_for_function("!document.querySelector('.typing-dots')", timeout=60000)
        await asyncio.sleep(4)

        # 2. Prompt 2: Richer prompt showing tool call & generated image
        print("Sending Prompt 2: Generate a scenic postcard image for Santorini and show live weather...")
        await page.fill("#input", "Generate a scenic postcard image for Santorini and show me live weather")
        await asyncio.sleep(1)
        await page.click("button[type='submit']")

        print("Waiting for Prompt 2 response with artwork & weather...")
        await asyncio.sleep(5)
        try:
            await page.wait_for_function("!document.querySelector('.typing-dots')", timeout=60000)
        except Exception as e:
            print("Timeout waiting for typing dots:", e)
        
        await asyncio.sleep(5)

        # Save video
        video_path = await page.video.path()
        print("Raw video recorded at:", video_path)

        await page.close()
        await context.close()
        await browser.close()

        target_file = os.path.join(ARTIFACT_DIR, "wanderlust_ai_demo_lofi.webm")
        shutil.copy(video_path, target_file)
        print("Saved demo video with lo-fi background music to:", target_file)

if __name__ == "__main__":
    asyncio.run(record_demo_lofi())
