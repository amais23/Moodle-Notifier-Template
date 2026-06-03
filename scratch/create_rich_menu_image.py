import os
from PIL import Image

def crop_and_resize_integrated():
    ai_img_path = r"C:\Users\chiah\.gemini\antigravity-ide\brain\6a6e08a7-55dd-4552-af29-728717bc77b7\rich_menu_widescreen_integrated_1780527908828.png"
    if not os.path.exists(ai_img_path):
        print("Error: AI integrated image not found!")
        return

    # 1. 讀取 AI 生成的一體化選單圖片 (1024x1024)
    img = Image.open(ai_img_path).convert("RGBA")
    
    # 2. 定義目標規格
    target_w = 2500
    target_h = 1686
    target_aspect = target_w / target_h # 1.4828
    
    # 3. 進行等比裁切 (Aspect Fill)
    # 為了完全保留卡片頂部上沿與底部文字，我們微調 Y 軸起點至 160 像素
    new_w = 1024
    new_h = int(new_w / target_aspect) # 690
    
    left = 0
    top = 167 # 中央對稱裁切
    right = new_w
    bottom = top + new_h # 857
    
    print(f"Cropping region: left={left}, top={top}, right={right}, bottom={bottom}")
    cropped_img = img.crop((left, top, right, bottom))
    
    # 4. 縮放到 2500x1686，完全不變形
    final_img = cropped_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    
    # 5. 轉成 RGB 以儲存 JPG
    final_rgb = final_img.convert("RGB")
    
    output_png = r"c:\Users\chiah\Documents\moodle notifier\frontend\public\rich_menu_template.png"
    output_jpg = r"c:\Users\chiah\Documents\moodle notifier\frontend\public\rich_menu_template.jpg"
    
    os.makedirs(os.path.dirname(output_png), exist_ok=True)
    
    final_img.save(output_png, "PNG")
    final_rgb.save(output_jpg, "JPEG", quality=95)
    print("Rich menu image cropped and resized successfully!")

if __name__ == "__main__":
    crop_and_resize_integrated()
