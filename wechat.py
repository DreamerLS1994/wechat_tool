# coding:utf-8
import sys
import itchat
from itchat.content import *
from prettytable import PrettyTable
from threading import Thread

from time import sleep, strftime, localtime, time
from os import system

#全局变量定义
g_isLogin = False   #是否登陆：False:未登录  True:已登录
g_isDone = False    #子进程完成标记，用于打点计时
g_loginName = ""
g_autoAddFriend = False


#@click.command()
#@click.option('-c',required=True,type=click.Choice(['1','2']))   # 限定-c的值为start，或者stop，required表示是否为必填参数

def logging(str):
	Time = strftime('%Y-%m-%d %H:%M:%S',localtime(time()))
	print("[LOGGING] " + Time + str, flush=True)


@itchat.msg_register([FRIENDS])
def add_friend(msg):
	print(msg, flush=True)
	global g_autoAddFriend
	if g_autoAddFriend == True:
		itchat.add_friend(**msg['Text'])
		itchat.send_msg('你好！很高兴认识你！', msg['RecommendInfo']['UserName'])
		logging("收到[%s]添加好友请求，已经自动通过！" %msg['RecommendInfo']['NickName'])
	
	
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
	
def Print_LoginMenu():
	print("============================================")
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
	global g_isDone, g_autoAddFriend
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
		
	if c == '1.5':
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
				print("自动添加好友当前已关闭，是否开启？: ", end="")
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

	if c =='8':
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
		return

def Print_MainMenu():
	print("============================================")
	print("\t\t1: 好友管理")
	print("\t\t   1.1: 好友性别比例")
	print("\t\t   1.2: 地区分布比例")
	print("\t\t   1.3: 显示好友列表")
	print("\t\t   1.4: 好友删除检测")
	print("\t\t   1.5: 开/关自动添加好友")

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
	#Thread(target = Login_Status).start()
	
	Thread(target = itchat.run).start()
	print("登陆成功！")
	g_isLogin = True
	main()

def Login_Start(type):
	itchat.login(enableCmdQR=type,loginCallback=Login_Done)
	#itchat.login(picDir=sys.path[0] + "/QR.png", loginCallback=Login_Done)
	#itchat.login(enableCmdQR=type)

def main():
	Print_Menu()

def init():
	global g_isLogin
	g_isLogin = False
	g_autoAddFriend = False
	
if __name__ == '__main__':
	while(True):
		main()
