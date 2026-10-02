# Unicode escapes preserve the original multilingual parser vocabulary.
# This source representation does not translate the accepted input values.
import re

def detect_language(text: str) -> str:
    if not text:
        return "unknown"
    cjk = len(re.findall('[\u4e00-\u9fff\u3400-\u4dbf]', text))
    total = len(text.strip())
    if total == 0:
        return "unknown"
    if cjk / total > 0.15:
        return "zh"
    return "en"

def is_chinese(text: str) -> bool:
    return detect_language(text) == "zh"
