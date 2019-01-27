# coding:utf-8
import sys
import itchat
import re
import requests
import json

from configparser import ConfigParser
from itchat.content import *
from prettytable import PrettyTable
from threading import Thread

from time import sleep, strftime, localtime, time
from os import system

#全局变量定义
g_isLogin = False   #是否登陆：False:未登录  True:已登录
g_isDone = False    #子进程完成标记，用于打点计时
g_loginName = ""
g_autoAddFriend = False   #自动添加好友标记
g_autoReplyFriend = False  #自动回复好友私聊标记
g_autoReplyGroup = False   #自动回复群聊@消息标记
g_checkIfCallback = False   #检测撤回消息标记

g_tulingAPIKey = ""				#图灵APIKey
g_autoReplyFriendBytuling = False  #图灵代答私聊消息
g_autoReplygroupBytuling = False    #图灵代答群聊@消息
g_isTulingReady = False             #图灵是否准备OK标记

g_cfg_r = ConfigParser()          #配置读取
g_cfg_w = ConfigParser()          #配置保存
msg_information = {}              #私聊消息字典

#@click.command()
#@click.option('-c',required=True,type=click.Choice(['1','2']))   # 限定-c的值为start，或者stop，required表示是否为必填参数

def logging(str):
    Time = strftime('%Y-%m-%d %H:%M:%S : ',localtime(time()))
    print("[LOGGING] " + Time + str, flush=True)


@itchat.msg_register([FRIENDS])
def add_friend(msg):
    #print(msg, flush=True)
    global g_autoAddFriend
    if g_autoAddFriend == True:
        itchat.add_friend(**msg['Text'])
        itchat.send_msg('你好！很高兴认识你！', msg['RecommendInfo']['UserName'])
        logging("收到[%s]添加好友请求，已经自动通过！" %msg['RecommendInfo']['NickName'])

@itchat.msg_register([TEXT, RECORDING, PICTURE], isFriendChat=True)
def reply_friend(msg):
    #print(msg, flush=True)
    global g_autoReplyFriend, g_autoReplyFriendBytuling, g_isTulingReady

    if msg['Type'] == "Text":
        msg_content = msg['Text']
    elif msg['Type'] == "Recording" or msg['Type'] == "Picture":
        msg_content = msg['FileName']
        msg['Text'](str(msg_content))    #下载文件
        
    ##将信息存储在字典中，每一个msg_id对应一条信息
    msg_information.update(
    {
        msg['MsgId']: {
            "msg_type": msg["Type"],
            "msg_content": msg_content,
            }
        }
    )

    if g_autoReplyFriend == True:
        itchat.send_msg('[自动回复]: 你的消息已收到！', toUserName = msg['FromUserName'])
        logging("收到[%s]的[%s]消息[%s]，已经自动回复！" %(msg['User']['NickName'], msg['Type'], msg_content))

    if g_autoReplyFriendBytuling == True and g_isTulingReady == True:
        if msg['Type'] == "Text":
            msg_response = tuling_getResponse(tuling_makeJson(msg_content))
            msg_response = "[机器人回复] " + msg_response
            itchat.send_msg(msg_response, toUserName = msg['FromUserName'])
            logging("收到[%s]的消息[%s]，图灵机器人已经帮你回复[%s]！" %(msg['User']['NickName'], msg_content, msg_response))


@itchat.msg_register([NOTE], isFriendChat=True)
def check_callback(msg):
    global g_checkIfCallback
    if g_checkIfCallback == True:
        if '撤回了一条消息' in msg['Content']:
            old_msg_id = re.search("\<msgid\>(.*?)\<\/msgid\>", msg['Content']).group(1)   #在返回的content查找撤回的消息的id
            old_msg = msg_information.get(old_msg_id)    #得到消息
            
            old_msg_type = old_msg["msg_type"]
            old_msg_content =  old_msg['msg_content']
            
            if old_msg_type == "Text":
                msg_body = '%s，内容是[%s]' %(msg['Text'], old_msg_content)
                itchat.send_msg(msg_body, toUserName='filehelper')
                logging(" %s，消息格式是文本格式，内容是[%s]" %(msg['Text'], old_msg_content))
            elif old_msg_type == "Recording" or old_msg_type == "Picture":
                msg_body = '%s，内容是下面这个文件' %(msg['Text'])
                itchat.send_msg(msg_body, toUserName='filehelper')
                file = '@fil@%s' % (old_msg_content)
                itchat.send(msg=file, toUserName='filehelper')
                logging(" %s，消息格式是图片或录音，内容已发送至文件传输助手！" %(msg['Text']))
                
            # 删除旧消息
            msg_information.pop(old_msg_id)
        

