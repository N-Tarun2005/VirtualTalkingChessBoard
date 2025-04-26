import pyautogui
import time
from PIL import Image
import os
import cv2
import numpy as np
import pyttsx3

# === Setup working directory ===
project_folder = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_folder)

# === Coordinate Handling ===
coords_file = os.path.join(project_folder, "coords.txt")

if os.path.exists(coords_file):
    with open(coords_file, "r") as f:
        lines = f.readlines()
        x1, y1 = map(int, lines[0].split(","))
        x2, y2 = map(int, lines[1].split(","))
    print(f"📌 Loaded saved board coordinates: Top-Left ({x1}, {y1}), Bottom-Right ({x2}, {y2})")
else:
    print("👡 Move mouse to TOP-LEFT of the board. You have 5 seconds...")
    time.sleep(5)
    top_left = pyautogui.position()
    x1, y1 = top_left
    print("Top-left:", top_left)

    print("👡 Now move to BOTTOM-RIGHT of the board. You have 5 seconds...")
    time.sleep(5)
    bottom_right = pyautogui.position()
    x2, y2 = bottom_right
    print("Bottom-right:", bottom_right)

    with open(coords_file, "w") as f:
        f.write(f"{x1},{y1}\n{x2},{y2}")
    print("🗕 Board coordinates saved for future use.")

if x2 < x1:
    x1, x2 = x2, x1
if y2 < y1:
    y1, y2 = y2, y1

width = x2 - x1
height = y2 - y1

if width == 0 or height == 0:
    print("❌ Invalid selection: Region size is zero.")
    exit()

region = (x1, y1, width, height)

# === Screenshot function ===
def capture_board(name):
    path = os.path.join(project_folder, f"{name}.png")
    screenshot = pyautogui.screenshot(region=region)
    screenshot.save(path)
    print(f"✅ {name}.png saved.")
    return path

# === Split Board into 64 Squares ===
def split_board(image_path, tag):
    board_img = Image.open(image_path)
    square_size_x = board_img.size[0] // 8
    square_size_y = board_img.size[1] // 8

    squares_folder = os.path.join(project_folder, f"squares_{tag}")
    os.makedirs(squares_folder, exist_ok=True)

    for row in range(8):
        for col in range(8):
            left = col * square_size_x
            top = row * square_size_y
            right = left + square_size_x
            bottom = top + square_size_y

            square_img = board_img.crop((left, top, right, bottom))
            square_name = chr(97 + col) + str(8 - row)
            square_img.save(os.path.join(squares_folder, f"{square_name}.png"))

    print(f"🧹 Split done for {tag} board into: {squares_folder}")
    return squares_folder

# === Detect Changes Between Two Boards ===
def detect_change(before_folder, after_folder):
    changed = []
    for filename in sorted(os.listdir(before_folder)):
        before_img = Image.open(os.path.join(before_folder, filename))
        after_img = Image.open(os.path.join(after_folder, filename))

        before_np = np.array(before_img.convert("L"))
        after_np = np.array(after_img.convert("L"))

        diff = cv2.absdiff(before_np, after_np)
        score = np.sum(diff)

        if score > 100000:  # Adjust this threshold if needed
            changed.append(filename.replace(".png", ""))

    return changed

# === Template Matching for Pieces ===
def match_piece(square_image, templates_folder):
    best_match = None
    best_score = float('inf')

    for template_name in os.listdir(templates_folder):
        template_path = os.path.join(templates_folder, template_name)
        template_img = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        
        square_gray = np.array(square_image.convert('L'))

        # Template Matching
        res = cv2.matchTemplate(square_gray, template_img, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        print(f"Matching {template_name} with score {max_val}")  # Debugging line

        if max_val > 0.7:  # Adjusted threshold for better matching
            best_match = template_name.replace(".png", "")
            best_score = max_val
            break  # Once a match is found, exit loop

    return best_match if best_match else "Unknown"

# === Speak function ===
def speak(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    engine.say(text)
    engine.runAndWait()

# === Loop to detect moves every 2-3 seconds ===
def continuously_check_for_moves():
    previous_board_path = None
    while True:
        input("\n📸 Press Enter to capture BEFORE move (board1.png)...")
        before_path = capture_board("board1")
        
        input("\n🔹 Make a move, then press Enter to capture AFTER move (board2.png)...")
        after_path = capture_board("board2")

        before_squares = split_board(before_path, "before")
        after_squares = split_board(after_path, "after")

        changes = detect_change(before_squares, after_squares)

        if len(changes) == 2:
            from_square, to_square = None, None
            before_img1 = Image.open(os.path.join(before_squares, f"{changes[0]}.png")).convert("L")
            after_img1 = Image.open(os.path.join(after_squares, f"{changes[0]}.png")).convert("L")
            before_sum1 = np.sum(np.array(before_img1))
            after_sum1 = np.sum(np.array(after_img1))

            before_img2 = Image.open(os.path.join(before_squares, f"{changes[1]}.png")).convert("L")
            after_img2 = Image.open(os.path.join(after_squares, f"{changes[1]}.png")).convert("L")
            before_sum2 = np.sum(np.array(before_img2))
            after_sum2 = np.sum(np.array(after_img2))

            if before_sum1 > after_sum1:
                from_square = changes[0]
                to_square = changes[1]
            else:
                from_square = changes[1]
                to_square = changes[0]

            # Match piece from before and after
            print(f"Matching piece for square {from_square}")
            piece_from = match_piece(before_img1, "path_to_templates_folder")  # Update path here
            piece_to = match_piece(after_img2, "path_to_templates_folder")  # Update path here

            move = f"{piece_from} moved from {from_square} to {to_square}"
            print("\n🗣 Move Detected:", move)
            speak(f"{piece_from} moved from {from_square} to {to_square}")
        else:
            print("⚠ No move detected.")
            speak("No move detected.")
        
        # Wait for 2-3 seconds before checking again
        time.sleep(2 + (3 - 2) * np.random.random())

# === Main Execution ===
continuously_check_for_moves()

# === Reset Coordinates ===
def reset_coords():
    if os.path.exists(coords_file):
        os.remove(coords_file)
        print("🔄 Coordinates reset. Run the script again to set new corners.")

# Uncomment this line to reset coords when needed
# reset_coords()