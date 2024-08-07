"""处理导出的微信数据(写完了, 但我用不上, 所以没再维护)"""
from collections import defaultdict
from datetime import datetime, timedelta
import json
import re

from constants import noneed, export_contacts, export_chatrooms, export_gzh, privacy_information
import os
import loguru

LOGGER = loguru.logger
new_json = []


def preprocess_json(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        json_content = json.load(f)
    for item in json_content:
        if item["type"] != 1:
            json_content.remove(item)
            continue
        for key in noneed:
            if key in item:
                del item[key]
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_content, f, ensure_ascii=False, indent=4)


def export_contact(messages: list, contact_name: str, path: str):
    njson = []
    for message in messages:
        if message["talker"] == contact_name:
            njson.append(message)

    with open(os.path.join(path, f"{contact_name}.json"), 'w', encoding='utf-8') as f:
        json.dump(njson, f, ensure_ascii=False, indent=4)

    LOGGER.info(f"Exported contact {contact_name} to {path}")
    LOGGER.info(f"Total {len(njson)} messages")


def export_chatroom(messages: list, chatroom_name: str, path: str):
    njson = []
    for message in messages:
        if message["talker"] == chatroom_name:
            njson.append(message)

    njson = preprocess_group_chat_messages(njson)
    with open(os.path.join(path, f"{chatroom_name}.json"), 'w', encoding='utf-8') as f:
        json.dump(njson, f, ensure_ascii=False, indent=4)
    LOGGER.info(f"Exported chatroom {chatroom_name} to {path}")
    LOGGER.info(f"Total {len(njson)} messages")


def _export_gzh(messages: list, gzh_name: str, path: str):
    njson = []
    for message in messages:
        if message["talker"] == gzh_name:
            njson.append(message)

    with open(os.path.join(path, f"{gzh_name}.json"), 'w', encoding='utf-8') as f:
        json.dump(njson, f, ensure_ascii=False, indent=4)

    LOGGER.info(f"Exported gzh {gzh_name} to {path}")
    LOGGER.info(f"Total {len(njson)} messages")


def export_main():
    if not os.path.exists(os.path.join(os.path.dirname(__file__), "exported")):
        os.makedirs(os.path.join(os.path.dirname(__file__), "exported"))
        os.makedirs(os.path.join(os.path.dirname(__file__), "exported", "contacts"))
        os.makedirs(os.path.join(os.path.dirname(__file__), "exported", "chatrooms"))
        os.makedirs(os.path.join(os.path.dirname(__file__), "exported", "gzh"))

    for contact in export_contacts:
        export_contact(new_json, contact, os.path.join(os.path.dirname(__file__), "exported", "contacts"))

    for chatroom in export_chatrooms:
        export_chatroom(new_json, chatroom, os.path.join(os.path.dirname(__file__), "exported", "chatrooms"))

    for gzh in export_gzh:
        _export_gzh(new_json, gzh, os.path.join(os.path.dirname(__file__), "exported", "gzh"))

    LOGGER.info("Exported all contacts, chatrooms and gzh")


def filter_personal_information(records: list):
    """Filter personal information with privacy_information list"""
    filtered_records = []
    for record in records:
        message = record["content"]
        original_message = message[:]
        for keyword in privacy_information:
            if keyword in message:
                LOGGER.info(f"Removing personal information '{keyword}' from message: {original_message}")
                message = message.replace(keyword, "")
        if message.strip():
            record["message"] = message
            filtered_records.append(record)
        else:
            LOGGER.info(f"Removed entire record with personal information in message: {original_message}")
    return filtered_records