@itchat.msg_register(TEXT, isGroupChat=True)
def reply_group(msg):
    #print(msg, flush=True)
    global g_autoReplyGroup
    if g_autoReplyGroup == True:
        if (msg.isAt):
            msg_content = msg['Content'].split("\u2005", 1)[1]
            itchat.send_msg('[自动回复]: 你的消息已收到！', toUserName = msg['FromUserName'])
            logging("收到群[%s]@你的消息[%s]，已经自动回复！" %(msg['User']['NickName'], msg_content))

    if g_autoReplygroupBytuling == True and g_isTulingReady == True and msg.isAt:
        if msg['Type'] == "Text":
            msg_content = msg['Content'].split("\u2005", 1)[1]
            msg_response = tuling_getResponse(tuling_makeJson(msg_content))
            msg_response = "[机器人回复] " + msg_response
            #print(msg_response)
            itchat.send_msg(msg_response, toUserName = msg['FromUserName'])
            logging("收到群[%s]@你的消息[%s]，图灵机器人已经帮你自动回复！" %(msg['User']['NickName'], msg_content))


def tuling_makeJson(data):
    global g_tulingAPIKey
    str = {
        "reqType":0,
        "perception": {
            "inputText": {
                "text": data
            }
        },
        "userInfo": {
            "apiKey": g_tulingAPIKey,
            "userId": "test"
        }
    }
    return json.dumps(str)

def tuling_getResponse(data):
    url = 'http://openapi.tuling123.com/openapi/api/v2'
    response = requests.post(url=url, data=data, headers={'Content-Type':'application/json'}, timeout=2)
    if response.status_code != 200:
        print("网络连接失败，请检查网络！")
        return ""
    r_dict = response.json()
        
    print(r_dict["results"][0])

    return  r_dict["results"][0]["values"]["text"]


def tuling_checkReady():
    global g_isDone, g_isTulingReady
    g_isDone = False

    data = tuling_makeJson("hello")
    url = 'http://openapi.tuling123.com/openapi/api/v2'
    response = requests.post(url=url, data=data, headers={'Content-Type':'application/json'})
    if response.status_code != 200:
        print("网络连接失败，请检查网络！")
        g_isDone = True
        return

    r_dict = response.json()

    if r_dict["intent"]["code"] == "4007":
        print("apiKey格式不合法！请输入正确的apiKey！")
        g_isDone = True
        return

    print("图灵机器人链接成功！")
    g_isDone = True
    g_isTulingReady = True


def save_config():
    global g_cfg_w, g_autoAddFriend, g_autoReplyFriend, g_autoReplyGroup, g_checkIfCallback, g_isDone
    global g_autoReplyFriendBytuling, g_autoReplygroupBytuling, g_tulingAPIKey

    g_isDone = False

    g_cfg_w.add_section("friends")
    g_cfg_w.set("friends", "auto_add_friend", str(g_autoAddFriend))
    g_cfg_w.set("friends", "auto_reply_friend", str(g_autoReplyFriend))
    g_cfg_w.set("friends", "auto_check_callback ", str(g_checkIfCallback))

    g_cfg_w.add_section("chatrooms")
    g_cfg_w.set("chatrooms", "auto_reply_group ", str(g_autoReplyGroup))

    g_cfg_w.add_section("tuling")
    g_cfg_w.set("tuling", "api_key ", g_tulingAPIKey)
    g_cfg_w.set("tuling", "auto_reply_friend_tuling ", str(g_autoReplyFriendBytuling))
    g_cfg_w.set("tuling", "auto_reply_group_tuling ", str(g_autoReplygroupBytuling))


    # 写存储文件
    with open("cfg.ini","w+") as f:
        g_cfg_w.write(f)
        
    print("配置保存成功，已写入[cfg.ini]文件中！")

    g_isDone = True


