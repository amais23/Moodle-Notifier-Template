from typing import List, Dict, Any, Tuple

class DiffEngine:
    """資料差異比對引擎，用於各監控器比對新舊資料狀態"""
    
    @staticmethod
    def detect_new(old_items: List[Dict[str, Any]], new_items: List[Dict[str, Any]], key_field: str) -> List[Dict[str, Any]]:
        """偵測新增的項目（新有、舊無）"""
        old_keys = {item.get(key_field) for item in old_items if item.get(key_field) is not None}
        return [item for item in new_items if item.get(key_field) not in old_keys]

    @staticmethod
    def detect_modified(
        old_items: List[Dict[str, Any]], 
        new_items: List[Dict[str, Any]], 
        key_field: str, 
        compare_fields: List[str]
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        偵測修改過的項目（新舊皆有，但指定欄位內容不同）
        回傳 List[Tuple[old_item, new_item]]
        """
        old_dict = {item.get(key_field): item for item in old_items if item.get(key_field) is not None}
        modified = []
        
        for new_item in new_items:
            key = new_item.get(key_field)
            if key in old_dict:
                old_item = old_dict[key]
                # 比對指定欄位是否不同
                is_changed = False
                for field in compare_fields:
                    if old_item.get(field) != new_item.get(field):
                        is_changed = True
                        break
                if is_changed:
                    modified.append((old_item, new_item))
                    
        return modified

    @staticmethod
    def detect_removed(old_items: List[Dict[str, Any]], new_items: List[Dict[str, Any]], key_field: str) -> List[Dict[str, Any]]:
        """偵測已移除的項目（舊有、新無）"""
        new_keys = {item.get(key_field) for item in new_items if item.get(key_field) is not None}
        return [item for item in old_items if item.get(key_field) not in new_keys]
