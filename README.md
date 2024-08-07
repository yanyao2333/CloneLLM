# Clone-LLM 数据集

## QQ
1. 从QQ导出txt格式聊天记录(最新nt版本qq好像不支持这样导出了, 反正我没找到)
2. 运行 `preprocess_raw_qq_msg.py`,会将聊天记录转换为json保存到 `./json_msg` 文件夹内
3. 编辑 `constants.py`, 照着注释写就好
4. 运行 `convert_to_dataset_v4.py`, 完成后会保存在 `./datasets` 文件夹内

## QZone
还没写好

## Wechat
最开始我也加入了微信聊天记录作为数据集, 但发现太乱, 还有各种处理不清的回复消息(实际上是可以处理的, 但太麻烦), 总之最后数据集质量不太好, 就去掉了.

如果你想尝试一下的话(不保证成功):
1. 导出微信数据库并解密, 保存 `message, rcontact, chatroom` 表为csv格式
2. 运行 `聊天记录按好友导出csv.py` (这玩意不能直接跑, 先打开修改一些路径吧, 我也不确定哪些需要修改)
3. 运行 `process_wechat.py` (也不能直接跑, 但函数封装的应该都是没问题的, 自己看看先跑哪个后跑哪个吧)