def read_config():
    global g_cfg_r, g_autoAddFriend, g_autoReplyFriend, g_autoReplyGroup, g_checkIfCallback, g_isDone
    global g_autoReplyFriendBytuling, g_autoReplygroupBytuling, g_tulingAPIKey

    g_isDone = False

    g_cfg_r.read("cfg.ini")

    g_autoAddFriend = g_cfg_r.getboolean("friends", "auto_add_friend")
    g_autoReplyFriend = g_cfg_r.getboolean("friends", "auto_reply_friend")
    g_checkIfCallback = g_cfg_r.getboolean("friends", "auto_check_callback")

    g_autoReplyGroup = g_cfg_r.getboolean("chatrooms", "auto_reply_group")

    g_tulingAPIKey = g_cfg_r.get("tuling", "api_key")
    g_autoReplyFriendBytuling = g_cfg_r.getboolean("tuling", "auto_reply_friend_tuling")
    g_autoReplygroupBytuling = g_cfg_r.getboolean("tuling", "auto_reply_group_tuling")

    tuling_checkReady()

    print("配置读取成功，已成功应用！")

    g_isDone = True


def getSelfInfo():
    global g_loginName
    friends = itchat.get_friends(update=True)[0:]
    g_loginName = friends[0]["NickName"]


def getFriends():
    global g_isDone
    g_isDone = False
    total = 0
    table = PrettyTable(["序号", "昵称", "备注", "性别", "地区"])

    friends = itchat.get_friends(update=True)[0:]
    for index, i in enumerate(friends[1:]):
        total += 1
        
        if i["Sex"] == 1:
            sex = "男生"
        elif i["Sex"] == 2:
            sex = "女生"
        else:
            sex = "未知"
        table.add_row([index, i['NickName'], i['RemarkName'], sex, i['Province']+i['City']])

    print("分析完成：")
    print(table)
    print("全部好友合计 %d" %total)
    g_isDone = True
    return

def getChatrooms():
    global g_isDone
    g_isDone = False
    total = 0

    table = PrettyTable(["序号", "群昵称", "你的昵称", "成员数量", "是否群主"])

    rooms = itchat.get_chatrooms(update=True)[0:]
    for index, i in enumerate(rooms):
        total += 1
        if i['IsOwner'] == 1:
            Owner = '是'
        else:
            Owner = '否'
            
        table.add_row([index, i['NickName'], i['Self']['NickName'], i['MemberCount'], Owner])

    print("分析完成：")
    print(table)
    print("全部群组合计 %d" %total)

    g_isDone = True
    return


def Screen_Clear():
    system('cls')


def Choose_LoginMenu():
    print("请选择：",end="")
    #click.echo('command is %s' %c)
    c=input()
    if c == '1':
        Login_Start(1)
        return
    if c == '2':
        Login_Start(2)
        return
    if c == '0':
        print("已退出程序！")
        exit()
    else:
        print("输入错误请重新输入!")
        Choose_LoginMenu()

def Print_LoginMenu():
    print("\n\n============================================")
    print("\t\t1: 扫码登陆(windows)")
    print("\t\t2: 扫码登陆(linux)")
    print("\t\t0: 退出程序")
    print("============================================")


