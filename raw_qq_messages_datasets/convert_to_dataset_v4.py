import json
import constants
import loguru
import os
from collections import defaultdict
from datetime import datetime

LOGGER = loguru.logger


def filter_chat_records(records: list) -> list:
    """依据设置的qq_msg_ignore_list privacy_information清洗聊天数据"""
    filtered_records = []
    for record in records:
        message: str = record["message"]
        for keyword in (constants.qq_msg_ignore_list + constants.privacy_information):
            if keyword in message:
                LOGGER.info(f"Removing keyword '{keyword}' from message: " + record["message"])
                message = message.replace(keyword, "")

        if message.strip():
            record["message"] = message
            filtered_records.append(record)
        else:
            # 如果处理后字符串为空, 就直接忽略这条记录
            LOGGER.info(f"Removed entire record with message: " + record["message"])
    return filtered_records


def filter_system_message(records: list):
    """删除撤回通知"""
    filtered_records = []
    for record in records:
        if record["username"] == "系统消息(10000)":
            # 我不太理解当时写这一段有啥意义, 好像是为了针对自己撤回内容和对方撤回内容填充不同的message内容, 但我觉得没必要
            # if constants.default_username not in record["message"] and not any([username in record["message"] for username in constants.other_username]):
            #     LOGGER.info(f"Removing system message: {record}")
            #     record["message"] = "我撤回了一条消息"
            #     filtered_records.append(record)
            # else:
            #     LOGGER.info(f"Removing system message: {record}")
            #     record["message"] = "咱撤回了一条消息"
            #     filtered_records.append(record)
            LOGGER.info(f"Removing system message: {record}")
            record["message"] = "我撤回了一条消息"

        filtered_records.append(record)
    return filtered_records


def replace_content(records: list):
    """依据replace_list对聊天记录中的内容进行替换"""
    filtered_records = []
    for record in records:
        message = record["message"]
        original_message = message[:]
        for keyword in constants.replace_dict:
            if keyword in message:
                LOGGER.info(
                    f"Replace content '{keyword}' from message: {original_message}, now content is {constants.replace_dict[keyword]}")
                message = message.replace(keyword, constants.replace_dict[keyword])
        if message.strip():
            record["message"] = message
            filtered_records.append(record)
        else:
            LOGGER.info(f"Removed entire record with url in message: {original_message}")
    return filtered_records


def replace_username(records: list):
    """Replace username with default_username"""
    filtered_records = []
    for record in records:
        username = record["username"]
        if username in constants.other_username:
            LOGGER.info(f"Replace username '{username}' to '{constants.default_username}'")
            username = constants.default_username
        record["username"] = username
        filtered_records.append(record)
    return filtered_records


def group_chat_records_by_date(records: list) -> list[list]:
    """将聊天记录按日期分组并排序"""
    records_by_date = defaultdict(list)

    for record in records:
        # 将聊天记录按天分组(这种分组方式有待考量)
        time_str = record["time"]
        # date_str = time_str.split(' ')[0]
        time_obj = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        records_by_date[time_obj.strftime("%Y-%m-%d")].append((time_obj, record))

    sorted_records_by_date = []
    for date, records in records_by_date.items():
        sorted_records = [record for _, record in sorted(records, key=lambda x: x[0])]
        sorted_records_by_date.append(sorted_records)

    return sorted_records_by_date


def format_message(message):
    """或许可以做些处理, 删除标点什么的"""
    # if not message[-1] in ".!?。！？":
    #     return message + "。"
    return message

def convert_to_dataset(chat_groups, my_username, their_username):
    """转换成alpaca格式数据集"""
    dataset = []
    for chat_group in chat_groups:
        history = []
        instruction_buffer = ""
        output_buffer = ""
        temp_dataset = []
        for record in chat_group:
            username = record['username']
            message = format_message(record['message'])
            if username == their_username:
                if instruction_buffer:
                    instruction_buffer += r" \n " + message
                else:
                    instruction_buffer = message
            elif username == my_username:
                if output_buffer:
                    output_buffer += r" \n " + message
                else:
                    output_buffer = message
                if instruction_buffer:
                    temp_dataset.append({
                        "instruction": instruction_buffer,
                        "input": "",
                        "output": output_buffer,
                        "history": history.copy()
                    })
                    history.append([instruction_buffer, output_buffer])
                    instruction_buffer = ""
                    output_buffer = ""

        if temp_dataset:
            dataset.append(temp_dataset[-1])
    return dataset



def process_one_json(file_path, output_path, their_username: str = None, use_username: bool = True):
    """处理一个文件, 生成数据集"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if use_username:
        # 获取好友名字
        their_username = data[0]["username"]
    records = data[0]["history"]
    records = filter_chat_records(records)
    records = filter_system_message(records)
    records = replace_content(records)
    records = replace_username(records)
    chat_groups = group_chat_records_by_date(records)
    dataset = convert_to_dataset(chat_groups, constants.default_username, their_username)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=4)

def main():
    """入口函数"""
    input_dir = os.path.join(os.path.dirname(__file__), "json_msg")
    output_dir = os.path.join(os.path.dirname(__file__), "t_datasets")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    for file_name in os.listdir(input_dir):
        file_path = os.path.join(input_dir, file_name)
        output_path = os.path.join(output_dir, file_name.split(".")[0] + "_final.json")
        LOGGER.info(f"Start process {file_path}, output to {output_path}")
        process_one_json(file_path, output_path)


def merge_datasets(directory_path):
    """把处理完的所有聊天记录数据集合并"""
    merged_dataset = []
    for root, dirs, files in os.walk(directory_path):
        for file_name in files:
            if file_name.endswith('.json'):
                file_path = os.path.join(root, file_name)
                with open(file_path, 'r', encoding="utf-8") as file:
                    dataset = json.load(file)
                    merged_dataset.extend(dataset)
    return merged_dataset


if __name__ == "__main__":
    main()
    # dataset = merge_datasets(os.path.join(os.path.dirname(__file__), "datasets"))
    # with open(os.path.join(os.path.dirname(__file__), "qq_dataset.json"), "w", encoding="utf-8") as f:
    #     json.dump(dataset, f, ensure_ascii=False, indent=4)
    # LOGGER.info(f"Total {len(dataset)} records")
