import imageio
from PIL import Image
import os

input_webm = "/config/.gemini/antigravity/brain/1596fd6d-4215-4f92-9b21-1ac402f67dc6/wanderlust_ai_demo.webm"
output_gif = "/config/Desktop/NewProject/wanderlust-ai/demo.gif"

print("Reading webm file...")
reader = imageio.get_reader(input_webm)

frames = []
for i, frame in enumerate(reader):
    if i % 4 == 0:  # ~6 fps for web efficiency
        img = Image.fromarray(frame)
        w, h = img.size
        new_w = 640
        new_h = int(h * (new_w / w))
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        # Convert to P mode with palette quantization
        img_p = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=128)
        frames.append(img_p)

print(f"Extracted {len(frames)} frames. Saving lightweight looping GIF...")
frames[0].save(
    output_gif,
    save_all=True,
    append_images=frames[1:],
    optimize=True,
    duration=150,
    loop=0
)

file_size_mb = os.path.getsize(output_gif) / (1024 * 1024)
print(f"Successfully generated optimized GIF: {output_gif} ({file_size_mb:.2f} MB)")
