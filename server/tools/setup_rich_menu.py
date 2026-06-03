import os
import sys
import requests
from pathlib import Path

# Add project root to sys.path so we can import Config
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from src.config import Config

def setup_rich_menu(dashboard_url: str):
    print("Loading config...")
    try:
        config = Config.load()
    except Exception as e:
        print(f"Error loading config: {e}")
        return

    if not config.line_token:
        print("Error: LINE_TOKEN is not configured in environment or local files.")
        return

    token = config.line_token
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 1. Clean up old rich menus to avoid hitting limits
    print("Listing existing rich menus...")
    list_url = "https://api.line.me/v2/bot/richmenu/list"
    try:
        r = requests.get(list_url, headers=headers)
        if r.status_code == 200:
            menus = r.json().get("richmenus", [])
            print(f"Found {len(menus)} existing rich menus.")
            for menu in menus:
                menu_id = menu.get("richMenuId")
                print(f"Deleting rich menu {menu_id}...")
                requests.delete(f"https://api.line.me/v2/bot/richmenu/{menu_id}", headers=headers)
        else:
            print(f"Failed to list rich menus: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Exception listing/deleting rich menus: {e}")

    # 2. Create rich menu
    print("Creating new rich menu...")
    create_url = "https://api.line.me/v2/bot/richmenu"
    menu_data = {
        "size": {
            "width": 2500,
            "height": 1686
        },
        "selected": True,
        "name": "Moodle Notifier Menu",
        "chatBarText": "選單 Menu",
        "areas": [
            {
                "bounds": {"x": 0, "y": 0, "width": 833, "height": 843},
                "action": {"type": "message", "text": "/courses"}
            },
            {
                "bounds": {"x": 833, "y": 0, "width": 833, "height": 843},
                "action": {"type": "message", "text": "/assignments"}
            },
            {
                "bounds": {"x": 1666, "y": 0, "width": 834, "height": 843},
                "action": {"type": "message", "text": "/grades"}
            },
            {
                "bounds": {"x": 0, "y": 843, "width": 833, "height": 843},
                "action": {"type": "message", "text": "/upcoming"}
            },
            {
                "bounds": {"x": 833, "y": 843, "width": 833, "height": 843},
                "action": {"type": "message", "text": "/messages"}
            },
            {
                "bounds": {"x": 1666, "y": 843, "width": 834, "height": 843},
                "action": {"type": "uri", "uri": dashboard_url}
            }
        ]
    }

    try:
        r = requests.post(create_url, headers=headers, json=menu_data)
        if r.status_code != 200:
            print(f"Failed to create rich menu: {r.status_code} - {r.text}")
            return
        rich_menu_id = r.json().get("richMenuId")
        print(f"Rich menu created successfully with ID: {rich_menu_id}")
    except Exception as e:
        print(f"Exception creating rich menu: {e}")
        return

    # 3. Upload image
    jpg_path = project_root / "frontend" / "public" / "rich_menu_template.jpg"
    png_path = project_root / "frontend" / "public" / "rich_menu_template.png"
    
    if jpg_path.exists():
        image_path = jpg_path
        content_type = "image/jpeg"
    elif png_path.exists():
        image_path = png_path
        content_type = "image/png"
    else:
        print(f"Error: Rich menu image template not found at {png_path} or {jpg_path}")
        return

    print(f"Uploading image from {image_path} ({content_type})...")
    upload_url = f"https://api-data.line.me/v2/bot/richmenu/{rich_menu_id}/content"
    upload_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": content_type
    }
    try:
        with open(image_path, "rb") as f:
            r = requests.post(upload_url, headers=upload_headers, data=f)
        if r.status_code != 200:
            print(f"Failed to upload rich menu image: {r.status_code} - {r.text}")
            return
        print("Rich menu image uploaded successfully.")
    except Exception as e:
        print(f"Exception uploading rich menu image: {e}")
        return

    # 4. Set as default rich menu
    print("Setting rich menu as default...")
    default_url = f"https://api.line.me/v2/bot/user/all/richmenu/{rich_menu_id}"
    try:
        r = requests.post(default_url, headers={"Authorization": f"Bearer {token}"})
        if r.status_code != 200:
            print(f"Failed to set default rich menu: {r.status_code} - {r.text}")
            return
        print("Rich menu set as default successfully! Setup complete.")
    except Exception as e:
        print(f"Exception setting default rich menu: {e}")

if __name__ == "__main__":
    try:
        config = Config.load()
        default_url = config.dashboard_url or "http://localhost:8000"
    except Exception:
        default_url = "http://localhost:8000"
        
    url = default_url
    for arg in sys.argv:
        if arg.startswith("--url="):
            url = arg.split("=", 1)[1]
    
    print(f"Using dashboard URL: {url}")
    setup_rich_menu(url)