def getSexRate():
    global g_isDone
    g_isDone = False
        
    M = F = other = total = 0
    friends = itchat.get_friends(update=True)[0:]
    #print(friends)
    for i in friends[1:]:
        total += 1
        sex = i["Sex"]
        if sex == 1:
            M += 1
        elif sex == 2:
            F += 1
        else:
            other += 1

    table = PrettyTable(["序号", "性别", "总数", "比例(%)"])
    table.add_row(['0', '男生', M, round(((float(M)/total*100)),2)])
    table.add_row(['1', '女生', F, round(((float(F)/total*100)),2)])
    table.add_row(['2', '其他', other, round(((float(other)/total*100)),2)])

    print("分析完成：")
    print(table)
    print("全部好友合计 %d" %total)

    g_isDone = True
    return


def getAreaRate():
    global g_isDone
    g_isDone = False

    total = 0
    area_list = []
    area_dict = {}
    friends = itchat.get_friends(update=True)[0:]  #获取所有好友
    for i in friends[1:]:   #第一个是自己，从第二个开始分析
        total += 1
        area_list.append(i["Province"]+i["City"])

    for i in area_list:                 #计数字典
        if area_dict.get(i) == None:
            area_dict[i] = 1
        else:
            area_dict[i] = area_dict.get(i)+1

    sorted_area_dict = sorted(area_dict.items(), key=lambda d:d[1], reverse = True) #排序

    table = PrettyTable(["序号", "城市", "总数", "比例(%)"])

    for index, j in enumerate(sorted_area_dict):
        if j[0] == '':
            table.add_row([index, "未知区域", j[1], round((float(j[1])/total*100),2)])
        else:
            table.add_row([index, j[0], j[1], round((float(j[1])/total*100),2)])
    print("分析完成：")
    print (table)
    print("全部好友合计 %d" %total)

    g_isDone = True
    return


