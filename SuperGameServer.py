import json
import os
import socket
import time
import tkinter
from ctypes import OleDLL
from math import log10
from threading import Thread, active_count
from tkinter import scrolledtext, ttk

__version__ = '2.6.16'

OleDLL('shcore').SetProcessDpiAwareness(1)


def log(info: str, flag: str) -> str:
    """ 日志记录函数 """
    _time = time.strftime('%Y/%m/%d %H:%M:%S', time.localtime())
    record = '[%s %s]%s\n' % (_time, flag, info)
    with open('server.log', 'a', encoding='utf-8') as file:
        file.write(record)
    Server.text.configure(state='normal')
    Server.text.insert('end', '['+record[12:])
    Server.text.configure(state='disabled')
    Server.text.see('end')
    return record


class Server:
    """ 服务器主界面 """

    root = tkinter.Tk()
    root.title('SuperGameServer-v%s' % __version__)
    root.geometry('%dx%d' % (1080, 607.5))
    root.resizable(False, False)
    # root.call('tk', 'scaling', 125/75)
    port = tkinter.IntVar(value=10000)
    conn = tkinter.IntVar(value=1000)
    thread = tkinter.StringVar()
    command = tkinter.StringVar()
    upload = tkinter.StringVar()
    download = tkinter.StringVar()

    tkinter.Frame(root, bg='white').place(width=1080, height=540, y=1)

    kw = {'anchor': 'w', 'font': ('楷体', 12)}
    tkinter.Label(root, text='上传速度', fg='red',
                  **kw).place(width=105, height=37.5, x=750, y=397.5)
    tkinter.Label(root, text='下载速度', fg='green',
                  **kw).place(width=105, height=37.5, x=750, y=442.5)
    tkinter.Label(root, text='线程数量', fg='blue',
                  **kw).place(width=105, height=37.5, x=750, y=487.5)
    tkinter.Label(root, text='连接端口',
                  **kw).place(width=105, height=37.5, x=750, y=15)
    tkinter.Label(root, text='连接数量',
                  **kw).place(width=105, height=37.5, x=750, y=60)
    tkinter.Label(root, textvariable=thread,
                  **kw).place(width=202.5, height=37.5, x=862.5, y=487.5)
    tkinter.Label(root, textvariable=upload,
                  **kw).place(width=202.5, height=37.5, x=862.5, y=397.5)
    tkinter.Label(root, textvariable=download,
                  **kw).place(width=202.5, height=37.5, x=862.5, y=442.5)

    entry_port = ttk.Entry(root, textvariable=port)
    entry_port.place(width=202.5, height=37.5, x=862.5, y=15)
    entry_conn = ttk.Entry(root, textvariable=conn)
    entry_conn.place(width=202.5, height=37.5, x=862.5, y=60)
    entry_comm = ttk.Entry(root, textvariable=command)
    entry_comm.place(width=720, height=34.5, x=15, y=556.5)

    button_start = ttk.Button(
        root, text='启 动', command=lambda: Server.start(), cursor='hand2')
    button_start.place(width=150, height=37.5, x=915, y=555)
    button_stop = ttk.Button(
        root, text='中 止', command=lambda: Server.stop(), state='disabled')
    button_stop.place(width=150, height=37.5, x=750, y=555)

    text = scrolledtext.ScrolledText(
        root, relief='flat', highlightthickness=1, font=('楷体', 12),
        highlightbackground='#5C5C5C', highlightcolor='#4A9EE0', state='disabled')
    text.place(x=15, y=15, width=720, height=510)

    canvas = tkinter.Canvas(
        root, highlightbackground='#5C5C5C', highlightthickness=1, bg='white')
    canvas.place(x=750, y=105, width=315, height=285)
    canvas.create_text(157.5, 142.5, text='网络数据传输\n实时监测图',
                       fill='grey', font=('楷体', 15), justify='center')

    for i in range(1, 11):
        canvas.create_line(i*31.5, 0, i*31.5, 285, fill='#CCC')
        canvas.create_line(0, i*28.5, 315, i*28.5, fill='#CCC')

    server: socket.socket = None  # 服务器套接字
    flag: dict[str, bool] = {}  # 服务器启动标识
    time: int = 0  # 运行时间
    up: int = 0  # 上传数据量
    down: int = 0  # 下载数据量

    connection = {}  # type: dict[Connection, str]
    attendance: list[str] = []
    room: dict[str, list[set]] = {'chess': [], 'Gobang': [], 'Flip': []}

    def __init__(self) -> None:
        self.entry_comm.bind('<Key-Return>', lambda _: self.input())
        self.root.mainloop()

    @classmethod
    def start(cls) -> None:
        """ 启动服务器 """

        if not cls.check():
            log('服务器启动失败！', 'WARN')
            return

        cls.entry_port.configure(state='disabled')
        cls.entry_conn.configure(state='disabled')
        cls.button_start.configure(state='disabled', cursor='arrow')
        cls.button_stop.configure(state='normal', cursor='hand2')

        cls.flag = {'main': True, 'refresh': True, 'monitor': True}

        log('创建服务端套接字', 'INFO')
        cls.server = socket.socket()

        addr, port = socket.gethostbyname(socket.gethostname()), cls.port.get()
        log('绑定地址: %s' % addr, 'INFO')
        log('绑定端口: %d' % port, 'INFO')
        cls.server.bind((addr, port))

        log('设定服务器最大连接数量: %d' % cls.conn.get(), 'INFO')
        cls.server.listen(cls.conn.get())

        log('启动数据传输监测协程', 'INFO')
        cls.monitor()
        log('启动服务器数据更新协程', 'INFO')
        cls.refresh()

        log('启动客户端连接线程', 'INFO')
        Thread(target=cls.connect_client, daemon=True).start()

        log('Done！若需要帮助，请键入“help”', 'INFO')

    @classmethod
    def stop(cls) -> None:
        """ 中止服务器 """
        if cls.flag['main']:
            cls.button_stop.configure(state='disabled', cursor='arrow')
            log('终止服务器数据更新协程', 'INFO')
            cls.flag['main'] = False
            log('关闭服务器套接字', 'INFO')
            cls.server.close()
            cls.stop()
        elif any(cls.flag.values()):
            cls.root.after(10, cls.stop)
        else:
            cls.thread.set('')
            cls.upload.set('')
            cls.download.set('')
            cls.button_start.configure(state='normal', cursor='hand2')
            cls.entry_port.configure(state='normal')
            cls.entry_conn.configure(state='normal')
            log('Done！点击“启动”以重启服务器', 'INFO')

    @classmethod
    def check(cls) -> bool:
        """ 参数检查 """
        try:
            log('检查服务器参数', 'INFO')
            if not 8192 <= cls.port.get() <= 65535:
                log('端口允许范围是8192~65535', 'ERROR')
                return False
            if not 100 <= cls.conn.get() <= 1000:
                log('连接数量允许范围是100~1000', 'ERROR')
                return False
            return True
        except tkinter.TclError:
            log('服务器参数应为整数', 'ERROR')
            return False

    @classmethod
    def connect_client(cls) -> None:
        """ 开启套接字的监听 """
        while cls.flag['main']:
            try:
                connect = cls.server.accept()[0],
                Thread(target=Connection, args=connect).start()
            except Exception as error:
                if cls.flag['main']:
                    log('异常客户端连接 %s%s' % (type(error), error), 'WARN')
                else:
                    for client in list(cls.connection):
                        client.close()
                    log('终止客户端连接线程', 'INFO')

    @classmethod
    def monitor(cls) -> None:
        """ 网络数据监测 """

        lines = Server.canvas.find_withtag('line')

        if lines:
            c1 = Server.canvas.coords(
                lines[-2])+[345, 285-log10(1+cls.up)*28.5]
            c2 = Server.canvas.coords(
                lines[-1])+[345.5, 285-log10(1+cls.down)*28.5]
            if Server.canvas.coords(lines[1])[2] < 0:
                cls.canvas.delete(*lines[:2])  # 删除过多线条
        else:
            c1 = [313.5, 285, 345, 285-log10(1+cls.up)*28.5]
            c2 = [315, 285, 345.5, 285-log10(1+cls.down)*28.5]

        cls.canvas.create_line(c1[-4:], tags='line', fill='red')
        cls.canvas.create_line(c2[-4:], tags='line', fill='green')

        for line in Server.canvas.find_withtag('line'):
            cls.canvas.move(line, -7.5, 0)  # 移动全部线条

        up, down = cls.up*5, cls.down*5
        cls.up, cls.down = 0, 0

        unit = 'B/s'
        if up >= 1024:
            up /= 1024
            unit = 'KB/s'
            if up >= 1024:
                up /= 1024
                unit = 'MB/s'
        cls.upload.set('%.1f%s' % (round(up), unit))

        unit = 'B/s'
        if down > 1024:
            down /= 1024
            unit = 'KB/s'
            if down >= 1024:
                down /= 1024
                unit = 'MB/s'
        cls.download.set('%.1f%s' % (round(down), unit))

        if cls.flag['main']:
            cls.root.after(200, cls.monitor)
        else:
            cls.flag['monitor'] = False
            for item in cls.canvas.find_withtag('line'):
                cls.canvas.delete(item)

    @classmethod
    def refresh(cls, day: int = -1) -> None:
        """ 刷新数据 """
        if not cls.flag['main']:
            cls.flag['refresh'] = False
            return

        cls.time += 0.1
        cls.thread.set(active_count())

        if day != time.localtime()[2]:
            day = time.localtime()[2]

            log('清空签到表数据', 'INFO')
            cls.attendance.clear()

        cls.root.after(100, cls.refresh, day)

    @classmethod
    def input(cls) -> None:
        """ 输入命令 """
        cmd = cls.command.get()

        if not cmd:
            return

        log(cmd, 'IN ')
        cls.command.set('')
        cmd = cmd.split()

        try:
            if cmd[0] == 'help':
                with open('command.txt', 'r', encoding='utf-8') as data:
                    log(data.read(), 'OUT')
            elif cmd[0] == 'connection':
                log(list(cls.connection.values()), 'OUT')
            elif cmd[0] == 'attendance':
                log(cls.attendance, 'OUT')
            elif cmd[0] == 'room':
                log(cls.room, 'OUT')
            elif cmd[0] == 'time':
                log('Time:%.1fs' % cls.time, 'OUT')
            elif cmd[0] == 'say':
                log('Server:\n%s' % cmd[1], 'OUT')
                for conn, name in Server.connection.items():
                    if name:
                        conn.send(cmd='Chat', account='Server', message=cmd[1])
            elif cmd[0] == 'kick':
                for conn, account in cls.connection.items():
                    if account == cmd[1]:
                        conn.close()
                        log('%s 被踢出服务器' % cmd[1], 'OUT')
                        break
                else:
                    log('%s 不在线或不存在' % cmd[1], 'OUT')
            elif cmd[0] == 'clear':
                if cmd[1] == 'connection':
                    for client in cls.connection:
                        client.close()
                    log('已断开所有客户端的连接', 'OUT')
                elif cmd[1] == 'attendance':
                    cls.attendance.clear()
                    log('清空签到表数据', 'OUT')
                else:
                    log('Unknow Command', 'OUT')
            else:
                log('Unknow Command', 'OUT')
        except:
            log('Unknow Command', 'OUT')