def convert_contact_chat_records(chat_records):
    from collections import defaultdict
    from datetime import datetime

    chat_by_date = defaultdict(list)
    chat_records = filter_personal_information(chat_records)
    for record in chat_records:
        date = datetime.fromtimestamp(record['createTime'] // 1000).strftime('%Y-%m-%d')
        chat_by_date[date].append(record)

    result = []
    for date, chats in chat_by_date.items():
        history = []
        instruction = ""
        answer = ""
        processing_instruction = False
        skip_starting_sends = True

        for i in range(len(chats)):
            if skip_starting_sends and chats[i]['isSend'] == 1:
                continue

            skip_starting_sends = False

            if chats[i]['isSend'] == 0:
                processing_instruction = True
                instruction = chats[i]['content']
            else:
                if processing_instruction:
                    answer = chats[i]['content']
                    history.append([instruction, answer])
                    result.append({
                        "instruction": instruction,
                        "input": "",
                        "output": answer,
                        "history": history.copy()
                    })
                    processing_instruction = False

    return result


def convert_group_chat_records(chat_records):
    chat_by_date = defaultdict(list)
    chat_records = filter_personal_information(chat_records)
    for record in chat_records:
        date = datetime.fromtimestamp(record['createTime'] // 1000).strftime('%Y-%m-%d')
        chat_by_date[date].append(record)

    result = []
    for date, chats in chat_by_date.items():
        history = []  # Reset history for each date
        instructions = []
        answers = []
        current_sender = ""
        previous_time = None

        i = 0
        while i < len(chats):
            if chats[i]['isSend'] == 1:
                answers.append(chats[i]['content'])
                while i + 1 < len(chats) and chats[i + 1]['isSend'] == 1:
                    answers[-1] += "\n" + chats[i + 1]['content']
                    i += 1

                instruction = ""
                j = i - 1
                if j >= 0 and chats[j]['isSend'] == 0:
                    current_sender = chats[j]['sender']
                    instruction = chats[j]['content']
                    previous_time = datetime.fromtimestamp(chats[j]['createTime'] // 1000)
                    while j - 1 >= 0 and chats[j - 1]['sender'] == current_sender and \
                            chats[j - 1]['isSend'] == 0 and \
                            datetime.fromtimestamp(chats[j - 1]['createTime'] // 1000) >= previous_time - timedelta(minutes=2):
                        instruction = chats[j - 1]['content'] + "\n" + instruction
                        previous_time = datetime.fromtimestamp(chats[j - 1]['createTime'] // 1000)
                        j -= 1

                instructions.append(instruction)
                current_pair = [instruction, "\n".join(answers)]
                history.append(current_pair)
                result.append({
                    "instruction": instruction,
                    "input": "",
                    "output": "\n".join(answers),
                    "history": history[:-1]
                })

                answers = []
            i += 1

    return result




def convert_main():
    if not os.path.exists(os.path.join(os.path.dirname(__file__), "datasets")):
        os.makedirs(os.path.join(os.path.dirname(__file__), "datasets"))
        os.makedirs(os.path.join(os.path.dirname(__file__), "datasets", "contacts"))
        os.makedirs(os.path.join(os.path.dirname(__file__), "datasets", "chatrooms"))
        os.makedirs(os.path.join(os.path.dirname(__file__), "datasets", "gzh"))

    # for contact in export_contacts:
    #     with open(os.path.join(os.path.dirname(__file__), "exported", "contacts", f"{contact}.json"), 'r',
    #               encoding='utf-8') as f:
    #         contact_json = json.load(f)
    #     contact_json = convert_contact_chat_records(contact_json)
    #     with open(os.path.join(os.path.dirname(__file__), "datasets", "contacts", f"{contact}.json"), 'w',
    #               encoding='utf-8') as f:
    #         json.dump(contact_json, f, ensure_ascii=False, indent=4)

    for chatroom in export_chatrooms:
        with open(os.path.join(os.path.dirname(__file__), "exported", "chatrooms", f"{chatroom}.json"), 'r',
                  encoding='utf-8') as f:
            chatroom_json = json.load(f)
        chatroom_json = convert_group_chat_records(chatroom_json)
        with open(os.path.join(os.path.dirname(__file__), "datasets", "chatrooms", f"{chatroom}.json"), 'w',
                  encoding='utf-8') as f:
            json.dump(chatroom_json, f, ensure_ascii=False, indent=4)


def preprocess_group_chat_messages(messages):
    processed_messages = []
    for message in messages:
        content = message["content"]
        sender = ""
        if message["isSend"] == 0:
            # 提取并删除发送者标识
            match = re.match(r'(.*?):\n', content)
            if match:
                sender = match.group(1)
                content = content.replace(f"{sender}:\n", "", 1)

        processed_message = message.copy()
        processed_message["content"] = content
        processed_message["sender"] = sender
        processed_messages.append(processed_message)

    return processed_messages


if "__main__" == __name__:
    # with open("message_new.json", 'r', encoding='utf-8') as f:
    #     new_json = json.load(f)
    # export_main()
    # LOGGER.info("Done")
    convert_main()