def Choose_MainMenu():
    global g_isDone, g_autoAddFriend, g_autoReplyFriend, g_autoReplyGroup, g_checkIfCallback
    global g_autoReplyFriendBytuling, g_autoReplygroupBytuling, g_isTulingReady, g_tulingAPIKey
    print("请选择：",end="")
    c=input()
    #print(c)
    if c == '1.1':
        print("正在分析，请稍等",end="")
        Thread(target = getSexRate).start()
        while(True):
            if g_isDone == False:
                print(".",end="",flush=True)
                sleep(0.2)
            else:
                break
        
        return
    if c == '1.2':
        print("正在分析，请稍等",end="")
        Thread(target = getAreaRate).start()
        while(True):
            if g_isDone == False:
                print(".",end="",flush=True)
                sleep(0.2)
            else:
                break
        return

    if c == '1.3':
        print("正在分析，请稍等",end="")
        Thread(target = getFriends).start()
        while(True):
            if g_isDone == False:
                print(".",end="",flush=True)
                sleep(0.2)
            else:
                break
        return
        
    if c == '1.4':
        while(True):
            if g_autoAddFriend == True:
                print("自动添加好友当前已开启，是否关闭？(y/n): ", end="")
                c = input()
                if c == 'Y' or c == 'y':
                    g_autoAddFriend = False
                    print("自动添加好友已关闭！")
                    break
                elif c == 'N' or c == 'n':
                    break
                else:
                    print("输入错误请重新输入！")
            else:
                print("自动添加好友当前已关闭，是否开启？(y/n): ", end="")
                c = input()
                if c == 'Y' or c == 'y':
                    g_autoAddFriend = True
                    print("自动添加好友已开启！")
                    break
                elif c == 'N' or c == 'n':
                    break
                else:
                    print("输入错误请重新输入！")

        return

    if c == '2.1':
        print("正在分析，请稍等",end="")
        Thread(target = getChatrooms).start()
        while(True):
            if g_isDone == False:
                print(".",end="",flush=True)
                sleep(0.2)
            else:
                break
        
        return
        

    if c == '2.2':
        while(True):
            if g_autoReplyGroup == True:
                print("自动回复群@消息当前已开启，是否关闭？(y/n): ", end="")
                c = input()
                if c == 'Y' or c == 'y':
                    g_autoReplyGroup = False
                    print("自动回复群@消息已关闭！")
                    break
                elif c == 'N' or c == 'n':
                    break
                else:
                    print("输入错误请重新输入！")
            else:
                print("自动回复群@消息当前已关闭，是否开启？(y/n): ", end="")
                c = input()
                if c == 'Y' or c == 'y':
                    g_autoReplyGroup = True
                    print("自动回复群@消息已开启！")
                    break
                elif c == 'N' or c == 'n':
                    break
                else:
                    print("输入错误请重新输入！")

        return
        
    if c == '3.1':
        while(True):
            if g_autoReplyFriend == True:
                print("自动回复私聊消息当前已开启，是否关闭？(y/n): ", end="")
                c = input()
                if c == 'Y' or c == 'y':
                    g_autoReplyFriend = False
                    print("自动回复私聊消息已关闭！")
                    break
                elif c == 'N' or c == 'n':
                    break
                else:
                    print("输入错误请重新输入！")
            else:
                print("自动回复私聊消息当前已关闭，是否开启？(y/n): ", end="")
                c = input()
                if c == 'Y' or c == 'y':
                    g_autoReplyFriend = True
                    print("自动回复私聊消息已开启！")
                    break
                elif c == 'N' or c == 'n':
                    break
                else:
                    print("输入错误请重新输入！")

        return

    if c == '3.2':
        print("请注意：自动监控撤回消息开启后，会自动下载语音和图片附件。")
        while(True):
            if g_checkIfCallback == True:
                print("自动监控撤回消息当前已开启，是否关闭？(y/n): ", end="")
                c = input()
                if c == 'Y' or c == 'y':
                    g_checkIfCallback = False
                    print("自动监控撤回消息已关闭！")
                    break
                elif c == 'N' or c == 'n':
                    break
                else:
                    print("输入错误请重新输入！")
            else:
                print("自动监控撤回消息当前已关闭，是否开启？(y/n): ", end="")
                c = input()
                if c == 'Y' or c == 'y':
                    g_checkIfCallback = True
                    print("自动监控撤回消息已开启！")
                    break
                elif c == 'N' or c == 'n':
                    break
                else:
                    print("输入错误请重新输入！")

        return
        
    if c == '4.1':
        while(True):
            print("请输入您申请到的图灵机器人APIKey：",end="")
            g_tulingAPIKey = input()
            print("正在测试连接，请稍等",end="")
            Thread(target = tuling_checkReady).start()
            while(True):
                if g_isDone == False:
                    print(".",end="",flush=True)
                    sleep(0.2)
                else: 
                    break
        
            return
            
        
        return

    if c == '4.2':
        if g_isTulingReady == False:
            print("图灵机器人连接失败，请先检查配置！")
            return
        while(True):
            if g_autoReplyFriendBytuling == True:
                print("图灵机器人代答私聊消息当前已开启，是否关闭？(y/n): ", end="")
                c = input()
                if c == 'Y' or c == 'y':
                    g_autoReplyFriendBytuling = False
                    print("图灵机器人代答私聊消息已关闭！")
                    break
                elif c == 'N' or c == 'n':
                    break
                else:
                    print("输入错误请重新输入！")
            else:
                print("图灵机器人代答私聊消息已关闭，是否开启？(y/n): ", end="")
                c = input()
                if c == 'Y' or c == 'y':
                    g_autoReplyFriendBytuling = True
                    print("图灵机器人代答私聊消息已开启！")
                    break
                elif c == 'N' or c == 'n':
                    break
                else:
                    print("输入错误请重新输入！")

        return

    if c == '4.3':
        if g_isTulingReady == False:
            print("图灵机器人连接失败，请先检查配置！")
            return
        while(True):
            if g_autoReplygroupBytuling == True:
                print("图灵机器人代答群聊@消息当前已开启，是否关闭？(y/n): ", end="")
                c = input()
                if c == 'Y' or c == 'y':
                    g_autoReplygroupBytuling = False
                    print("图灵机器人代答群聊@消息已关闭！")
                    break
                elif c == 'N' or c == 'n':
                    break
                else:
                    print("输入错误请重新输入！")
            else:
                print("图灵机器人代答群聊@消息已关闭，是否开启？(y/n): ", end="")
                c = input()
                if c == 'Y' or c == 'y':
                    g_autoReplygroupBytuling = True
                    print("图灵机器人代答群聊@消息已开启！")
                    break
                elif c == 'N' or c == 'n':
                    break
                else:
                    print("输入错误请重新输入！")
        return

    if c == '7.1':
        print("正在保存，请稍等",end="")
        Thread(target = save_config).start()
        while(True):
            if g_isDone == False:
                print(".",end="",flush=True)
                sleep(0.2)
            else:
                break
        return


    if c == '7.2':
        print("正在读取，请稍等",end="")
        Thread(target = read_config).start()
        while(True):
            if g_isDone == False:
                print(".",end="",flush=True)
                sleep(0.2)
            else:
                break
        return
        
    if c == '7.3':
        print("-------------------------------")
        print("当前配置如下：")
        print("-------------------------------")

        print("自动加好友: %s" %(str(g_autoAddFriend)))
        print("自动回复好友：%s" %(str(g_autoReplyFriend)))
        print("自动监控消息撤回：%s" %(str(g_checkIfCallback)))
        
        print("自动回复群@消息：%s" %(str(g_autoReplyGroup)))
        
        print("图灵机器人APIKey：%s" %(str(g_tulingAPIKey)))
        print("图灵机器人代答私聊消息：%s" %(str(g_autoReplyFriendBytuling)))
        print("图灵机器人代答群聊@消息：%s" %(str(g_autoReplygroupBytuling)))
        print("-------------------------------")
        
        return
        
    if c == '8':
        Screen_Clear()
        return
    if c == '9':
        print("已退出登陆！")
        itchat.logout()
        global g_isLogin
        g_isLogin = False
        main()
        return
    else:
        print("输入错误请重新输入")
        Choose_MainMenu()

