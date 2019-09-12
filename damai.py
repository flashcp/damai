import time
import pickle
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

DM_LOGIN_URL = 'https://passport.damai.cn/login?ru=https%3A%2F%2Fwww.damai.cn%2F'
CHROME_DRIVER = 'D:/python3/Scripts/chromedriver.exe'  # Windows和Mac的配置路径不一样


class SessionException(Exception):
    def __init__(self, message):
        super().__init__(self)
        self.message = message

    def __str__(self):
        return self.message


class Crawler:
    def __init__(self, username, password, name, site, date, prices, people):
        """
        :param username: 用户名
        :param password: 密码
        :param name: 明星姓名
        :param site: 演出地点
        :param date: 演出日期
        :param prices: 价格列表，多种价格可选
        :param people: 观影人
        """
        self.browser = None
        self.wait = None
        self.links = ""
        self.username = username
        self.password = password
        self.name = name
        self.site = site
        self.date = date
        self.prices = prices
        self.people = people

    def start(self):
        print("###初始化浏览器###")
        self.init_browser()
        time.sleep(1)
        # 如果cookie 登陆不成功，使用密码登陆
        if "大麦登录" in self.browser.title:
            # print("cooike尝试失败，尝试输入账号")
            self.browser.switch_to.frame("alibaba-login-box")
            self.__write_username()
            time.sleep(2.5)
            self.__write_password()
            time.sleep(3.5)
            if self.__lock_exist():
                self.__unlock()
            # print("开始发起登录请求")
            self.__submit()
        time.sleep(4.5)
        # print("登录成功，开始选择演唱会")
        self.select_concert()
        time.sleep(6.5)
        # print("选票")
        self.choose_ticket()
        # print("买票")
        self.buy_ticket()

    def __write_username(self):
        """
        输入账号
        :param username:
        :return:
        """
        username_input_element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#fm-login-id")))
        username_input_element.clear()
        username_input_element.send_keys(self.username)

    def __write_password(self):
        """
        输入密码
        :param password:
        :return:
        """
        password_input_element = self.browser.find_element_by_id("fm-login-password")
        password_input_element.clear()
        password_input_element.send_keys(self.password)

    def __lock_exist(self):
        """
        判断是否存在滑动验证
        :return:
        """
        return self.is_element_exist('#nc_1_wrapper') and self.browser.find_element_by_id(
            'nc_1_wrapper').is_displayed()

    def __unlock(self):
        """
        执行滑动解锁
        :return:
        """
        bar_element = self.browser.find_element_by_id('nc_1_n1z')
        ActionChains(self.browser).drag_and_drop_by_offset(bar_element, 300, 0).perform()
        time.sleep(1.5)
        self.browser.get_screenshot_as_file('error.png')
        if self.is_element_exist('.errloading > span'):
            error_message_element = self.browser.find_element_by_css_selector('.errloading > span')
            error_message = error_message_element.text
            self.browser.execute_script('noCaptcha.reset(1)')
            raise SessionException('滑动验证失败, message = ' + error_message)

    def __submit(self):
        """
        提交登录
        :return:
        """
        self.browser.find_element_by_css_selector('.password-login').click()
        time.sleep(0.5)
        if self.is_element_exist("#login-error"):
            error_message_element = self.browser.find_element_by_css_selector('#login-error > p')
            error_message = error_message_element.text
            raise SessionException('登录出错, message = ' + error_message)

    def set_cookie(self):
        try:
            # 载入cookie
            cookies = pickle.load(open("cookies.pkl", "rb"))
            print("读取cookie", cookies)
            self.browser.delete_all_cookies()
            for cookie in cookies:
                cookie_dict = {
                    # 必须有，不然就是假登录
                    'domain': cookie.get('domain'),
                    'name': cookie.get('name'),
                    'value': cookie.get('value'),
                    "expiry": "",
                    'path': '/',
                    'httpOnly': False,
                    'HostOnly': False,
                    'Secure': False}
                self.browser.add_cookie(cookie_dict)
            print('###载入Cookie###')
        except Exception as e:
            print(e)

    # 选择演出会
    def select_concert(self):
        # 保存cookie，用于 cookie 登陆
        pickle.dump(self.browser.get_cookies(), open("cookies.pkl", "wb"))
        # print("保存cookie", self.browser.get_cookies())

        input_concert = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".input-search")))
        input_concert.clear()
        input_concert.send_keys(self.name)
        self.browser.find_element_by_css_selector(".btn-search").click()
        concert_content = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".item__main .item__box")))
        # 查找包含演唱会地点的超链接并保存链接
        self.links = concert_content.find_element_by_xpath("//a[contains(text(),'{}')]".format(self.site)).get_attribute("href")
        # print("购买链接", self.links)
        self.browser.get(self.links)

    # 选择门票
    def choose_ticket(self):
        num = 1  # 第一次尝试
        time_start = time.time()
        while self.browser.title.find('订单结算') == -1:  # 如果跳转到了订单结算界面就算这部成功了
            if num != 1:  # 如果前一次失败了，那就刷新界面重新开始
                self.browser.get(self.links)
            try:
                perform_data = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".select_right_list")))
                # 选日期
                perform_data.find_element_by_xpath("//*[contains(text(),'{}')]".format(self.date)).click()
            except Exception as e:
                print(e)

            # 选价格
            pricelist = self.browser.find_element_by_css_selector(".select_right_list")
            for i in self.prices:
                price = pricelist.find_element_by_xpath("//*[contains(text(),'{}')]".format(i))
                if not price.text.find("缺货登记"):
                    price.click()
                    break

            self.browser.find_element_by_css_selector('.buybtn').click()
            num += 1
            try:
                element = self.wait.until(EC.title_contains('订单结算'))
            except:
                print('###未跳转到订单结算界面###')
        time_end = time.time()
        print("###经过%d轮奋斗，共耗时%f秒，抢票成功！请确认订单信息###" % (num - 1, round(time_end - time_start, 3)))

    # 购买门票
    def buy_ticket(self):
        print('###开始确认订单###')
        print('###默认购票人信息###')
        # 如果要求实名制
        try:
            buyer_list = self.browser.find_element_by_css_selector('.buyer-list-item')
            buyer_list.find_element_by_xpath("//*[contains(text(),'{}')]".format(self.people)).click()
        except Exception as e:
            print("###实名信息选择框没有显示###")
            print(e)

        # 同意以上协议
        checkbox = self.browser.find_element_by_css_selector('.next-checkbox-inner input')
        if checkbox.get_attribute("aria-checked") == "false":
            checkbox.click()
        # 提交订单
        # self.browser.find_element_by_css_selector('.next-btn.next-btn-normal.next-btn-medium').click()
        try:
            self.wait.until(EC.title_contains('支付'))
            print('###成功提交订单,请手动支付###')
        except:
            print('###提交订单失败,请查看问题###')

    def is_element_exist(self, element):
        try:
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, element)))
            return True
        except:
            return False

    def init_browser(self):
        """
        初始化selenium浏览器
        :return:
        """
        options = Options()
        # options.add_argument("--headless")
        prefs = {"profile.managed_default_content_settings.images": 1}
        options.add_experimental_option("prefs", prefs)
        options.add_argument('--proxy-server=http://127.0.0.1:8080')
        options.add_argument('disable-infobars')
        options.add_argument('--no-sandbox')

        self.browser = webdriver.Chrome(executable_path=CHROME_DRIVER, options=options)
        self.wait = WebDriverWait(self.browser, 10)
        # self.browser.implicitly_wait(3)
        self.browser.maximize_window()
        # print("cooike尝试登陆")
        self.browser.get(DM_LOGIN_URL)
        self.set_cookie()
        self.browser.refresh()


# 执行命令行
if __name__ == "__main__":
    account = ""
    password = ""
    name = "潘玮柏"
    site = "北京"
    date = "周六"
    price = ["580", "780"]
    people = ""
    Crawler(account, password, name, site, date, price, people).start()