class Connection:
    """ 客户端连接类 """

    def __init__(self, connect: socket.socket) -> None:
        Server.connection[self] = None
        self.flag = True  # 活跃标识
        self.connect = connect  # 连接
        self.authentication()

    def send(self, **kw) -> None:
        """ 发送数据 """
        try:
            msg = kw.__repr__().encode('UTF-8')
            self.connect.send(msg)
            Server.up += msg.__sizeof__()
        except Exception as error:
            log('数据发送失败 %s%s' % (type(error), error), 'WARN')

    def recv(self) -> dict:
        """ 接收数据 """
        try:
            msg = self.connect.recv(4096)
            data = eval(msg.decode('UTF-8'))
            if isinstance(data, dict):
                Server.down += msg.__sizeof__()
                return data
        except TimeoutError:
            if Server.connection.get(self):
                log('与 %s 失去网络连接' % Server.connection[self], 'INFO')
        except WindowsError as error:
            if error.errno in (10038, 10054):
                return {}
            log('数据接收失败 %s' % error, 'WARN')
        except Exception as error:
            _type = type(error)
            if _type not in (UnicodeDecodeError, SyntaxError, ValueError, NameError):
                log('数据接收失败 %s%s' % (_type, error), 'ERROR')

        self.close()
        return {}

    def authentication(self) -> None:
        """ 身份验证 """
        self.connect.settimeout(3)
        if self.recv().get('cmd') == 'Identity':
            self.send(cmd='Identity')
            self.connect.settimeout(60)
            self.process()
        else:
            self.close()

    def close(self) -> None:
        """ 断开连接 """
        if not self.flag:
            return

        if Server.connection.get(self):
            log('%s 登出服务器' % Server.connection[self], 'INFO')

        self.flag = False
        self.connect.close()
        del Server.connection[self]

    def process(self):
        """ 客户端数据处理函数 """
        while self.flag:
            msg = self.recv()

            if msg.get('cmd') == 'Quit':
                self.close()

            elif msg.get('cmd') == 'Delay':
                self.send(cmd='Delay')

            elif msg.get('cmd') == 'Announcement':
                with open('Announcement.txt', 'r', encoding='utf-8') as file:
                    self.send(cmd='Announcement', data=file.read())

            elif msg.get('cmd') == 'Feedback':
                log('%s 反馈' % msg['account'], 'INFO')
                with open('feedback.txt', 'a', encoding='utf-8') as file:
                    file.write('%s\n\n' % msg['feedback'])

            elif msg.get('cmd') == 'Login':
                Account_System.login(self, msg)

            elif msg.get('cmd') == 'Register':
                Account_System.register(self, msg)

            elif msg.get('cmd') == 'Update':
                file = Update_System.check_version(msg['version'])
                if file:
                    self.send(cmd='Update', value=True,
                              size=os.path.getsize('packages/%s.zip' % file))
                    time.sleep(0.01)
                    Update_System.update(self, file)
                else:
                    self.send(cmd='Update', value=False)

            elif msg.get('cmd') == 'Attendance':
                if (date := time.localtime())[:3] == msg['date']:
                    if msg['account'] in Server.attendance:
                        self.send(cmd='Attendance', value=False)
                    else:
                        self.send(cmd='Attendance', value=True)
                        Server.attendance.append(msg['account'])
                        log('%s 今日签到' % msg['account'], 'INFO')
                        with open('data/%s.json' % msg['account'], 'r', encoding='utf-8') as file:
                            user = json.load(file)
                        user['money'] += 10 if date[6] == 5 or date[6] == 6 else 5
                        with open('data/%s.json' % msg['account'], 'w', encoding='utf-8') as file:
                            json.dump(user, file)
                else:
                    self.send(cmd='Attendance', value=None)

            elif msg.get('cmd') == 'Chat':
                log('%s:\n%s' % (msg['act'], msg['msg']), 'INFO')
                for conn, name in Server.connection.items():
                    if name:
                        conn.send(
                            cmd='Chat', act=msg['act'], message=msg['msg'])


