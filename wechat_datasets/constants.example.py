# 数据库导出表中的很多字段我们都不需要, 先处理一波, 可以大幅减小json文件体积
noneed = ["lvbuffer", "historyId", "solitaireFoldInfo", "flag", "msgSeq", "bizChatUserId", "bizChatId", "bizClientMsgId", "transBrandWording", "transContent", "status", "imgPath", "reserved", "isShowTimer", "msgSvrId"]

# 下面的export_xxx都要填其在数据库中对应的id
export_contacts = []

export_chatrooms = []

export_gzh = [] # 公众号，单独处理

privacy_information = []