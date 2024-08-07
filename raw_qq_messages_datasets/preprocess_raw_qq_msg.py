"""用于将导出的.txt聊天记录转换为json格式"""
import json
import re
import os


def extract_history(lines):
    history = []
    pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (.+)')
    i = 0
    while i < len(lines):
        line = lines[i]
        match = pattern.match(line)
        if match:
            time = match.group(1)
            username = match.group(2)
            message = ""
            i += 1
            while i < len(lines) and lines[i].strip() and not pattern.match(lines[i]):
                message += lines[i] + "\n"
                i += 1
            history_entry = {
                "username": username,
                "time": time,
                "message": message.strip()
            }
            history.append(history_entry)
        else:
            i += 1
    return history


def build_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    parsed_data = []
    group = None
    username = None
    history_lines = []
    for line in lines:
        if "消息分组:" in line:
            group = line.split("消息分组:")[1].strip()
        elif "消息对象:" in line:
            if history_lines:
                parsed_data.append({
                    "group": group,
                    "username": username,
                    "history": extract_history(history_lines)
                })
                history_lines = []
            username = line.split("消息对象:")[1].strip()
        elif line.strip() and group and username:
            history_lines.append(line)

    if history_lines:
        parsed_data.append({
            "group": group,
            "username": username,
            "history": extract_history(history_lines)
        })

    return parsed_data



if __name__ == "__main__":
    if not os.path.exists(os.path.join(os.path.dirname(__file__), "json_msg")):
        os.makedirs(os.path.join(os.path.dirname(__file__), "json_msg"))
    for file_name in os.listdir(os.path.join(os.path.dirname(__file__), "json_msg")):
        file_path = os.path.join(os.path.dirname(__file__), "json_msg", file_name)
        json_data = build_json(file_path)
        output_path = os.path.join(os.path.dirname(__file__), "json_msg", file_name.replace(".txt", ".json"))
        with open(output_path, 'w', encoding='utf-8') as file:
            json.dump(json_data, file, ensure_ascii=False, indent=4)