class Account_System:
    """ 账号系统 """

    with open('data/init.json', 'r', encoding='utf-8') as file:
        init: dict = json.load(file)

    @classmethod
    def login(cls, conn: Connection, msg: dict) -> None:
        """ 登录操作 """
        if value := msg['act'] in os.listdir('data'):
            log('%s 登录服务器' % msg['act'], 'INFO')
            for conn, act in tuple(Server.connection.items()):
                if act == msg['act']:  # 重复登录
                    conn.close()
                    break
            with open('data/%s/data.json' % msg['act'], 'r', encoding='utf-8') as file:
                if value := json.load(file)['password'] == msg['psd']:
                    Server.connection[conn] = msg['act']
        conn.send(cmd='Login', value=value)

    @classmethod
    def register(cls, conn: Connection, msg: dict) -> None:
        """ 注册操作 """
        if value := not msg['act'] in os.listdir('data'):
            log('%s 注册账号' % msg['act'], 'INFO')
            cls.init['password'] = msg['psd']
            os.mkdir('data/' + msg['act'])
            open('data/%s/cache.dat' % msg['act'], 'w').close()
            with open('data/%s/data.json' % msg['act'], 'w', encoding='utf-8') as file:
                json.dump(cls.init, file)
        conn.send(cmd='Register', value=value)

    @classmethod
    def query(cls, conn: Connection, msg: dict) -> None:
        """ 查询操作 """
        if value := msg['act'] in os.listdir('data'):
            with open('data/%s/data.json' % msg['act'], 'r', encoding='utf-8') as data:
                value = json.load(data)['data']
        conn.send(cmd='Query', value=value)

    @classmethod
    def modify(cls, act: str, **kw) -> dict | None:
        """ 修改数据 """
        with open('data/%s/data.json' % act, 'r', encoding='utf-8') as file:
            data: dict[str, str | dict] = json.load(file)
        if not kw:
            return data
        elif kw.get('friend', None):
            data['friend'] = kw['friend']
        else:
            data['data'].update(**kw)
        with open('data/%s/data.json' % act, 'w', encoding='utf-8') as file:
            json.dump(file, data)

    @classmethod
    def add_friend(cls, conn: Connection, act: str) -> None:
        """ 添加好友操作 """
        for conn_, user in Server.connection.items():
            if user != act:
                conn_.send(cmd='Validation', act=Server.connection[conn])
                break
        else:
            with open('data/%s/cache.dat' % act, 'a', encoding='utf-8') as file:
                file.write('Server %s\n' % act)

    @classmethod
    def delete_firend(cls, conn: Connection, act: str) -> None:
        """ 删除好友操作 """
        friend: list = cls.modify(Server.connection[conn])['friend']
        friend.remove(act)
        cls.modify(Server.connection[conn], friend=friend)


