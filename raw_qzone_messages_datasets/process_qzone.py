"""没写完"""
import json
from collections import Counter, deque
import constants
import loguru
import re

LOGGER = loguru.logger


def extract_replies_with_names(comment_list):
    replies = []
    for comment in comment_list:
        content = comment.get('content', '')
        content = replace_with_emoji(content)
        content = re.sub(r'@\{uin:\d+,nick:([^,]+),[^\}]+\}', r'@\1 ', content)
        create_time = comment.get('createTime', comment.get('createTime2', ''))
        name = comment.get('name', '')
        sub_replies = extract_replies_with_names(comment.get('list_3', []))
        replies.append({
            'content': content,
            'createTime': create_time,
            'name': name,
            'subReplies': sub_replies
        })
    return replies


def extract_data_with_reply_tree(json_content):
    extracted_data = []
    for item in json_content:
        content = item.get('content', '')
        create_time = item.get('createTime', item.get('createTime2', ''))
        name = item.get('name', '')
        replies = extract_replies_with_names(item.get('commentlist', []))
        content = replace_with_emoji(content)
        content = re.sub(r'@\{uin:\d+,nick:([^,]+),[^\}]+\}', r'@\1 ', content)
        extracted_data.append({
            'content': content,
            'createTime': create_time,
            'name': name,
            'replies': replies
        })
    return extracted_data


def replace_with_emoji(text):
    for code, emoji in constants.emoji_mapping.items():
        if code in text:
            LOGGER.info(f"Replacing code {code} with emoji {emoji}")
            text = text.replace(code, emoji)
    li = re.compile(r'\[em\]e\d+\[\/em\]').findall(text)
    if li:
        LOGGER.warning(f"unmapping emoji: {li}")
    text = re.sub(r'\[em\]e\d+\[\/em\]', '', text)
    return text


def process_shuoshuo(shuoshuo_list):
    dataset_entries = []
    skipped_shuoshuos = []

    for shuoshuo in shuoshuo_list:
        content = shuoshuo["content"]
        if len(content) > 40:
            skipped_shuoshuos.append(shuoshuo)
            continue

        for reply in shuoshuo["replies"]:
            entry = {
                "instruction": reply["content"],
                "input": "",
                "output": content,
                "history": []
            }

            # Queue to handle subReplies recursively
            queue = deque([(reply["subReplies"], entry)])
            while queue:
                sub_replies, parent_entry = queue.popleft()
                for sub_reply in sub_replies:
                    child_entry = {
                        "instruction": sub_reply["content"],
                        "input": "",
                        "output": content,
                        "history": [parent_entry["instruction"], content]
                    }
                    dataset_entries.append(child_entry)
                    queue.append((sub_reply["subReplies"], child_entry))

            dataset_entries.append(entry)

    return dataset_entries, skipped_shuoshuos


with open('formatted_messages.json', 'r', encoding='utf-8') as f:
    json_content = json.load(f)
    extracted_data = extract_data_with_reply_tree(json_content)
    with open('data_extracted.json', 'w', encoding='utf-8') as f2:
        json.dump(extracted_data, f2, indent=4, ensure_ascii=False)
    dataset_entries, skipped_shuoshuos = process_shuoshuo(extracted_data)
    with open('dataset_entries.json', 'w', encoding='utf-8') as f3:
        json.dump(dataset_entries, f3, indent=4, ensure_ascii=False)
    with open('skipped_shuoshuos.json', 'w', encoding='utf-8') as f4:
        json.dump(skipped_shuoshuos, f4, indent=4, ensure_ascii=False)
    print(f"Total entries: {len(dataset_entries)}")