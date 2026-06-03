import os
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

def create_rich_menu():
    bg_path = r"C:\Users\chiah\.gemini\antigravity-ide\brain\6a6e08a7-55dd-4552-af29-728717bc77b7\rich_menu_bg_1780527082541.png"
    if not os.path.exists(bg_path):
        print("Error: Background image not found!")
        return

    # 1. 讀取背景圖並強制 resize 至 LINE 大選單標準規格 (2500x1686)
    img = Image.open(bg_path).convert("RGBA").resize((2500, 1686), Image.Resampling.LANCZOS)
    
    # 2. 建立透明繪圖層，用來繪製半透明卡片與文字
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # area 定義
    cols = 3
    rows = 2
    width = 2500
    height = 1686
    card_w = 833
    card_h = 843
    
    # 卡片內距 (Padding)
    pad_x = 45
    pad_y = 45
    corner_radius = 45
    
    # 6 個卡片的內容，使用 Iconify API 獲取對應顏色的 Lucide 圖案透明 PNG
    cards = [
        {
            "title": "監控課程", 
            "icon_url": "https://api.iconify.design/lucide:book-open.png?color=%2389b4fa&width=200&height=200",
            "col": 0, "row": 0
        },
        {
            "title": "待繳作業", 
            "icon_url": "https://api.iconify.design/lucide:clipboard-list.png?color=%23f38ba8&width=200&height=200",
            "col": 1, "row": 0
        },
        {
            "title": "成績查詢", 
            "icon_url": "https://api.iconify.design/lucide:bar-chart-3.png?color=%23a6e3a1&width=200&height=200",
            "col": 2, "row": 0
        },
        {
            "title": "近期活動", 
            "icon_url": "https://api.iconify.design/lucide:calendar.png?color=%23f9e2af&width=200&height=200",
            "col": 0, "row": 1
        },
        {
            "title": "最新私訊", 
            "icon_url": "https://api.iconify.design/lucide:message-square.png?color=%23cba6f7&width=200&height=200",
            "col": 1, "row": 1
        },
        {
            "title": "控制台網頁", 
            "icon_url": "https://api.iconify.design/lucide:layout-dashboard.png?color=%2389dceb&width=200&height=200",
            "col": 2, "row": 1
        }
    ]
    
    # 載入中文字型
    font_path = "C:\\Windows\\Fonts\\msjhbd.ttc" # 微軟正黑體 粗體
    if not os.path.exists(font_path):
        font_path = "C:\\Windows\\Fonts\\msjh.ttc"
    
    try:
        font = ImageFont.truetype(font_path, 68)
    except Exception:
        font = ImageFont.load_default()
        print("Warning: Microsoft JhengHei font not found. Using default font.")
        
    for card in cards:
        c = card["col"]
        r = card["row"]
        
        # 格子的精確 bounds
        x_start = c * 833
        y_start = r * 843
        x_end = (c + 1) * 833 if c < 2 else 2500
        y_end = (r + 1) * 843 if r < 1 else 1686
        
        # 卡片繪製 bounds
        cx1 = x_start + pad_x
        cy1 = y_start + pad_y
        cx2 = x_end - pad_x
        cy2 = y_end - pad_y
        
        # 繪製毛玻璃卡片背景與外邊框 (半透明)
        draw.rounded_rectangle(
            [cx1, cy1, cx2, cy2],
            radius=corner_radius,
            fill=(255, 255, 255, 14),
            outline=(255, 255, 255, 45),
            width=4
        )
        
        # 卡片中心點
        center_x = (cx1 + cx2) // 2
        
        # 下載並黏貼 Icon
        try:
            print(f"Downloading icon for {card['title']}...")
            res = requests.get(card["icon_url"], timeout=10)
            if res.status_code == 200:
                icon_img = Image.open(BytesIO(res.content)).convert("RGBA")
                icon_w, icon_h = icon_img.size
                icon_x = center_x - icon_w // 2
                icon_y = cy1 + 170
                overlay.paste(icon_img, (icon_x, icon_y), icon_img)
        except Exception as e:
            print(f"Failed to fetch icon for {card['title']}: {e}")
            
        # 繪製繁體中文文字 (置中，卡片下半部)
        text = card["title"]
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        
        text_x = center_x - text_w // 2
        text_y = cy2 - 210
        
        # 陰影
        draw.text((text_x + 3, text_y + 3), text, font=font, fill=(0, 0, 0, 120))
        # 本體
        draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 255))
        
    # 3. 將 overlay 與背景 Alpha 合併
    final_img = Image.alpha_composite(img, overlay)
    
    # 4. 轉為 RGB 儲存
    final_rgb = final_img.convert("RGB")
    
    output_png = r"c:\Users\chiah\Documents\moodle notifier\frontend\public\rich_menu_template.png"
    output_jpg = r"c:\Users\chiah\Documents\moodle notifier\frontend\public\rich_menu_template.jpg"
    
    os.makedirs(os.path.dirname(output_png), exist_ok=True)
    
    final_img.save(output_png, "PNG")
    final_rgb.save(output_jpg, "JPEG", quality=95)
    print("Rich menu image generated successfully!")

if __name__ == "__main__":
    create_rich_menu()