class Chat_System:
    """ 聊天系统 """

    @classmethod
    def broadcast(cls, act: str, msg: dict):
        """ 广播操作 """
        for conn, user in Server.connection.items():
            if user:
                conn.send(cmd='Broadcast', act=act, msg=msg)

    @classmethod
    def chat(cls, conn: Connection, act: str, msg: dict) -> None:
        """ 聊天操作 """
        for conn, user in Server.connection.items():
            if act == user:
                conn.send(cmd='Chat', frm=Server.connection[conn], msg=msg)
                break
        else:
            with open('data/%s/cache.dat' % act, 'a', encoding='utf-8') as file:
                file.write('%s %s\n' % (act, msg))

    @classmethod
    def cache(cls, conn: Connection) -> None:
        """ 释放缓存消息 """
        with open('data/%s/cache.dat', 'r', encoding='utf-8') as file:
            for info in file.readlines():
                frm, msg = info.split()
                if frm == 'Server':
                    conn.send(cmd='Validation', act=msg)
                else:
                    conn.send(cmd='Chat', frm=frm, msg=msg)
        open('data/%s/cache.dat' % Server.connection[conn], 'w').close()


class Update_System:
    """ 更新系统 """

    @classmethod
    def check_version(cls, version: list[int]) -> str:
        """ 版本检查 """
        with open('packages/version.dat', 'r', encoding='utf-8') as file:
            data = file.read().split()
        if data[-1] == version:
            return ''
        else:
            try:
                version = data[data.index(version) + 1]
            except:
                version = data[0]
        return 'package-%s' % version

    @classmethod
    def update(cls, connect: Connection, file: str):
        """ 更新 """
        file = open('packages/%s.zip' % file, 'rb')
        try:
            while down := file.read(8192):
                connect.connect.send(down)
                Server.up += down.__sizeof__()
        except:
            connect.close()
        file.close()


class Game_System:
    """ 游戏系统 """

    @classmethod
    def connect_game(cls, act: str, game: str):
        """ 连接游戏服务器 """

    @classmethod
    def create_room(cls, act: str, game: str):
        """ 创建房间 """


if __name__ == '__main__':
    Server()
