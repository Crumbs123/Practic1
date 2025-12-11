import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import pymysql
import hashlib
import random
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os
import datetime
import pandas as pd
from tkinter import filedialog as fd
import sys

class DigitalCaptcha:
    def __init__(self):
        self.captcha_text = ""
        self.display_text = ""
        self.generate_captcha()
    
    def generate_captcha(self):
        """Генерирует случайную цифровую капчу"""
        # Создаем 6 случайных цифр
        digits = [str(random.randint(0, 9)) for _ in range(6)]
        self.captcha_text = "".join(digits)
        self.display_text = " ".join(self.captcha_text)
        return self.display_text
    
    def check_solution(self, user_input):
        """Проверяет введенный пользователем код"""
        # Удаляем пробелы из ввода пользователя
        user_clean = user_input.replace(" ", "").strip()
        return user_clean == self.captcha_text
    
    def get_captcha_display_text(self):
        """Возвращает текст капчи для отображения"""
        return self.display_text

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect()
        
    def connect(self):
        try:
            self.connection = pymysql.connect(
                host='localhost',
                user='root',
                password='root',  
                port=3306,# Укажите ваш пароль
                database='school_management',
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            return True
        except Exception as e:
            print(f"Ошибка подключения: {str(e)}")
            return False
    
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def authenticate_user(self, username, password):
        try:
            with self.connection.cursor() as cursor:
                sql = "SELECT * FROM Пользователи WHERE логин = %s"
                cursor.execute(sql, (username,))
                user = cursor.fetchone()
                
                if user:
                    hashed_password = self.hash_password(password)
                    if user['пароль'] == hashed_password:
                        return user
                return None
        except Exception as e:
            print(f"Ошибка аутентификации: {e}")
            return None
    
    def update_login_attempts(self, username, failed_attempts=0, blocked=False):
        try:
            with self.connection.cursor() as cursor:
                if blocked:
                    sql = "UPDATE Пользователи SET попытки_входа = %s, блокирован = TRUE WHERE логин = %s"
                else:
                    sql = "UPDATE Пользователи SET попытки_входа = %s WHERE логин = %s"
                cursor.execute(sql, (failed_attempts, username))
                self.connection.commit()
        except Exception as e:
            print(f"Ошибка обновления попыток входа: {e}")
    
    def register_user(self, username, password, role, full_name, email, phone=None, class_id=None):
        try:
            with self.connection.cursor() as cursor:
                # Проверка существования пользователя
                sql = "SELECT * FROM Пользователи WHERE логин = %s"
                cursor.execute(sql, (username,))
                if cursor.fetchone():
                    return False, "Пользователь с таким логином уже существует"
                
                # Добавление нового пользователя
                hashed_password = self.hash_password(password)
                sql = """INSERT INTO Пользователи (логин, пароль, роль, полное_имя, email, телефон, класс_id) 
                         VALUES (%s, %s, %s, %s, %s, %s, %s)"""
                cursor.execute(sql, (username, hashed_password, role, full_name, email, phone, class_id))
                self.connection.commit()
                return True, "Пользователь успешно зарегистрирован"
        except Exception as e:
            return False, f"Ошибка регистрации: {str(e)}"
    
    def get_all_users(self):
        try:
            with self.connection.cursor() as cursor:
                sql = """SELECT u.*, k.название as класс_название 
                         FROM Пользователи u 
                         LEFT JOIN Классы k ON u.класс_id = k.id"""
                cursor.execute(sql)
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка получения пользователей: {e}")
            return []
    
    def get_students(self):
        try:
            with self.connection.cursor() as cursor:
                sql = """SELECT u.*, k.название as класс_название 
                         FROM Пользователи u 
                         LEFT JOIN Классы k ON u.класс_id = k.id
                         WHERE u.роль = 'Ученик'"""
                cursor.execute(sql)
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка получения учеников: {e}")
            return []
    
    def get_teachers(self):
        try:
            with self.connection.cursor() as cursor:
                sql = """SELECT * FROM Пользователи WHERE роль = 'Учитель'"""
                cursor.execute(sql)
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка получения учителей: {e}")
            return []
    
    def get_classes(self):
        try:
            with self.connection.cursor() as cursor:
                sql = """SELECT k.*, u.полное_имя as классный_руководитель 
                         FROM Классы k 
                         LEFT JOIN Пользователи u ON k.классный_руководитель_id = u.id"""
                cursor.execute(sql)
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка получения классов: {e}")
            return []
    
    def get_subjects(self):
        try:
            with self.connection.cursor() as cursor:
                sql = """SELECT p.*, u.полное_имя as учитель_имя 
                         FROM Предметы p 
                         LEFT JOIN Пользователи u ON p.учитель_id = u.id"""
                cursor.execute(sql)
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка получения предметов: {e}")
            return []
    
    def get_schedule(self, class_id=None):
        try:
            with self.connection.cursor() as cursor:
                if class_id:
                    sql = """SELECT r.*, p.название as предмет, u.полное_имя as учитель, k.название as класс
                             FROM Расписание r
                             JOIN Предметы p ON r.предмет_id = p.id
                             JOIN Пользователи u ON r.учитель_id = u.id
                             JOIN Классы k ON r.класс_id = k.id
                             WHERE r.класс_id = %s
                             ORDER BY 
                                 FIELD(r.день_недели, 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'),
                                 r.время_начала"""
                    cursor.execute(sql, (class_id,))
                else:
                    sql = """SELECT r.*, p.название as предмет, u.полное_имя as учитель, k.название as класс
                             FROM Расписание r
                             JOIN Предметы p ON r.предмет_id = p.id
                             JOIN Пользователи u ON r.учитель_id = u.id
                             JOIN Классы k ON r.класс_id = k.id
                             ORDER BY 
                                 FIELD(r.день_недели, 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'),
                                 r.время_начала"""
                    cursor.execute(sql)
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка получения расписания: {e}")
            return []
    
    def get_grades(self, student_id=None, subject_id=None):
        try:
            with self.connection.cursor() as cursor:
                sql = """SELECT o.*, p.название as предмет, u.полное_имя как ученик, 
                                t.полное_имя как учитель_имя
                         FROM Оценки o
                         JOIN Предметы p ON o.предмет_id = p.id
                         JOIN Пользователи u ON o.ученик_id = u.id
                         JOIN Пользователи t ON o.учитель_id = t.id
                         WHERE 1=1"""
                params = []
                
                if student_id:
                    sql += " AND o.ученик_id = %s"
                    params.append(student_id)
                if subject_id:
                    sql += " AND o.предмет_id = %s"
                    params.append(subject_id)
                
                sql += " ORDER BY o.дата DESC"
                cursor.execute(sql, tuple(params))
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка получения оценок: {e}")
            return []
    
    def get_homework(self, class_id=None, student_id=None):
        try:
            with self.connection.cursor() as cursor:
                if student_id:
                    sql = """SELECT h.*, p.название как предмет, u.полное_имя как учитель, 
                                    k.название как класс
                             FROM Домашние_задания h
                             JOIN Предметы p ON h.предмет_id = p.id
                             JOIN Пользователи u ON h.учитель_id = u.id
                             JOIN Классы k ON h.класс_id = k.id
                             WHERE h.класс_id = (SELECT класс_id FROM Пользователи WHERE id = %s)
                             ORDER BY h.срок_сдачи"""
                    cursor.execute(sql, (student_id,))
                elif class_id:
                    sql = """SELECT h.*, p.название как предмет, u.полное_имя как учитель, k.название как класс
                             FROM Домашние_задания h
                             JOIN Предметы p ON h.предмет_id = p.id
                             JOIN Пользователи u ON h.учитель_id = u.id
                             JOIN Классы k ON h.класс_id = k.id
                             WHERE h.класс_id = %s
                             ORDER BY h.срок_сдачи"""
                    cursor.execute(sql, (class_id,))
                else:
                    sql = """SELECT h.*, p.название как предмет, u.полное_имя как учитель, k.название как класс
                             FROM Домашние_задания h
                             JOIN Предметы p ON h.предмет_id = p.id
                             JOIN Пользователи u ON h.учитель_id = u.id
                             JOIN Классы k ON h.класс_id = k.id
                             ORDER BY h.срок_сдачи"""
                    cursor.execute(sql)
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка получения домашних заданий: {e}")
            return []
    
    def add_grade(self, student_id, subject_id, grade, date, grade_type, comment, teacher_id):
        try:
            with self.connection.cursor() as cursor:
                sql = """INSERT INTO Оценки (ученик_id, предмет_id, оценка, дата, тип_оценки, комментарий, учитель_id)
                         VALUES (%s, %s, %s, %s, %s, %s, %s)"""
                cursor.execute(sql, (student_id, subject_id, grade, date, grade_type, comment, teacher_id))
                self.connection.commit()
                return True, "Оценка успешно добавлена"
        except Exception as e:
            return False, f"Ошибка добавления оценки: {str(e)}"
    
    def add_homework(self, subject_id, class_id, teacher_id, assignment, issue_date, due_date):
        try:
            with self.connection.cursor() as cursor:
                sql = """INSERT INTO Домашние_задания (предмет_id, класс_id, учитель_id, задание, дата_выдачи, срок_сдачи)
                         VALUES (%s, %s, %s, %s, %s, %s)"""
                cursor.execute(sql, (subject_id, class_id, teacher_id, assignment, issue_date, due_date))
                self.connection.commit()
                return True, "Домашнее задание успешно добавлено"
        except Exception as e:
            return False, f"Ошибка добавления задания: {str(e)}"
    
    def add_schedule(self, class_id, subject_id, teacher_id, day, start_time, end_time, classroom):
        try:
            with self.connection.cursor() as cursor:
                sql = """INSERT INTO Расписание (класс_id, предмет_id, учитель_id, день_недели, время_начала, время_окончания, кабинет)
                         VALUES (%s, %s, %s, %s, %s, %s, %s)"""
                cursor.execute(sql, (class_id, subject_id, teacher_id, day, start_time, end_time, classroom))
                self.connection.commit()
                return True, "Урок успешно добавлен в расписание"
        except Exception as e:
            return False, f"Ошибка добавления в расписание: {str(e)}"
    
    def add_subject(self, name, description, teacher_id):
        try:
            with self.connection.cursor() as cursor:
                sql = """INSERT INTO Предметы (название, описание, учитель_id)
                         VALUES (%s, %s, %s)"""
                cursor.execute(sql, (name, description, teacher_id))
                self.connection.commit()
                return True, "Предмет успешно добавлен"
        except Exception as e:
            return False, f"Ошибка добавления предмета: {str(e)}"
    
    def add_class(self, name, year, class_teacher_id):
        try:
            with self.connection.cursor() as cursor:
                sql = """INSERT INTO Классы (название, год_обучения, классный_руководитель_id)
                         VALUES (%s, %s, %s)"""
                cursor.execute(sql, (name, year, class_teacher_id))
                self.connection.commit()
                return True, "Класс успешно добавлен"
        except Exception as e:
            return False, f"Ошибка добавления класса: {str(e)}"
    
    def update_user(self, user_id, **kwargs):
        try:
            with self.connection.cursor() as cursor:
                set_clause = ", ".join([f"{key} = %s" for key in kwargs.keys()])
                sql = f"UPDATE Пользователи SET {set_clause} WHERE id = %s"
                values = list(kwargs.values()) + [user_id]
                cursor.execute(sql, tuple(values))
                self.connection.commit()
                return True
        except Exception as e:
            print(f"Ошибка обновления пользователя: {e}")
            return False
    
    def delete_user(self, user_id):
        try:
            with self.connection.cursor() as cursor:
                sql = "DELETE FROM Пользователи WHERE id = %s"
                cursor.execute(sql, (user_id,))
                self.connection.commit()
                return True
        except Exception as e:
            print(f"Ошибка удаления пользователя: {e}")
            return False
    
    def delete_grade(self, grade_id):
        try:
            with self.connection.cursor() as cursor:
                sql = "DELETE FROM Оценки WHERE id = %s"
                cursor.execute(sql, (grade_id,))
                self.connection.commit()
                return True
        except Exception as e:
            print(f"Ошибка удаления оценки: {e}")
            return False
    
    def delete_homework(self, homework_id):
        try:
            with self.connection.cursor() as cursor:
                sql = "DELETE FROM Домашние_задания WHERE id = %s"
                cursor.execute(sql, (homework_id,))
                self.connection.commit()
                return True
        except Exception as e:
            print(f"Ошибка удаления задания: {e}")
            return False
    
    def delete_schedule(self, schedule_id):
        try:
            with self.connection.cursor() as cursor:
                sql = "DELETE FROM Расписание WHERE id = %s"
                cursor.execute(sql, (schedule_id,))
                self.connection.commit()
                return True
        except Exception as e:
            print(f"Ошибка удаления из расписания: {e}")
            return False
    
    def get_statistics(self):
        try:
            with self.connection.cursor() as cursor:
                # Общая статистика
                stats = {}
                
                # Количество пользователей по ролям
                sql = "SELECT роль, COUNT(*) as количество FROM Пользователи GROUP BY роль"
                cursor.execute(sql)
                stats['users_by_role'] = cursor.fetchall()
                
                # Средние оценки по предметам
                sql = """SELECT p.название as предмет, AVG(o.оценка) as средняя_оценка 
                         FROM Оценки o 
                         JOIN Предметы p ON o.предмет_id = p.id 
                         GROUP BY p.id"""
                cursor.execute(sql)
                stats['avg_grades_by_subject'] = cursor.fetchall()
                
                # Количество домашних заданий по классам
                sql = """SELECT k.название as класс, COUNT(h.id) as количество_заданий 
                         FROM Домашние_задания h 
                         JOIN Классы k ON h.класс_id = k.id 
                         GROUP BY k.id"""
                cursor.execute(sql)
                stats['homework_by_class'] = cursor.fetchall()
                
                return stats
        except Exception as e:
            print(f"Ошибка получения статистики: {e}")
            return {}

class LoginWindow:
    def __init__(self, root, db_manager):
        self.root = root
        self.db = db_manager
        self.login_attempts = 0
        self.current_user = None
        self.captcha = None
        
        self.setup_login_window()
    
    def setup_login_window(self):
        self.root.title("Авторизация - Управление учебным процессом")
        self.root.geometry("600x600")
        
        # Основной фрейм
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        title_label = ttk.Label(main_frame, text="Авторизация в системе", 
                               font=("Arial", 18, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Поля ввода
        input_frame = ttk.LabelFrame(main_frame, text="Учетные данные", padding="15")
        input_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(input_frame, text="Логин:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=8)
        self.username_entry = ttk.Entry(input_frame, width=30, font=("Arial", 10))
        self.username_entry.grid(row=0, column=1, pady=8, padx=10)
        
        ttk.Label(input_frame, text="Пароль:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=8)
        self.password_entry = ttk.Entry(input_frame, width=30, show="*", font=("Arial", 10))
        self.password_entry.grid(row=1, column=1, pady=8, padx=10)
        
        # Фрейм для цифровой капчи
        captcha_frame = ttk.LabelFrame(main_frame, text="Введите код с картинки", padding="15")
        captcha_frame.pack(fill=tk.X, pady=10)
        
        # Создаем капчу
        self.captcha = DigitalCaptcha()
        
        # Отображаем капчу
        self.captcha_label = ttk.Label(captcha_frame, 
                               text=self.captcha.get_captcha_display_text(),
                               font=("Courier", 24, "bold"),
                               foreground="blue",
                               background="lightgray",
                               relief="solid",
                               padding=10)
        self.captcha_label.pack(pady=10)
        
        # Кнопка обновления капчи
        ttk.Button(captcha_frame, text="Обновить код", 
                  command=self.refresh_captcha).pack(pady=5)
        
        # Поле для ввода капчи
        ttk.Label(captcha_frame, text="Введите код (6 цифр):").pack(pady=5)
        self.captcha_entry = ttk.Entry(captcha_frame, width=20, font=("Arial", 12), justify="center")
        self.captcha_entry.pack(pady=5)
        
        # Кнопка входа
        login_button = ttk.Button(main_frame, text="Войти", command=self.login, 
                                 style="Accent.TButton")
        login_button.pack(pady=20)
        
        # Стили
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Arial", 10, "bold"), padding=10)
    
    def refresh_captcha(self):
        """Обновляет цифровую капчу"""
        self.captcha.generate_captcha()
        self.captcha_label.config(text=self.captcha.get_captcha_display_text())
        self.captcha_entry.delete(0, tk.END)
    
    def login(self):
        """Обработка входа"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showwarning("Ошибка", "Пожалуйста, заполните все поля")
            return
        
        # Проверка капчи
        user_captcha_input = self.captcha_entry.get().strip()
        if not self.captcha.check_solution(user_captcha_input):
            self.login_attempts += 1
            if self.login_attempts >= 3:
                # Блокировка учетной записи
                self.db.update_login_attempts(username, self.login_attempts, blocked=True)
                messagebox.showerror("Ошибка", 
                    "Вы заблокированы. Обратитесь к администратору")
                return
            else:
                messagebox.showerror("Ошибка", 
                    f"Неверный код с картинки. Осталось попыток: {3 - self.login_attempts}")
                self.refresh_captcha()  # Обновляем капчу
                return
        
        # Проверка учетных данных
        user = self.db.authenticate_user(username, password)
        
        if user:
            if user['блокирован']:
                messagebox.showerror("Ошибка", 
                    "Вы заблокированы. Обратитесь к администратору")
                return
            
            # Сброс счетчика попыток при успешном входе
            self.db.update_login_attempts(username, 0)
            
            self.current_user = user
            messagebox.showinfo("Успех", "Вы успешно авторизовались")
            
            # Закрываем окно авторизации и открываем главное
            self.root.destroy()
            
            # Открываем главное окно в зависимости от роли
            root_main = tk.Tk()
            if user['роль'] == 'Администратор':
                AdminWindow(root_main, self.db, user)
            elif user['роль'] == 'Учитель':
                TeacherWindow(root_main, self.db, user)
            else:
                StudentWindow(root_main, self.db, user)
            root_main.mainloop()
            
        else:
            self.login_attempts += 1
            if self.login_attempts >= 3:
                # Блокировка учетной записи
                self.db.update_login_attempts(username, self.login_attempts, blocked=True)
                messagebox.showerror("Ошибка", 
                    "Вы заблокированы. Обратитесь к администратору")
            else:
                messagebox.showerror("Ошибка", 
                    f"Вы ввели неверный логин или пароль. Осталось попыток: {3 - self.login_attempts}")
                self.refresh_captcha()  # Обновляем капчу при ошибке

class MainWindow:
    def __init__(self, root, db_manager, user):
        self.root = root
        self.db = db_manager
        self.user = user
        
        self.root.title(f"Управление учебным процессом - {self.user['полное_имя']}")
        self.root.geometry("1200x700")
        
        # Создание меню
        self.create_menu()
        
        # Заголовок
        self.create_header()
        
        # Основное содержимое
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Статус бар
        self.create_status_bar()
    
    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Выйти", command=self.root.quit)
        
        if self.user['роль'] in ['Администратор', 'Учитель']:
            admin_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Администрирование", menu=admin_menu)
            admin_menu.add_command(label="Экспорт данных", command=self.export_data)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Помощь", menu=help_menu)
        help_menu.add_command(label="О программе", command=self.show_about)
    
    def create_header(self):
        header_frame = ttk.Frame(self.root, relief="raised", padding="10")
        header_frame.pack(fill=tk.X)
        
        title_label = ttk.Label(header_frame, 
                               text=f"Система управления учебным процессом",
                               font=("Arial", 16, "bold"))
        title_label.pack(side=tk.LEFT)
        
        user_info_label = ttk.Label(header_frame, 
                                   text=f"{self.user['полное_имя']} ({self.user['роль']})",
                                   font=("Arial", 10))
        user_info_label.pack(side=tk.RIGHT)
    
    def create_status_bar(self):
        status_bar = ttk.Frame(self.root, relief="sunken", padding="5")
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_label = ttk.Label(status_bar, text=f"Текущее время: {current_time}")
        status_label.pack(side=tk.LEFT)
    
    def export_data(self):
        # Базовый метод для экспорта
        messagebox.showinfo("Экспорт", "Функция экспорта данных")
    
    def show_about(self):
        about_text = """
        Система управления учебным процессом
        Версия 1.0
        
        Функции:
        - Управление пользователями
        - Управление классами и предметами
        - Расписание уроков
        - Выставление оценок
        - Домашние задания
        - Статистика и отчеты
        
        Разработчик: Школьная информационная система
        """
        messagebox.showinfo("О программе", about_text)

class AdminWindow(MainWindow):
    def __init__(self, root, db_manager, user):
        super().__init__(root, db_manager, user)
        self.setup_admin_interface()
    
    def setup_admin_interface(self):
        # Панель навигации
        nav_frame = ttk.Frame(self.main_frame)
        nav_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        
        buttons = [
            ("👥 Управление пользователями", self.manage_users),
            ("🏫 Управление классами", self.manage_classes),
            ("📚 Управление предметами", self.manage_subjects),
            ("📅 Расписание", self.manage_schedule),
            ("📊 Статистика", self.view_statistics),
            ("📈 Отчеты", self.generate_reports),
            ("⚙️ Настройки системы", self.system_settings),
        ]
        
        for text, command in buttons:
            btn = ttk.Button(nav_frame, text=text, command=command, width=25)
            btn.pack(pady=5, fill=tk.X)
        
        # Основная область
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Показать начальный экран
        self.show_dashboard()
    
    def show_dashboard(self):
        self.clear_content()
        
        title_label = ttk.Label(self.content_frame, 
                               text="Панель администратора",
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=20)
        
        # Быстрая статистика
        stats_frame = ttk.LabelFrame(self.content_frame, text="Быстрая статистика", padding="10")
        stats_frame.pack(fill=tk.X, pady=10)
        
        stats = self.db.get_statistics()
        
        if stats:
            col_frame = ttk.Frame(stats_frame)
            col_frame.pack(fill=tk.X)
            
            # Пользователи по ролям
            users_text = "Пользователи:\n"
            for item in stats.get('users_by_role', []):
                users_text += f"{item['роль']}: {item['количество']}\n"
            
            ttk.Label(col_frame, text=users_text, justify=tk.LEFT).pack(side=tk.LEFT, padx=20)
            
            # Средние оценки
            grades_text = "Средние оценки:\n"
            for item in stats.get('avg_grades_by_subject', []):
                grades_text += f"{item['предмет']}: {item['средняя_оценка']:.2f}\n"
            
            ttk.Label(col_frame, text=grades_text, justify=tk.LEFT).pack(side=tk.LEFT, padx=20)
        
        # Быстрые действия
        actions_frame = ttk.LabelFrame(self.content_frame, text="Быстрые действия", padding="10")
        actions_frame.pack(fill=tk.X, pady=10)
        
        quick_buttons_frame = ttk.Frame(actions_frame)
        quick_buttons_frame.pack()
        
        quick_buttons = [
            ("➕ Добавить пользователя", lambda: self.add_user_dialog()),
            ("➕ Добавить класс", lambda: self.add_class_dialog()),
            ("📋 Просмотреть отчет", lambda: self.generate_reports()),
        ]
        
        for text, command in quick_buttons:
            ttk.Button(quick_buttons_frame, text=text, command=command).pack(side=tk.LEFT, padx=5)
    
    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def manage_users(self):
        self.clear_content()
        
        title_label = ttk.Label(self.content_frame, 
                               text="Управление пользователями",
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # Панель инструментов
        toolbar = ttk.Frame(self.content_frame)
        toolbar.pack(fill=tk.X, pady=10)
        
        ttk.Button(toolbar, text="Добавить пользователя", 
                  command=self.add_user_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Обновить", 
                  command=lambda: self.refresh_user_list(tree)).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Экспорт в Excel", 
                  command=lambda: self.export_users_to_excel()).pack(side=tk.LEFT, padx=5)
        
        # Таблица пользователей
        table_frame = ttk.Frame(self.content_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("ID", "Логин", "Роль", "Полное имя", "Email", "Класс", "Блокирован")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended")
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        tree.column("ID", width=50)
        tree.column("Полное имя", width=150)
        
        # Полоса прокрутки
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Загрузка данных
        self.refresh_user_list(tree)
        
        # Контекстное меню
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="Разблокировать", 
                                command=lambda: self.unblock_selected_users(tree))
        context_menu.add_command(label="Изменить роль", 
                                command=lambda: self.change_role_dialog(tree))
        context_menu.add_command(label="Сбросить пароль", 
                                command=lambda: self.reset_password_dialog(tree))
        context_menu.add_separator()
        context_menu.add_command(label="Удалить", 
                                command=lambda: self.delete_selected_users(tree))
        
        tree.bind("<Button-3>", lambda e: context_menu.tk_popup(e.x_root, e.y_root))
    
    def refresh_user_list(self, tree):
        for item in tree.get_children():
            tree.delete(item)
        
        users = self.db.get_all_users()
        for user in users:
            tree.insert("", tk.END, values=(
                user['id'],
                user['логин'],
                user['роль'],
                user['полное_имя'],
                user['email'],
                user.get('класс_название', ''),
                "Да" if user['блокирован'] else "Нет"
            ))
    
    def add_user_dialog(self, parent_window=None):
        dialog = tk.Toplevel(parent_window or self.root)
        dialog.title("Добавить нового пользователя")
        dialog.geometry("500x550")
        dialog.transient(parent_window or self.root)
        dialog.grab_set()
        
        form_frame = ttk.Frame(dialog, padding="20")
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Логин
        ttk.Label(form_frame, text="Логин *:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=8)
        login_entry = ttk.Entry(form_frame, width=30)
        login_entry.grid(row=0, column=1, pady=8, padx=10)
        
        # Пароль
        ttk.Label(form_frame, text="Пароль *:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=8)
        password_entry = ttk.Entry(form_frame, width=30, show="*")
        password_entry.grid(row=1, column=1, pady=8, padx=10)
        
        # Подтверждение пароля
        ttk.Label(form_frame, text="Подтверждение пароля *:", font=("Arial", 10)).grid(row=2, column=0, sticky=tk.W, pady=8)
        confirm_entry = ttk.Entry(form_frame, width=30, show="*")
        confirm_entry.grid(row=2, column=1, pady=8, padx=10)
        
        # Роль
        ttk.Label(form_frame, text="Роль *:", font=("Arial", 10)).grid(row=3, column=0, sticky=tk.W, pady=8)
        role_var = tk.StringVar(value="Ученик")
        role_combo = ttk.Combobox(form_frame, textvariable=role_var, 
                                 values=["Администратор", "Учитель", "Ученик"], width=27)
        role_combo.grid(row=3, column=1, pady=8, padx=10)
        
        # Полное имя
        ttk.Label(form_frame, text="Полное имя *:", font=("Arial", 10)).grid(row=4, column=0, sticky=tk.W, pady=8)
        name_entry = ttk.Entry(form_frame, width=30)
        name_entry.grid(row=4, column=1, pady=8, padx=10)
        
        # Email
        ttk.Label(form_frame, text="Email:", font=("Arial", 10)).grid(row=5, column=0, sticky=tk.W, pady=8)
        email_entry = ttk.Entry(form_frame, width=30)
        email_entry.grid(row=5, column=1, pady=8, padx=10)
        
        # Телефон
        ttk.Label(form_frame, text="Телефон:", font=("Arial", 10)).grid(row=6, column=0, sticky=tk.W, pady=8)
        phone_entry = ttk.Entry(form_frame, width=30)
        phone_entry.grid(row=6, column=1, pady=8, padx=10)
        
        # Класс (для учеников)
        ttk.Label(form_frame, text="Класс:", font=("Arial", 10)).grid(row=7, column=0, sticky=tk.W, pady=8)
        class_var = tk.StringVar()
        classes = self.db.get_classes()
        class_names = [cls['название'] for cls in classes]
        class_combo = ttk.Combobox(form_frame, textvariable=class_var, 
                                  values=class_names, width=27)
        class_combo.grid(row=7, column=1, pady=8, padx=10)
        
        def add_user():
            username = login_entry.get().strip()
            password = password_entry.get().strip()
            confirm_password = confirm_entry.get().strip()
            role = role_var.get()
            full_name = name_entry.get().strip()
            email = email_entry.get().strip()
            phone = phone_entry.get().strip()
            
            if not all([username, password, full_name]):
                messagebox.showwarning("Ошибка", "Заполните все обязательные поля (*)")
                return
            
            if password != confirm_password:
                messagebox.showwarning("Ошибка", "Пароли не совпадают")
                return
            
            if len(password) < 6:
                messagebox.showwarning("Ошибка", "Пароль должен содержать минимум 6 символов")
                return
            
            # Определяем ID класса
            class_id = None
            if role == 'Ученик' and class_var.get():
                for cls in classes:
                    if cls['название'] == class_var.get():
                        class_id = cls['id']
                        break
            
            success, message = self.db.register_user(username, password, role, full_name, email, phone, class_id)
            if success:
                messagebox.showinfo("Успех", message)
                dialog.destroy()
                # Обновляем список пользователей если открыт
                for widget in self.content_frame.winfo_children():
                    if isinstance(widget, ttk.Treeview):
                        self.refresh_user_list(widget)
            else:
                messagebox.showerror("Ошибка", message)
        
        # Кнопки
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=8, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Добавить", command=add_user, width=15).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Отмена", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=10)
    
    def unblock_selected_users(self, tree):
        selected_items = tree.selection()
        if not selected_items:
            messagebox.showwarning("Ошибка", "Выберите пользователей для разблокировки")
            return
        
        for item in selected_items:
            user_id = tree.item(item)['values'][0]
            username = tree.item(item)['values'][1]
            
            if self.db.update_user(user_id, блокирован=False):
                self.db.update_user(user_id, попытки_входа=0)
        
        messagebox.showinfo("Успех", "Пользователи разблокированы")
        self.refresh_user_list(tree)
    
    def change_role_dialog(self, tree):
        selected_items = tree.selection()
        if not selected_items:
            messagebox.showwarning("Ошибка", "Выберите пользователей для изменения роли")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Изменение роли")
        dialog.geometry("300x200")
        
        ttk.Label(dialog, text="Выберите новую роль:", padding="20").pack()
        
        role_var = tk.StringVar(value="Ученик")
        role_combo = ttk.Combobox(dialog, textvariable=role_var, 
                                 values=["Администратор", "Учитель", "Ученик"])
        role_combo.pack(pady=10)
        
        def apply_role():
            new_role = role_var.get()
            for item in selected_items:
                user_id = tree.item(item)['values'][0]
                self.db.update_user(user_id, роль=new_role)
            
            messagebox.showinfo("Успех", "Роли изменены")
            dialog.destroy()
            self.refresh_user_list(tree)
        
        ttk.Button(dialog, text="Применить", command=apply_role).pack(pady=10)
    
    def reset_password_dialog(self, tree):
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showwarning("Ошибка", "Выберите пользователя")
            return
        
        user_id = tree.item(selected_item[0])['values'][0]
        username = tree.item(selected_item[0])['values'][1]
        
        new_password = simpledialog.askstring("Сброс пароля", 
                                            f"Введите новый пароль для {username}:",
                                            show="*")
        
        if new_password:
            if len(new_password) < 6:
                messagebox.showwarning("Ошибка", "Пароль должен содержать минимум 6 символов")
                return
            
            hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
            if self.db.update_user(user_id, пароль=hashed_password):
                messagebox.showinfo("Успех", "Пароль успешно изменен")
    
    def delete_selected_users(self, tree):
        selected_items = tree.selection()
        if not selected_items:
            messagebox.showwarning("Ошибка", "Выберите пользователей для удаления")
            return
        
        usernames = [tree.item(item)['values'][1] for item in selected_items]
        confirm = messagebox.askyesno("Подтверждение", 
                                     f"Вы уверены, что хотите удалить {len(usernames)} пользователей?\n"
                                     f"{', '.join(usernames[:3])}{'...' if len(usernames) > 3 else ''}")
        
        if confirm:
            for item in selected_items:
                user_id = tree.item(item)['values'][0]
                self.db.delete_user(user_id)
            
            messagebox.showinfo("Успех", "Пользователи удалены")
            self.refresh_user_list(tree)
    
    def export_users_to_excel(self):
        users = self.db.get_all_users()
        if not users:
            messagebox.showwarning("Ошибка", "Нет данных для экспорта")
            return
        
        # Создаем DataFrame
        data = []
        for user in users:
            data.append({
                'ID': user['id'],
                'Логин': user['логин'],
                'Роль': user['роль'],
                'Полное имя': user['полное_имя'],
                'Email': user['email'],
                'Телефон': user.get('телефон', ''),
                'Класс': user.get('класс_название', ''),
                'Блокирован': 'Да' if user['блокирован'] else 'Нет',
                'Дата создания': user['создан']
            })
        
        df = pd.DataFrame(data)
        
        # Сохраняем в файл
        file_path = fd.asksaveasfilename(defaultextension=".xlsx",
                                        filetypes=[("Excel files", "*.xlsx"),
                                                  ("All files", "*.*")])
        if file_path:
            df.to_excel(file_path, index=False)
            messagebox.showinfo("Успех", f"Данные экспортированы в {file_path}")
    
    def manage_classes(self):
        self.clear_content()
        
        title_label = ttk.Label(self.content_frame, 
                               text="Управление классами",
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # Панель инструментов
        toolbar = ttk.Frame(self.content_frame)
        toolbar.pack(fill=tk.X, pady=10)
        
        ttk.Button(toolbar, text="Добавить класс", 
                  command=self.add_class_dialog).pack(side=tk.LEFT, padx=5)
        
        # Таблица классов
        table_frame = ttk.Frame(self.content_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("ID", "Название", "Год обучения", "Классный руководитель")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        tree.column("Название", width=100)
        tree.column("Классный руководитель", width=200)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Загрузка данных
        classes = self.db.get_classes()
        for cls in classes:
            tree.insert("", tk.END, values=(
                cls['id'],
                cls['название'],
                cls['год_обучения'],
                cls.get('классный_руководитель', 'Не назначен')
            ))
    
    def add_class_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить новый класс")
        dialog.geometry("400x300")
        
        form_frame = ttk.Frame(dialog, padding="20")
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(form_frame, text="Название класса *:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=8)
        name_entry = ttk.Entry(form_frame, width=25)
        name_entry.grid(row=0, column=1, pady=8, padx=10)
        
        ttk.Label(form_frame, text="Год обучения *:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=8)
        year_entry = ttk.Entry(form_frame, width=25)
        year_entry.grid(row=1, column=1, pady=8, padx=10)
        
        ttk.Label(form_frame, text="Классный руководитель:", font=("Arial", 10)).grid(row=2, column=0, sticky=tk.W, pady=8)
        teacher_var = tk.StringVar()
        teachers = self.db.get_teachers()
        teacher_names = [f"{t['id']}: {t['полное_имя']}" for t in teachers]
        teacher_combo = ttk.Combobox(form_frame, textvariable=teacher_var, 
                                    values=teacher_names, width=22)
        teacher_combo.grid(row=2, column=1, pady=8, padx=10)
        
        def add_class():
            name = name_entry.get().strip()
            year = year_entry.get().strip()
            teacher = teacher_var.get()
            
            if not all([name, year]):
                messagebox.showwarning("Ошибка", "Заполните обязательные поля (*)")
                return
            
            try:
                year_int = int(year)
            except ValueError:
                messagebox.showwarning("Ошибка", "Год обучения должен быть числом")
                return
            
            teacher_id = None
            if teacher:
                teacher_id = int(teacher.split(":")[0])
            
            success, message = self.db.add_class(name, year_int, teacher_id)
            if success:
                messagebox.showinfo("Успех", message)
                dialog.destroy()
                self.manage_classes()  # Обновляем список
            else:
                messagebox.showerror("Ошибка", message)
        
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Добавить", command=add_class, width=15).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Отмена", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=10)
    
    def manage_subjects(self):
        self.clear_content()
        
        title_label = ttk.Label(self.content_frame, 
                               text="Управление предметами",
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        toolbar = ttk.Frame(self.content_frame)
        toolbar.pack(fill=tk.X, pady=10)
        
        ttk.Button(toolbar, text="Добавить предмет", 
                  command=self.add_subject_dialog).pack(side=tk.LEFT, padx=5)
        
        table_frame = ttk.Frame(self.content_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("ID", "Название", "Описание", "Учитель")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        for col in columns:
            tree.heading(col, text=col)
        
        tree.column("Название", width=150)
        tree.column("Описание", width=250)
        tree.column("Учитель", width=200)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        subjects = self.db.get_subjects()
        for subject in subjects:
            tree.insert("", tk.END, values=(
                subject['id'],
                subject['название'],
                subject.get('описание', ''),
                subject.get('учитель_имя', 'Не назначен')
            ))
    
    def add_subject_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить новый предмет")
        dialog.geometry("500x300")
        
        form_frame = ttk.Frame(dialog, padding="20")
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(form_frame, text="Название предмета *:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=8)
        name_entry = ttk.Entry(form_frame, width=30)
        name_entry.grid(row=0, column=1, pady=8, padx=10)
        
        ttk.Label(form_frame, text="Описание:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=8)
        desc_entry = tk.Text(form_frame, width=30, height=5)
        desc_entry.grid(row=1, column=1, pady=8, padx=10)
        
        ttk.Label(form_frame, text="Учитель:", font=("Arial", 10)).grid(row=2, column=0, sticky=tk.W, pady=8)
        teacher_var = tk.StringVar()
        teachers = self.db.get_teachers()
        teacher_names = [f"{t['id']}: {t['полное_имя']}" for t in teachers]
        teacher_combo = ttk.Combobox(form_frame, textvariable=teacher_var, 
                                    values=teacher_names, width=27)
        teacher_combo.grid(row=2, column=1, pady=8, padx=10)
        
        def add_subject():
            name = name_entry.get().strip()
            description = desc_entry.get("1.0", tk.END).strip()
            teacher = teacher_var.get()
            
            if not name:
                messagebox.showwarning("Ошибка", "Введите название предмета")
                return
            
            teacher_id = None
            if teacher:
                teacher_id = int(teacher.split(":")[0])
            
            success, message = self.db.add_subject(name, description, teacher_id)
            if success:
                messagebox.showinfo("Успех", message)
                dialog.destroy()
                self.manage_subjects()
            else:
                messagebox.showerror("Ошибка", message)
        
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Добавить", command=add_subject, width=15).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Отмена", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=10)
    
    def manage_schedule(self):
        self.clear_content()
        
        title_label = ttk.Label(self.content_frame, 
                               text="Управление расписанием",
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # Фильтры
        filter_frame = ttk.Frame(self.content_frame)
        filter_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(filter_frame, text="Класс:").pack(side=tk.LEFT, padx=5)
        class_var = tk.StringVar()
        classes = self.db.get_classes()
        class_names = [cls['название'] for cls in classes]
        class_combo = ttk.Combobox(filter_frame, textvariable=class_var, 
                                  values=class_names, width=15)
        class_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(filter_frame, text="Показать", 
                  command=lambda: self.load_schedule(tree, class_var.get())).pack(side=tk.LEFT, padx=5)
        ttk.Button(filter_frame, text="Добавить урок", 
                  command=self.add_schedule_dialog).pack(side=tk.LEFT, padx=5)
        
        # Таблица расписания
        table_frame = ttk.Frame(self.content_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("ID", "День недели", "Время", "Предмет", "Учитель", "Кабинет", "Класс")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        for col in columns:
            tree.heading(col, text=col)
        
        tree.column("День недели", width=120)
        tree.column("Время", width=100)
        tree.column("Предмет", width=150)
        tree.column("Учитель", width=150)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Загрузка всех расписаний
        self.load_schedule(tree)
        
        # Контекстное меню
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="Удалить урок", 
                                command=lambda: self.delete_schedule_item(tree))
        
        tree.bind("<Button-3>", lambda e: context_menu.tk_popup(e.x_root, e.y_root))
    
    def load_schedule(self, tree, class_name=None):
        for item in tree.get_children():
            tree.delete(item)
        
        if class_name:
            # Находим ID класса
            class_id = None
            classes = self.db.get_classes()
            for cls in classes:
                if cls['название'] == class_name:
                    class_id = cls['id']
                    break
            
            if class_id:
                schedule = self.db.get_schedule(class_id)
            else:
                schedule = []
        else:
            schedule = self.db.get_schedule()
        
        for item in schedule:
            time_str = f"{item['время_начала']} - {item['время_окончания']}"
            tree.insert("", tk.END, values=(
                item['id'],
                item['день_недели'],
                time_str,
                item['предмет'],
                item['учитель'],
                item['кабинет'],
                item['класс']
            ))
    
    def add_schedule_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить урок в расписание")
        dialog.geometry("500x450")
        
        form_frame = ttk.Frame(dialog, padding="20")
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Класс
        ttk.Label(form_frame, text="Класс *:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=8)
        class_var = tk.StringVar()
        classes = self.db.get_classes()
        class_names = [cls['название'] for cls in classes]
        class_combo = ttk.Combobox(form_frame, textvariable=class_var, 
                                  values=class_names, width=27)
        class_combo.grid(row=0, column=1, pady=8, padx=10)
        
        # Предмет
        ttk.Label(form_frame, text="Предмет *:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=8)
        subject_var = tk.StringVar()
        subjects = self.db.get_subjects()
        subject_names = [sub['название'] for sub in subjects]
        subject_combo = ttk.Combobox(form_frame, textvariable=subject_var, 
                                    values=subject_names, width=27)
        subject_combo.grid(row=1, column=1, pady=8, padx=10)
        
        # Учитель
        ttk.Label(form_frame, text="Учитель *:", font=("Arial", 10)).grid(row=2, column=0, sticky=tk.W, pady=8)
        teacher_var = tk.StringVar()
        teachers = self.db.get_teachers()
        teacher_names = [t['полное_имя'] for t in teachers]
        teacher_combo = ttk.Combobox(form_frame, textvariable=teacher_var, 
                                    values=teacher_names, width=27)
        teacher_combo.grid(row=2, column=1, pady=8, padx=10)
        
        # День недели
        ttk.Label(form_frame, text="День недели *:", font=("Arial", 10)).grid(row=3, column=0, sticky=tk.W, pady=8)
        day_var = tk.StringVar(value="Понедельник")
        day_combo = ttk.Combobox(form_frame, textvariable=day_var,
                                values=["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"],
                                width=27)
        day_combo.grid(row=3, column=1, pady=8, padx=10)
        
        # Время начала
        ttk.Label(form_frame, text="Время начала (ЧЧ:ММ) *:", font=("Arial", 10)).grid(row=4, column=0, sticky=tk.W, pady=8)
        start_entry = ttk.Entry(form_frame, width=27)
        start_entry.grid(row=4, column=1, pady=8, padx=10)
        start_entry.insert(0, "09:00")
        
        # Время окончания
        ttk.Label(form_frame, text="Время окончания (ЧЧ:ММ) *:", font=("Arial", 10)).grid(row=5, column=0, sticky=tk.W, pady=8)
        end_entry = ttk.Entry(form_frame, width=27)
        end_entry.grid(row=5, column=1, pady=8, padx=10)
        end_entry.insert(0, "09:45")
        
        # Кабинет
        ttk.Label(form_frame, text="Кабинет:", font=("Arial", 10)).grid(row=6, column=0, sticky=tk.W, pady=8)
        room_entry = ttk.Entry(form_frame, width=27)
        room_entry.grid(row=6, column=1, pady=8, padx=10)
        
        def add_schedule():
            class_name = class_var.get()
            subject_name = subject_var.get()
            teacher_name = teacher_var.get()
            day = day_var.get()
            start_time = start_entry.get().strip()
            end_time = end_entry.get().strip()
            room = room_entry.get().strip()
            
            if not all([class_name, subject_name, teacher_name, day, start_time, end_time]):
                messagebox.showwarning("Ошибка", "Заполните все обязательные поля (*)")
                return
            
            # Находим ID класса
            class_id = None
            for cls in classes:
                if cls['название'] == class_name:
                    class_id = cls['id']
                    break
            
            # Находим ID предмета
            subject_id = None
            for sub in subjects:
                if sub['название'] == subject_name:
                    subject_id = sub['id']
                    break
            
            # Находим ID учителя
            teacher_id = None
            for tch in teachers:
                if tch['полное_имя'] == teacher_name:
                    teacher_id = tch['id']
                    break
            
            success, message = self.db.add_schedule(class_id, subject_id, teacher_id, 
                                                   day, start_time, end_time, room)
            if success:
                messagebox.showinfo("Успех", message)
                dialog.destroy()
                self.manage_schedule()  # Обновляем расписание
            else:
                messagebox.showerror("Ошибка", message)
        
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Добавить", command=add_schedule, width=15).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Отмена", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=10)
    
    def delete_schedule_item(self, tree):
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showwarning("Ошибка", "Выберите урок для удаления")
            return
        
        schedule_id = tree.item(selected_item[0])['values'][0]
        
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить этот урок?"):
            if self.db.delete_schedule(schedule_id):
                messagebox.showinfo("Успех", "Урок удален из расписания")
                tree.delete(selected_item[0])
    
    def view_statistics(self):
        self.clear_content()
        
        title_label = ttk.Label(self.content_frame, 
                               text="Статистика учебного процесса",
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # Получаем статистику
        stats = self.db.get_statistics()
        
        # Пользователи по ролям
        if 'users_by_role' in stats:
            users_frame = ttk.LabelFrame(self.content_frame, text="Пользователи по ролям", padding="10")
            users_frame.pack(fill=tk.X, pady=10, padx=20)
            
            for item in stats['users_by_role']:
                row_frame = ttk.Frame(users_frame)
                row_frame.pack(fill=tk.X, pady=2)
                
                ttk.Label(row_frame, text=item['роль'], width=20, anchor=tk.W).pack(side=tk.LEFT)
                ttk.Label(row_frame, text=str(item['количество'])).pack(side=tk.LEFT)
        
        # Средние оценки
        if 'avg_grades_by_subject' in stats:
            grades_frame = ttk.LabelFrame(self.content_frame, text="Средние оценки по предметам", padding="10")
            grades_frame.pack(fill=tk.X, pady=10, padx=20)
            
            for item in stats['avg_grades_by_subject']:
                row_frame = ttk.Frame(grades_frame)
                row_frame.pack(fill=tk.X, pady=2)
                
                ttk.Label(row_frame, text=item['предмет'], width=30, anchor=tk.W).pack(side=tk.LEFT)
                ttk.Label(row_frame, text=f"{item['средняя_оценка']:.2f}").pack(side=tk.LEFT)
        
        # Домашние задания
        if 'homework_by_class' in stats:
            hw_frame = ttk.LabelFrame(self.content_frame, text="Домашние задания по классам", padding="10")
            hw_frame.pack(fill=tk.X, pady=10, padx=20)
            
            for item in stats['homework_by_class']:
                row_frame = ttk.Frame(hw_frame)
                row_frame.pack(fill=tk.X, pady=2)
                
                ttk.Label(row_frame, text=item['класс'], width=20, anchor=tk.W).pack(side=tk.LEFT)
                ttk.Label(row_frame, text=str(item['количество_заданий'])).pack(side=tk.LEFT)
    
    def generate_reports(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Генерация отчетов")
        dialog.geometry("400x300")
        
        ttk.Label(dialog, text="Выберите тип отчета:", padding="20").pack()
        
        reports_frame = ttk.Frame(dialog, padding="20")
        reports_frame.pack()
        
        report_types = [
            ("Отчет по успеваемости", self.generate_grades_report),
            ("Отчет по посещаемости", self.generate_attendance_report),
            ("Отчет по домашним заданиям", self.generate_homework_report),
            ("Общий отчет по классу", self.generate_class_report),
        ]
        
        for text, command in report_types:
            ttk.Button(reports_frame, text=text, command=command, width=30).pack(pady=5)
    
    def generate_grades_report(self):
        file_path = fd.asksaveasfilename(defaultextension=".xlsx",
                                        filetypes=[("Excel files", "*.xlsx"),
                                                  ("All files", "*.*")],
                                        title="Сохранить отчет по успеваемости")
        if file_path:
            # Здесь можно реализовать генерацию отчета
            messagebox.showinfo("Успех", f"Отчет будет сохранен в {file_path}")
    
    def generate_attendance_report(self):
        messagebox.showinfo("Информация", "Функция генерации отчета по посещаемости")
    
    def generate_homework_report(self):
        messagebox.showinfo("Информация", "Функция генерации отчета по домашним заданиям")
    
    def generate_class_report(self):
        messagebox.showinfo("Информация", "Функция генерации общего отчета по классу")
    
    def system_settings(self):
        self.clear_content()
        
        title_label = ttk.Label(self.content_frame, 
                               text="Настройки системы",
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=20)
        
        settings_frame = ttk.Frame(self.content_frame)
        settings_frame.pack(pady=20)
        
        settings = [
            ("Максимальное количество попыток входа:", "3"),
            ("Длительность блокировки (часы):", "24"),
            ("Минимальная длина пароля:", "6"),
        ]
        
        for i, (label, value) in enumerate(settings):
            ttk.Label(settings_frame, text=label).grid(row=i, column=0, sticky=tk.W, pady=10, padx=10)
            ttk.Entry(settings_frame, width=20).grid(row=i, column=1, pady=10, padx=10)
            ttk.Entry(settings_frame, width=10).insert(0, value)
        
        ttk.Button(settings_frame, text="Сохранить настройки", 
                  command=lambda: messagebox.showinfo("Успех", "Настройки сохранены")).grid(
                  row=len(settings), column=0, columnspan=2, pady=20)

class TeacherWindow(MainWindow):
    def __init__(self, root, db_manager, user):
        super().__init__(root, db_manager, user)
        self.setup_teacher_interface()
    
    def setup_teacher_interface(self):
        # Панель навигации
        nav_frame = ttk.Frame(self.main_frame)
        nav_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        
        buttons = [
            ("👨‍🎓 Мои ученики", self.view_my_students),
            ("📝 Выставление оценок", self.grade_students),
            ("📚 Мои предметы", self.view_my_subjects),
            ("📅 Мое расписание", self.view_my_schedule),
            ("🏠 Домашние задания", self.manage_homework),
            ("📊 Успеваемость", self.view_performance),
        ]
        
        for text, command in buttons:
            btn = ttk.Button(nav_frame, text=text, command=command, width=20)
            btn.pack(pady=5, fill=tk.X)
        
        # Основная область
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        self.show_teacher_dashboard()
    
    def show_teacher_dashboard(self):
        self.clear_content()
        
        title_label = ttk.Label(self.content_frame, 
                               text=f"Добро пожаловать, {self.user['полное_имя']}!",
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=20)
        
        # Сегодняшние уроки
        today_frame = ttk.LabelFrame(self.content_frame, text="Сегодняшние уроки", padding="10")
        today_frame.pack(fill=tk.X, pady=10, padx=20)
        
        # Здесь можно добавить логику получения сегодняшних уроков
        ttk.Label(today_frame, text="Сегодня уроков: 3").pack()
        
        # Ближайшие домашние задания
        hw_frame = ttk.LabelFrame(self.content_frame, text="Ближайшие сроки сдачи", padding="10")
        hw_frame.pack(fill=tk.X, pady=10, padx=20)
        
        # Быстрые действия
        actions_frame = ttk.LabelFrame(self.content_frame, text="Быстрые действия", padding="10")
        actions_frame.pack(fill=tk.X, pady=10, padx=20)
        
        quick_buttons_frame = ttk.Frame(actions_frame)
        quick_buttons_frame.pack()
        
        quick_buttons = [
            ("➕ Выставить оценку", self.grade_students),
            ("➕ Задать ДЗ", lambda: self.add_homework_dialog()),
            ("📋 Проверить ДЗ", self.check_homework),
        ]
        
        for text, command in quick_buttons:
            ttk.Button(quick_buttons_frame, text=text, command=command).pack(side=tk.LEFT, padx=5)
    
    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def view_my_students(self):
        self.clear_content()
        
        title_label = ttk.Label(self.content_frame, 
                               text="Мои ученики",
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # Получаем предметы учителя
        subjects = self.db.get_subjects()
        my_subjects = [sub for sub in subjects if sub.get('учитель_id') == self.user['id']]
        
        if not my_subjects:
            ttk.Label(self.content_frame, text="У вас нет назначенных предметов").pack(pady=20)
            return
        
        # Для каждого предмета показываем учеников
        for subject in my_subjects:
            subject_frame = ttk.LabelFrame(self.content_frame, text=subject['название'], padding="10")
            subject_frame.pack(fill=tk.X, pady=10, padx=20)
            
            # Здесь можно добавить логику получения учеников по предмету
            ttk.Label(subject_frame, text=f"Ученики, изучающие {subject['название']}").pack()
    
    def grade_students(self):
        self.clear_content()
        
        title_label = ttk.Label(self.content_frame, 
                               text="Выставление оценок",
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # Форма выставления оценки
        form_frame = ttk.LabelFrame(self.content_frame, text="Новая оценка", padding="15")
        form_frame.pack(fill=tk.X, pady=10, padx=20)
        
        ttk.Label(form_frame, text="Ученик:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=8)
        student_var = tk.StringVar()
        students = self.db.get_students()
        student_names = [f"{s['id']}: {s['полное_имя']} ({s.get('класс_название', '')})" for s in students]
        student_combo = ttk.Combobox(form_frame, textvariable=student_var, 
                                    values=student_names, width=40)
        student_combo.grid(row=0, column=1, pady=8, padx=10)
        
        ttk.Label(form_frame, text="Предмет:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=8)
        subject_var = tk.StringVar()
        subjects = self.db.get_subjects()
        subject_names = [sub['название'] for sub in subjects]
        subject_combo = ttk.Combobox(form_frame, textvariable=subject_var, 
                                    values=subject_names, width=40)
        subject_combo.grid(row=1, column=1, pady=8, padx=10)
        
        ttk.Label(form_frame, text="Оценка:", font=("Arial", 10)).grid(row=2, column=0, sticky=tk.W, pady=8)
        grade_var = tk.StringVar(value="5")
        grade_combo = ttk.Combobox(form_frame, textvariable=grade_var, 
                                  values=["5", "4", "3", "2", "1"], width=10)
        grade_combo.grid(row=2, column=1, sticky=tk.W, pady=8, padx=10)
        
        ttk.Label(form_frame, text="Тип оценки:", font=("Arial", 10)).grid(row=3, column=0, sticky=tk.W, pady=8)
        type_var = tk.StringVar(value="Устный ответ")
        type_combo = ttk.Combobox(form_frame, textvariable=type_var,
                                 values=["Контрольная", "Самостоятельная", "Домашняя работа", "Устный ответ", "Тест"],
                                 width=20)
        type_combo.grid(row=3, column=1, sticky=tk.W, pady=8, padx=10)
        
        ttk.Label(form_frame, text="Дата:", font=("Arial", 10)).grid(row=4, column=0, sticky=tk.W, pady=8)
        date_entry = ttk.Entry(form_frame, width=20)
        date_entry.grid(row=4, column=1, sticky=tk.W, pady=8, padx=10)
        date_entry.insert(0, datetime.datetime.now().strftime("%Y-%m-%d"))
        
        ttk.Label(form_frame, text="Комментарий:", font=("Arial", 10)).grid(row=5, column=0, sticky=tk.W, pady=8)
        comment_entry = tk.Text(form_frame, width=40, height=3)
        comment_entry.grid(row=5, column=1, pady=8, padx=10)
        
        def add_grade():
            student = student_var.get()
            subject = subject_var.get()
            grade = grade_var.get()
            grade_type = type_var.get()
            date = date_entry.get().strip()
            comment = comment_entry.get("1.0", tk.END).strip()
            
            if not all([student, subject, grade, date]):
                messagebox.showwarning("Ошибка", "Заполните все обязательные поля")
                return
            
            # Находим ID ученика
            student_id = int(student.split(":")[0])
            
            # Находим ID предмета
            subject_id = None
            for sub in subjects:
                if sub['название'] == subject:
                    subject_id = sub['id']
                    break
            
            success, message = self.db.add_grade(student_id, subject_id, int(grade), 
                                                date, grade_type, comment, self.user['id'])
            if success:
                messagebox.showinfo("Успех", message)
                # Очищаем форму
                student_var.set('')
                subject_var.set('')
                comment_entry.delete("1.0", tk.END)
            else:
                messagebox.showerror("Ошибка", message)
        
        ttk.Button(form_frame, text="Выставить оценку", command=add_grade).grid(row=6, column=0, columnspan=2, pady=20)
    
    def view_my_subjects(self):
        self.clear_content()
        
        title_label = ttk.Label(self.content_frame, 
                               text="Мои предметы",
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        subjects = self.db.get_subjects()
        my_subjects = [sub for sub in subjects if sub.get('учитель_id') == self.user['id']]
        
        if not my_subjects:
            ttk.Label(self.content_frame, text="У вас нет назначенных предметов").pack(pady=20)
            return
        
        for subject in my_subjects:
            subject_frame = ttk.LabelFrame(self.content_frame, padding="10")
            subject_frame.pack(fill=tk.X, pady=5, padx=20)
            
            ttk.Label(subject_frame, text=f"📚 {subject['название']}", 
                     font=("Arial", 11, "bold")).pack(anchor=tk.W)
            
            if subject.get('описание'):
                ttk.Label(subject_frame, text=subject['описание'], 
                         wraplength=600).pack(anchor=tk.W, pady=5)
    
    def view_my_schedule(self):
        self.clear_content()
        
        title_label = ttk.Label(self.content_frame, 
                               text="Мое расписание",
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # Получаем все расписание и фильтруем по учителю
        schedule = self.db.get_schedule()
        my_schedule = [item for item in schedule if item.get('учитель_id') == self.user['id']]
        
        if not my_schedule:
            ttk.Label(self.content_frame, text="У вас нет уроков в расписании").pack(pady=20)
            return
        
        # Группируем по дням недели
        days = {}
        for item in my_schedule:
            day = item['день_недели']
            if day not in days:
                days[day] = []
            days[day].append(item)
        
        # Сортируем дни
        day_order = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']
        
        for day in day_order:
            if day in days:
                day_frame = ttk.LabelFrame(self.content_frame, text=day, padding="10")
                day_frame.pack(fill=tk.X, pady=5, padx=20)
                
                # Сортируем уроки по времени
                lessons = sorted(days[day], key=lambda x: x['время_начала'])
                
                for lesson in lessons:
                    time_str = f"{lesson['время_начала']} - {lesson['время_окончания']}"
                    lesson_text = f"{time_str} | {lesson['предмет']} | {lesson['класс']} | Каб. {lesson['кабинет']}"
                    
                    ttk.Label(day_frame, text=lesson_text).pack(anchor=tk.W, pady=2)
    
    def manage_homework(self):
        self.clear_content()
        
        title_label = ttk.Label(self.content_frame, 
                               text="Домашние задания",
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        toolbar = ttk.Frame(self.content_frame)
        toolbar.pack(fill=tk.X, pady=10)
        
        ttk.Button(toolbar, text="Добавить задание", 
                  command=self.add_homework_dialog).pack(side=tk.LEFT, padx=5)
        
        # Получаем домашние задания
        homework = self.db.get_homework()
        my_homework = [hw for hw in homework if hw.get('учитель_id') == self.user['id']]
        
        if not my_homework:
            ttk.Label(self.content_frame, text="Нет домашних заданий").pack(pady=20)
            return
        
        for hw in my_homework:
            hw_frame = ttk.LabelFrame(self.content_frame, padding="10")
            hw_frame.pack(fill=tk.X, pady=5, padx=20)
            
            due_date = datetime.datetime.strptime(str(hw['срок_сдачи']), "%Y-%m-%d").strftime("%d.%m.%Y")
            hw_text = f"📝 {hw['предмет']} | Класс: {hw['класс']} | Срок: {due_date}"
            
            ttk.Label(hw_frame, text=hw_text, font=("Arial", 10, "bold")).pack(anchor=tk.W)
            ttk.Label(hw_frame, text=hw['задание'], wraplength=600).pack(anchor=tk.W, pady=5)
    
    def add_homework_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить домашнее задание")
        dialog.geometry("500x400")
        
        form_frame = ttk.Frame(dialog, padding="20")
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(form_frame, text="Предмет *:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=8)
        subject_var = tk.StringVar()
        subjects = self.db.get_subjects()
        my_subjects = [sub['название'] for sub in subjects if sub.get('учитель_id') == self.user['id']]
        subject_combo = ttk.Combobox(form_frame, textvariable=subject_var, 
                                    values=my_subjects, width=30)
        subject_combo.grid(row=0, column=1, pady=8, padx=10)
        
        ttk.Label(form_frame, text="Класс *:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=8)
        class_var = tk.StringVar()
        classes = self.db.get_classes()
        class_names = [cls['название'] for cls in classes]
        class_combo = ttk.Combobox(form_frame, textvariable=class_var, 
                                  values=class_names, width=30)
        class_combo.grid(row=1, column=1, pady=8, padx=10)
        
        ttk.Label(form_frame, text="Задание *:", font=("Arial", 10)).grid(row=2, column=0, sticky=tk.W, pady=8)
        assignment_entry = tk.Text(form_frame, width=30, height=5)
        assignment_entry.grid(row=2, column=1, pady=8, padx=10)
        
        ttk.Label(form_frame, text="Срок сдачи (ГГГГ-ММ-ДД) *:", font=("Arial", 10)).grid(row=3, column=0, sticky=tk.W, pady=8)
        due_entry = ttk.Entry(form_frame, width=30)
        due_entry.grid(row=3, column=1, pady=8, padx=10)
        due_entry.insert(0, (datetime.datetime.now() + datetime.timedelta(days=7)).strftime("%Y-%m-%d"))
        
        def add_homework():
            subject = subject_var.get()
            class_name = class_var.get()
            assignment = assignment_entry.get("1.0", tk.END).strip()
            due_date = due_entry.get().strip()
            
            if not all([subject, class_name, assignment, due_date]):
                messagebox.showwarning("Ошибка", "Заполните все обязательные поля (*)")
                return
            
            # Находим ID предмета
            subject_id = None
            for sub in subjects:
                if sub['название'] == subject:
                    subject_id = sub['id']
                    break
            
            # Находим ID класса
            class_id = None
            for cls in classes:
                if cls['название'] == class_name:
                    class_id = cls['id']
                    break
            
            issue_date = datetime.datetime.now().strftime("%Y-%m-%d")
            
            success, message = self.db.add_homework(subject_id, class_id, self.user['id'], 
                                                   assignment, issue_date, due_date)
            if success:
                messagebox.showinfo("Успех", message)
                dialog.destroy()
                self.manage_homework()
            else:
                messagebox.showerror("Ошибка", message)
        
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Добавить", command=add_homework, width=15).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Отмена", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=10)
    
    def check_homework(self):
        self.clear_content()
        
        title_label = ttk.Label(self.content_frame, 
                               text="Проверка домашних заданий",
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        ttk.Label(self.content_frame, text="Функция проверки домашних заданий в разработке").pack(pady=20)
    
    def view_performance(self):
        self.clear_content()
        
        title_label = ttk.Label(self.content_frame, 
                               text="Успеваемость учеников",
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # Выбираем предмет
        filter_frame = ttk.Frame(self.content_frame)
        filter_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(filter_frame, text="Предмет:").pack(side=tk.LEFT, padx=5)
        subject_var = tk.StringVar()
        subjects = self.db.get_subjects()
        my_subjects = [sub['название'] for sub in subjects if sub.get('учитель_id') == self.user['id']]
        subject_combo = ttk.Combobox(filter_frame, textvariable=subject_var, 
                                    values=my_subjects, width=20)
        subject_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(filter_frame, text="Показать", 
                  command=lambda: self.show_performance_for_subject(subject_var.get())).pack(side=tk.LEFT, padx=5)
        
        self.performance_frame = ttk.Frame(self.content_frame)
        self.performance_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        ttk.Label(self.performance_frame, text="Выберите предмет для просмотра успеваемости").pack(pady=50)
    
    def show_performance_for_subject(self, subject_name):
        for widget in self.performance_frame.winfo_children():
            widget.destroy()
        
        if not subject_name:
            ttk.Label(self.performance_frame, text="Выберите предмет").pack(pady=50)
            return
        
        # Находим ID предмета
        subject_id = None
        subjects = self.db.get_subjects()
        for sub in subjects:
            if sub['название'] == subject_name:
                subject_id = sub['id']
                break
        
        if not subject_id:
            ttk.Label(self.performance_frame, text="Предмет не найден").pack(pady=50)
            return
        
        # Получаем оценки по предмету
        grades = self.db.get_grades(subject_id=subject_id)
        
        if not grades:
            ttk.Label(self.performance_frame, text="Нет оценок по этому предмету").pack(pady=50)
            return
        
        # Группируем по ученикам
        students_grades = {}
        for grade in grades:
            student_name = grade['ученик']
            if student_name not in students_grades:
                students_grades[student_name] = []
            students_grades[student_name].append(grade)
        
        # Создаем таблицу
        table_frame = ttk.Frame(self.performance_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовки
        headers_frame = ttk.Frame(table_frame)
        headers_frame.pack(fill=tk.X)
        
        ttk.Label(headers_frame, text="Ученик", width=20, relief="solid").pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(headers_frame, text="Средний балл", width=10, relief="solid").pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(headers_frame, text="Кол-во оценок", width=10, relief="solid").pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Данные
        for student, student_grades in students_grades.items():
            row_frame = ttk.Frame(table_frame)
            row_frame.pack(fill=tk.X)
            
            avg_grade = sum(g['оценка'] for g in student_grades) / len(student_grades)
            count = len(student_grades)
            
            ttk.Label(row_frame, text=student, width=20, relief="solid").pack(side=tk.LEFT, fill=tk.X, expand=True)
            ttk.Label(row_frame, text=f"{avg_grade:.2f}", width=10, relief="solid").pack(side=tk.LEFT, fill=tk.X, expand=True)
            ttk.Label(row_frame, text=str(count), width=10, relief="solid").pack(side=tk.LEFT, fill=tk.X, expand=True)

class StudentWindow(MainWindow):
    def __init__(self, root, db_manager, user):
        super().__init__(root, db_manager, user)
        self.setup_student_interface()
    
    def setup_student_interface(self):
        # Панель навигации
        nav_frame = ttk.Frame(self.main_frame)
        nav_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        
        buttons = [
            ("📊 Мои оценки", self.view_my_grades),
            ("📅 Мое расписание", self.view_my_schedule),
            ("🏠 Домашние задания", self.view_my_homework),
            ("📈 Успеваемость", self.view_my_performance),
            ("👨‍🏫 Мои учителя", self.view_my_teachers),
        ]
        
        for text, command in buttons:
            btn = ttk.Button(nav_frame, text=text, command=command, width=20)
            btn.pack(pady=5, fill=tk.X)
        
        # Основная область
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        self.show_student_dashboard()
    
    def show_student_dashboard(self):
        self.clear_content()
        
        title_label = ttk.Label(self.content_frame, 
                               text=f"Добро пожаловать, {self.user['полное_имя']}!",
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=20)
        
        # Быстрая информация
        info_frame = ttk.LabelFrame(self.content_frame, text="Моя информация", padding="10")
        info_frame.pack(fill=tk.X, pady=10, padx=20)
        
        # Класс ученика
        ttk.Label(info_frame, text=f"Класс: {self.user.get('класс_название', 'Не указан')}", 
                 font=("Arial", 10)).pack(anchor=tk.W, pady=2)
        
        # Сегодняшние уроки
        today_frame = ttk.LabelFrame(self.content_frame, text="Сегодняшние уроки", padding="10")
        today_frame.pack(fill=tk.X, pady=10, padx=20)
        
        # Здесь можно добавить логику получения сегодняшних уроков
        today = datetime.datetime.now().strftime("%A")
        days_ru = {
            'Monday': 'Понедельник',
            'Tuesday': 'Вторник',
            'Wednesday': 'Среда',
            'Thursday': 'Четверг',
            'Friday': 'Пятница',
            'Saturday': 'Суббота',
            'Sunday': 'Воскресенье'
        }
        today_ru = days_ru.get(today, today)
        
        if self.user.get('класс_id'):
            schedule = self.db.get_schedule(self.user['класс_id'])
            today_lessons = [lesson for lesson in schedule if lesson['день_недели'] == today_ru]
            
            if today_lessons:
                for lesson in today_lessons:
                    time_str = f"{lesson['время_начала']} - {lesson['время_окончания']}"
                    lesson_text = f"{time_str} | {lesson['предмет']} | Каб. {lesson['кабинет']}"
                    ttk.Label(today_frame, text=lesson_text).pack(anchor=tk.W, pady=2)
            else:
                ttk.Label(today_frame, text="Сегодня уроков нет").pack()
        else:
            ttk.Label(today_frame, text="Класс не указан").pack()
        
        # Ближайшие домашние задания
        hw_frame = ttk.LabelFrame(self.content_frame, text="Ближайшие домашние задания", padding="10")
        hw_frame.pack(fill=tk.X, pady=10, padx=20)
        
        if self.user.get('класс_id'):
            homework = self.db.get_homework(student_id=self.user['id'])
            
            if homework:
                # Сортируем по сроку сдачи
                homework_sorted = sorted(homework, key=lambda x: x['срок_сдачи'])
                
                for hw in homework_sorted[:3]:  # Показываем 3 ближайших
                    due_date = datetime.datetime.strptime(str(hw['срок_сдачи']), "%Y-%m-%d").strftime("%d.%m.%Y")
                    status = hw.get('статус_сдачи', 'Не сдано')
                    status_color = "green" if status == 'Сдано' else "red" if status == 'Просрочено' else "black"
                    
                    hw_text = f"{hw['предмет']} | Срок: {due_date} | Статус: {status}"
                    label = ttk.Label(hw_frame, text=hw_text)
                    label.pack(anchor=tk.W, pady=2)
            else:
                ttk.Label(hw_frame, text="Нет домашних заданий").pack()
        else:
            ttk.Label(hw_frame, text="Класс не указан").pack()
    
    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def view_my_grades(self):
        self.clear_content()
        
        title_label = ttk.Label(self.content_frame, 
                               text="Мои оценки",
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # Фильтр по предметам
        filter_frame = ttk.Frame(self.content_frame)
        filter_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(filter_frame, text="Предмет:").pack(side=tk.LEFT, padx=5)
        subject_var = tk.StringVar(value="Все предметы")
        subjects = self.db.get_subjects()
        subject_names = ["Все предметы"] + [sub['название'] for sub in subjects]
        subject_combo = ttk.Combobox(filter_frame, textvariable=subject_var, 
                                    values=subject_names, width=20)
        subject_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(filter_frame, text="Показать", 
                  command=lambda: self.load_student_grades(subject_var.get())).pack(side=tk.LEFT, padx=5)
        
        # Область для отображения оценок
        self.grades_frame = ttk.Frame(self.content_frame)
        self.grades_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Загружаем все оценки по умолчанию
        self.load_student_grades("Все предметы")
    
    def load_student_grades(self, subject_filter):
        for widget in self.grades_frame.winfo_children():
            widget.destroy()
        
        # Получаем оценки
        if subject_filter == "Все предметы":
            grades = self.db.get_grades(student_id=self.user['id'])
        else:
            # Находим ID предмета
            subject_id = None
            subjects = self.db.get_subjects()
            for sub in subjects:
                if sub['название'] == subject_filter:
                    subject_id = sub['id']
                    break
            
            if subject_id:
                grades = self.db.get_grades(student_id=self.user['id'], subject_id=subject_id)
            else:
                grades = []
        
        if not grades:
            ttk.Label(self.grades_frame, text="Нет оценок").pack(pady=50)
            return
        
        # Группируем по предметам
        subjects_grades = {}
        for grade in grades:
            subject_name = grade['предмет']
            if subject_name not in subjects_grades:
                subjects_grades[subject_name] = []
            subjects_grades[subject_name].append(grade)
        
        # Отображаем оценки по предметам
        for subject, subject_grades in subjects_grades.items():
            subject_frame = ttk.LabelFrame(self.grades_frame, text=subject, padding="10")
            subject_frame.pack(fill=tk.X, pady=5, padx=20)
            
            # Средний балл по предмету
            avg_grade = sum(g['оценка'] for g in subject_grades) / len(subject_grades)
            ttk.Label(subject_frame, text=f"Средний балл: {avg_grade:.2f}", 
                     font=("Arial", 10, "bold")).pack(anchor=tk.W)
            
            # Таблица оценок
            table_frame = ttk.Frame(subject_frame)
            table_frame.pack(fill=tk.X, pady=5)
            
            # Заголовки
            headers = ["Дата", "Оценка", "Тип", "Учитель", "Комментарий"]
            for i, header in enumerate(headers):
                ttk.Label(table_frame, text=header, font=("Arial", 9, "bold"), 
                         relief="solid", width=15).grid(row=0, column=i, sticky="nsew", padx=1, pady=1)
            
            # Данные
            for row_idx, grade in enumerate(subject_grades, 1):
                date_str = datetime.datetime.strptime(str(grade['дата']), "%Y-%m-%d").strftime("%d.%m.%Y")
                values = [
                    date_str,
                    str(grade['оценка']),
                    grade['тип_оценки'],
                    grade['учитель_имя'],
                    grade.get('комментарий', '')[:30] + "..." if len(grade.get('комментарий', '')) > 30 else grade.get('комментарий', '')
                ]
                
                for col_idx, value in enumerate(values):
                    ttk.Label(table_frame, text=value, relief="solid", 
                             width=15, wraplength=150).grid(row=row_idx, column=col_idx, 
                                                           sticky="nsew", padx=1, pady=1)
    
    def view_my_schedule(self):
        self.clear_content()
        
        title_label = ttk.Label(self.content_frame, 
                               text="Мое расписание",
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        if not self.user.get('класс_id'):
            ttk.Label(self.content_frame, text="Класс не указан").pack(pady=20)
            return
        
        # Получаем расписание для класса
        schedule = self.db.get_schedule(self.user['класс_id'])
        
        if not schedule:
            ttk.Label(self.content_frame, text="Расписание не составлено").pack(pady=20)
            return
        
        # Группируем по дням недели
        days = {}
        for item in schedule:
            day = item['день_недели']
            if day not in days:
                days[day] = []
            days[day].append(item)
        
        # Сортируем дни
        day_order = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']
        
        for day in day_order:
            if day in days:
                day_frame = ttk.LabelFrame(self.content_frame, text=day, padding="10")
                day_frame.pack(fill=tk.X, pady=5, padx=20)
                
                # Сортируем уроки по времени
                lessons = sorted(days[day], key=lambda x: x['время_начала'])
                
                for lesson in lessons:
                    time_str = f"{lesson['время_начала']} - {lesson['время_окончания']}"
                    lesson_text = f"{time_str} | {lesson['предмет']} | {lesson['учитель']} | Каб. {lesson['кабинет']}"
                    
                    ttk.Label(day_frame, text=lesson_text).pack(anchor=tk.W, pady=2)
    
    def view_my_homework(self):
        self.clear_content()
        
        title_label = ttk.Label(self.content_frame, 
                               text="Мои домашние задания",
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        if not self.user.get('класс_id'):
            ttk.Label(self.content_frame, text="Класс не указан").pack(pady=20)
            return
        
        # Получаем домашние задания
        homework = self.db.get_homework(student_id=self.user['id'])
        
        if not homework:
            ttk.Label(self.content_frame, text="Нет домашних заданий").pack(pady=20)
            return
        
        # Сортируем по сроку сдачи
        homework_sorted = sorted(homework, key=lambda x: x['срок_сдачи'])
        
        for hw in homework_sorted:
            hw_frame = ttk.LabelFrame(self.content_frame, padding="10")
            hw_frame.pack(fill=tk.X, pady=5, padx=20)
            
            # Информация о задании
            issue_date = datetime.datetime.strptime(str(hw['дата_выдачи']), "%Y-%m-%d").strftime("%d.%m.%Y")
            due_date = datetime.datetime.strptime(str(hw['срок_сдачи']), "%Y-%m-%d").strftime("%d.%m.%Y")
            status = hw.get('статус_сдачи', 'Не сдано')
            
            # Заголовок
            header_text = f"📝 {hw['предмет']} | Выдано: {issue_date} | Срок: {due_date} | Статус: {status}"
            ttk.Label(hw_frame, text=header_text, font=("Arial", 10, "bold")).pack(anchor=tk.W)
            
            # Задание
            ttk.Label(hw_frame, text="Задание:", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(5, 0))
            ttk.Label(hw_frame, text=hw['задание'], wraplength=600, justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 5))
            
            # Учитель
            ttk.Label(hw_frame, text=f"Учитель: {hw['учитель']}", font=("Arial", 9)).pack(anchor=tk.W)
    
    def view_my_performance(self):
        self.clear_content()
        
        title_label = ttk.Label(self.content_frame, 
                               text="Моя успеваемость",
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # Получаем все оценки
        grades = self.db.get_grades(student_id=self.user['id'])
        
        if not grades:
            ttk.Label(self.content_frame, text="Нет оценок").pack(pady=20)
            return
        
        # Группируем по предметам и вычисляем средние
        subjects_stats = {}
        for grade in grades:
            subject = grade['предмет']
            if subject not in subjects_stats:
                subjects_stats[subject] = {
                    'grades': [],
                    'count': 0,
                    'sum': 0
                }
            subjects_stats[subject]['grades'].append(grade['оценка'])
            subjects_stats[subject]['count'] += 1
            subjects_stats[subject]['sum'] += grade['оценка']
        
        # Выводим статистику
        stats_frame = ttk.LabelFrame(self.content_frame, text="Статистика по предметам", padding="15")
        stats_frame.pack(fill=tk.X, pady=10, padx=20)
        
        # Заголовки таблицы
        headers_frame = ttk.Frame(stats_frame)
        headers_frame.pack(fill=tk.X, pady=(0, 5))
        
        headers = ["Предмет", "Средний балл", "Кол-во оценок", "Лучшая оценка", "Худшая оценка"]
        for i, header in enumerate(headers):
            ttk.Label(headers_frame, text=header, font=("Arial", 9, "bold"), 
                     width=15).grid(row=0, column=i, padx=2, pady=2)
        
        # Данные
        for idx, (subject, stats) in enumerate(subjects_stats.items(), 1):
            avg = stats['sum'] / stats['count']
            best = max(stats['grades'])
            worst = min(stats['grades'])
            
            row_frame = ttk.Frame(stats_frame)
            row_frame.pack(fill=tk.X, pady=2)
            
            values = [subject, f"{avg:.2f}", str(stats['count']), str(best), str(worst)]
            for i, value in enumerate(values):
                ttk.Label(row_frame, text=value, width=15).grid(row=0, column=i, padx=2, pady=2)
        
        # Общая статистика
        total_avg = sum(grade['оценка'] for grade in grades) / len(grades)
        total_best = max(grade['оценка'] for grade in grades)
        total_worst = min(grade['оценка'] for grade in grades)
        
        total_frame = ttk.LabelFrame(self.content_frame, text="Общая статистика", padding="15")
        total_frame.pack(fill=tk.X, pady=10, padx=20)
        
        ttk.Label(total_frame, text=f"Общий средний балл: {total_avg:.2f}", 
                 font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=2)
        ttk.Label(total_frame, text=f"Лучшая оценка: {total_best}").pack(anchor=tk.W, pady=2)
        ttk.Label(total_frame, text=f"Худшая оценка: {total_worst}").pack(anchor=tk.W, pady=2)
        ttk.Label(total_frame, text=f"Всего оценок: {len(grades)}").pack(anchor=tk.W, pady=2)
    
    def view_my_teachers(self):
        self.clear_content()
        
        title_label = ttk.Label(self.content_frame, 
                               text="Мои учителя",
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        if not self.user.get('класс_id'):
            ttk.Label(self.content_frame, text="Класс не указан").pack(pady=20)
            return
        
        # Получаем расписание класса
        schedule = self.db.get_schedule(self.user['класс_id'])
        
        if not schedule:
            ttk.Label(self.content_frame, text="Расписание не составлено").pack(pady=20)
            return
        
        # Собираем уникальных учителей
        teachers = {}
        for lesson in schedule:
            teacher_name = lesson['учитель']
            subject = lesson['предмет']
            
            if teacher_name not in teachers:
                teachers[teacher_name] = []
            
            if subject not in teachers[teacher_name]:
                teachers[teacher_name].append(subject)
        
        if not teachers:
            ttk.Label(self.content_frame, text="Нет информации об учителях").pack(pady=20)
            return
        
        # Выводим список учителей
        for teacher, subjects in teachers.items():
            teacher_frame = ttk.LabelFrame(self.content_frame, padding="10")
            teacher_frame.pack(fill=tk.X, pady=5, padx=20)
            
            ttk.Label(teacher_frame, text=f"👨‍🏫 {teacher}", 
                     font=("Arial", 11, "bold")).pack(anchor=tk.W)
            ttk.Label(teacher_frame, text=f"Предметы: {', '.join(subjects)}").pack(anchor=tk.W, pady=5)

def main():
    root = tk.Tk()
    
    # Создаем менеджер базы данных
    db_manager = DatabaseManager()
    if not db_manager.connect():
        return
    
    # Создаем окно авторизации
    login_app = LoginWindow(root, db_manager)
    root.mainloop()

if __name__ == "__main__":
    main()