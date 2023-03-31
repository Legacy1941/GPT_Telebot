import telebot
import openai
import sqlite3
import threading

from telebot import util, types
from config import bot_token, openAI_token

API_TOKEN = bot_token
openai.api_key = openAI_token
bot = telebot.TeleBot(API_TOKEN, num_threads=40)
count = 0
last_message = ''

class WorkWithBase:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor() 

    def to_get_data(self, Request):
        # Получение данных из базы. (Работает только с SELECT)
        try:
            self.cursor.execute(Request)
            self.conn.commit()
            records = self.cursor.fetchall()
            self.conn.close()
            return records
        except Exception as Mistake:
            print(Mistake)
            self.conn.rollback()
        self.conn.close()
    
    def base_manipulation(self, Request):
        # Проводит манипуляции с базой. (Работает только с INSERT, UPDATE, REMOVE, CREATE)
        try:
            self.cursor.execute(Request)
            self.conn.commit()
        except Exception as Mistake:
            print(Mistake)
            self.conn.rollback()
        self.conn.close()

class UserDatabase:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users
                            (id INTEGER PRIMARY KEY,
                            username TEXT,
                            roleuser TEXT,
                            user_model TEXT,
                            banned_status INTEGER)''')
        self.conn.commit()

    def insert_user(self, id, username, roleuser, user_model, banned_status):
        self.cursor.execute("INSERT INTO users (id, username, roleuser, user_model, banned_status) VALUES (?, ?, ?, ?, ?)", (id, username, roleuser, user_model, banned_status))
        self.conn.commit()

    def close_connection(self):
        self.conn.close()

class WorkingInDatabase:
        
    def get_users(self):
        db = WorkWithBase('user_base.db')
        records = db.to_get_data("""SELECT * from users""")
        return records

    def get_only_one_user(self, message):
        db = WorkWithBase('user_base.db')
        records = db.to_get_data(f"""SELECT * from users WHERE id = {message.from_user.id} AND roleuser = 'Admin'""")
        
        return records
    
    def check_ban_state(self, message):
        db = WorkWithBase('user_base.db')
        records = db.to_get_data(f"""SELECT * from users WHERE id = {message.from_user.id} AND banned_status = 1""")
        
        return records

    def get_list_of_banned_users(self):
        db = WorkWithBase('user_base.db')
        records = db.to_get_data(f"""SELECT * from users WHERE banned_status = {1}""")
        if len(records) == 0:
            return 'False'
        return records
    
    def block_User(self, message):
        try:
            db = WorkWithBase('user_base.db')
            db.base_manipulation(f"""UPDATE users SET banned_status = 1 WHERE id = {message.text}""")
            bot.send_message(message.from_user.id, 'Пользователь был заблокирован.')
        except Exception as Mistake:
            bot.send_message(message.from_user.id, 'Пользователь с таким ID не обнаружен.')
            print(Mistake)

    def un_block_User(self, message):
        try:
            db = WorkWithBase('user_base.db')
            db.base_manipulation(f"""UPDATE users SET banned_status = 0 WHERE id = {message.text}""")
            bot.send_message(message.from_user.id, 'Пользователь был разблокирован.')
        except Exception as Mistake:
            bot.send_message(message.from_user.id, 'Пользователь с таким ID не обнаружен.')
            print(Mistake)

    def get_all_namemodel(self):
        db = WorkWithBase('user_base.db')
        records = db.to_get_data("""SELECT name_model from models""")
        
        return records

    def update_user_model(self, message):
        try:
            db = WorkWithBase('user_base.db')
            db.base_manipulation(f"""UPDATE users SET user_model = '{message.text}' WHERE id = {message.from_user.id}""")
            bot.send_message(message.from_user.id, 'Модель была изменена.')
        except Exception as Mistake:
            bot.send_message(message.from_user.id, 'Непредвиденная ошибка во время смены модели.')
            print(Mistake)

    # Получение параметров для обращения к определенной модели 
    def get_models_from_users(self, message):
        db = WorkWithBase('user_base.db')
        records = db.to_get_data(f"""SELECT user_model from users WHERE id = {message.from_user.id}""")
        db = WorkWithBase('user_base.db')
        # records = db.to_get_data(f"""SELECT * from models WHERE name_model = {records[0][0]}""")
        records = db.to_get_data(f"SELECT * from models WHERE name_model = '{str(records[0][0])}'")
        return records  
    # 

    # Формирование respons'a
    def making_response(self, message):
        params = WorkingInDatabase.get_models_from_users(self,message)
        if params[0][1] == 'gpt-3.5-turbo':
          userMessage = [{'content': message.text, 'role': "user"}]
          request =  openai.ChatCompletion.create(
                    model               = params[0][1],
                    messages            = userMessage,
                    temperature         = params[0][2],
                    top_p               = params[0][3],
                    frequency_penalty   = params[0][4],
                    presence_penalty    = params[0][5],) 
          return request['choices'][0]['message']['content']
        elif params[0][1] == 'text-davinci-003':
            request =  openai.Completion.create(
                    model               = params[0][1],
                    prompt              = message.text,
                    temperature         = params[0][2],
                    top_p               = params[0][3],
                    frequency_penalty   = params[0][4],
                    presence_penalty    = params[0][5],)  
            return request['choices'][0]['text']   

    def get_user_model(self, message):
        pass 

class UserAction:
    def __init__(self, message):
        self.message = message
    
    def userActivity(self):
        db = WorkingInDatabase()
        bot.delete_message(self.chat.id, self.message_id)

        if self.text == 'Получить список всех пользователй':
            bot.send_message(self.from_user.id,f'Список пользователей которые пользовались ботом:', reply_markup=types.ReplyKeyboardRemove()) 
            for user in db.get_users():
                bot.send_message(self.from_user.id, text = "• <b>" + user[1] + "</b>" + "<b> — </b>" + "UserID: " + f"{user[0]}", parse_mode='HTML')

        elif self.text == 'Просмотреть список заблокированных пользователей':
            bot_message = bot.send_message(self.from_user.id,f'Список пользователей которые были заблокированны:', reply_markup=types.ReplyKeyboardRemove()) 
            for user in db.get_list_of_banned_users():
                if user == 'F':
                    bot.delete_message(self.chat.id, bot_message.message_id)
                    bot.send_message(self.from_user.id, text = "В данный момент нету заблокированных пользователей")
                    break 
                bot.send_message(self.from_user.id, text = "• <b>" + user[1] + "</b>" + "<b> — </b>" + "UserID: " + f"{user[0]}", parse_mode='HTML')
        
        elif self.text == 'Заблокировать пользователя':
            send = bot.send_message(self.from_user.id,f'Введите ID пользователя:', reply_markup=types.ReplyKeyboardRemove())
            bot.register_next_step_handler(send, db.block_User)

        elif self.text == 'Разблокировать пользователя':
            send = bot.send_message(self.from_user.id,f'Введите ID пользователя:', reply_markup=types.ReplyKeyboardRemove())
            bot.register_next_step_handler(send, db.un_block_User)

@bot.message_handler(commands=['edit_model'])
def send_model(message):
    db = WorkingInDatabase()

    keyBoard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for button in db.get_all_namemodel():
        keyBoard.add(types.KeyboardButton(button[0]))

    send =  bot.send_message(message.from_user.id,f'Какая именно модель вас интересует?', reply_markup=keyBoard)
    bot.register_next_step_handler(send, db.update_user_model)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, """Приветствуем вас в BabyGPT!
Мы надеемся, что вы будете наслаждаться использованием нашего сервиса и получите максимальное удовольствие от использования нашего бота. 
Спасибо за то, что выбрали BabyGPT!""")

    try:
        db = UserDatabase('user_base.db')
        db.insert_user(message.from_user.id, message.from_user.full_name, 'User', 'gpt-3.5-turbo', 0)
        db.close_connection()
    except Exception as Mistake:
        print(Mistake)

@bot.message_handler(commands=['admin'])
def create_adminPanel(message):
    db = WorkingInDatabase()
    if len(db.get_only_one_user(message)) >= 1:
        keyBoard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

        button_one = types.KeyboardButton(text='Просмотреть список заблокированных пользователей')
        button_two = types.KeyboardButton(text='Оповестить пользователей')
        button_three = types.KeyboardButton(text='Заблокировать пользователя')
        button_four = types.KeyboardButton(text='Разблокировать пользователя')
        button_five = types.KeyboardButton(text='Получить список всех пользователй')

        keyBoard.add(button_one, button_two, button_three, button_four, button_five)
        send =  bot.send_message(message.from_user.id,f'Здравствуйте {message.from_user.username}', reply_markup=keyBoard)
        bot.register_next_step_handler(send, UserAction.userActivity)
    else:
        bot.send_message(message.from_user.id, "У вас нет доступа к панели администратора!")

@bot.message_handler(chat_types=['private'], func=lambda message: True)
def gpt_message(message):
    global count
    global last_message
    db = WorkingInDatabase()
    if len(db.check_ban_state(message)) < 1:
        # if count <=1:
            # userMessage = [{'content': message.text + ' Контекст: ' + last_message,'role': "user"}]
            try:
                count += 1
                botMessage = bot.send_message(chat_id=message.from_user.id, text='⌛️ Подготовка ответа...')
                # Выбор модели - gpt / davinchi
                response = db.making_response(message)
                # response = openai.ChatCompletion.create(
                #     model="gpt-3.5-turbo",
                #     messages= userMessage,
                #     temperature= 0.2,
                #     top_p=0.0,
                #     frequency_penalty= 0.4,
                #     presence_penalty= 0.0,)  
                bot.delete_message(chat_id=message.chat.id, message_id=botMessage.message_id)
            except Exception as Mistake:
                print(Mistake)
                bot.reply_to(message, text='Во время отправки сообщения произошла ошибка, попробуйте повторить вопрос или повторить попытку позже.')
                return False
            try:
                for messageText in util.smart_split(response, 3000):
                    bot.reply_to(message, messageText)
                    count -= 1
                # last_message = ''
                # last_message = 'Вопрос: ' + userMessage[0]['content'] +  ' Ответ: ' + response['choices'][0]['message']['content'].strip()
            except Exception as Mistake:
                bot.send_message(chat_id=message.from_user.id, text='К сожалению, похоже сеть перегружена, повтори вопрос или попробуй позже:')
                print(Mistake)
                count -= 1
        # else:
        #     bot.send_message(message.from_user.id, 'Количество одновременных запросов не может превышать больше 2')
        #     count -= 1
    else:
        bot.send_message(message.from_user.id, 'Вам было запрещено использовать BabyGPT')
        count -= 1

        
if __name__ == '__main__':
    print('Ready for work!')
    bot.infinity_polling(none_stop=True, timeout=120, long_polling_timeout=120)
    print('Goodbye')