def Print_MainMenu():
    print("\n\n============================================")
    print("\t\t1: 好友管理")
    print("\t\t   1.1: 好友性别比例")
    print("\t\t   1.2: 好友地区分布")
    print("\t\t   1.3: 显示好友列表")
    print("\t\t   1.4: 开/关自动添加好友")

    print("\t\t2: 群组管理")
    print("\t\t   2.1: 显示群组列表")
    print("\t\t   2.2: 开/关自动回复群@消息")

    print("\t\t3: 消息管理")
    print("\t\t   3.1: 开/关自动回复私聊消息")
    print("\t\t   3.2: 开/关自动监控撤回消息")

    print("\t\t4: 图灵机器人接入")
    print("\t\t   4.1: 配置图灵机器人")
    print("\t\t   4.2: 开/关图灵回复私聊消息")
    print("\t\t   4.3: 开/关图灵回复群聊@消息")

    print("\t\t7: 配置管理")
    print("\t\t   7.1: 配置保存")
    print("\t\t   7.2: 配置读取")
    print("\t\t   7.3: 查看配置")
    print("\t\t8: 清空屏幕")
    print("\t\t9: 退出登陆")
    print("============================================")



def Print_Menu():
    global g_isLogin, g_loginName

    if g_isLogin == True:  #登陆成功
        Print_MainMenu()
        print("当前已登陆！昵称：%s" %g_loginName)
        Choose_MainMenu()
    else:
        Print_LoginMenu()
        print("您尚未登陆，请先登陆！")
        Choose_LoginMenu()

def Login_Done():
    global g_isLogin
    getSelfInfo()
    Screen_Clear()

    print("登陆成功！")

    g_isLogin = True

def Login_Start(type):
    itchat.login(enableCmdQR=type, loginCallback=Login_Done)
    #itchat.login(picDir=sys.path[0] + "/QR.png", loginCallback=Login_Done)
    #itchat.login(enableCmdQR=type)
    Thread(target = itchat.run).start()
    main()

def main():
    Print_Menu()

def init():
    global g_isLogin, g_isTulingReady
    g_isLogin = g_isTulingReady = False

if __name__ == '__main__':
    init()
    while(True):
        main()
