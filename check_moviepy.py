import sys
import shutil
import moviepy.editor as mp

print("Python executable:", sys.executable)
print("Python version:", sys.version)

ffmpeg_path = shutil.which("ffmpeg")
print("ffmpeg path:", ffmpeg_path)

try:
    # создаём маленький тестовый клип
    clip = mp.ColorClip(size=(10, 10), color=(255, 0, 0), duration=0.5)
    clip.write_videofile("test.mp4", fps=24)
    print("MoviePy работает")
except Exception as e:
    print("Ошибка MoviePy:", e)
