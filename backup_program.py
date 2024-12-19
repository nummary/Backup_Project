import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
from tkinter import ttk
from threading import Thread
from mega import Mega
from cryptography.fernet import Fernet
import os
import time

# 
# @module backup_program
# @brief GUI-программа для резервного копирования файлов, шифрования, загрузки в MEGA и восстановления.
#

# Глобальные переменные
backup_process_active = False # Флаг для контроля процесса резервного копирования
current_file = "" # Путь к текущему выбранному файлу
mega = Mega() # Экземпляр библиотеки MEGA
mega_session = None # Сессия MEGA после авторизации
key_file = "encryption_key.key" # Файл с ключом шифрования
backup_interval_minutes = 1  # Интервал резервного копирования в минутах

# 
# @function load_or_generate_key
# @brief Генерирует или загружает ключ для шифрования данных.
# @return Экземпляр Fernet для шифрования и дешифрования данных.
# 

def load_or_generate_key():
    if not os.path.exists(key_file):
        key = Fernet.generate_key()
        with open(key_file, "wb") as key_out:
            key_out.write(key)
    else:
        with open(key_file, "rb") as key_in:
            key = key_in.read()
    return Fernet(key)

cipher = load_or_generate_key()

# 
# @function encrypt_file
# @brief Шифрует файл с использованием Fernet.
# @param file_path Путь к файлу для шифрования.
# @return Путь к зашифрованному файлу.
# 

def encrypt_file(file_path):
    encrypted_path = file_path + ".enc"
    with open(file_path, "rb") as original_file:
        data = original_file.read()
    encrypted_data = cipher.encrypt(data)
    with open(encrypted_path, "wb") as encrypted_file:
        encrypted_file.write(encrypted_data)
    return encrypted_path

# 
# @function decrypt_file
# @brief Дешифрует файл с использованием Fernet.
# @param encrypted_path Путь к зашифрованному файлу.
# @param save_path Путь для сохранения дешифрованного файла.
# 

def decrypt_file(encrypted_path, save_path):
    with open(encrypted_path, "rb") as enc_file:
        encrypted_data = enc_file.read()
    decrypted_data = cipher.decrypt(encrypted_data)
    with open(save_path, "wb") as decrypted_file:
        decrypted_file.write(decrypted_data)

# 
# @function mega_login
# @brief Выполняет авторизацию в MEGA.
# 

def mega_login():
    global mega_session
    email = email_entry.get()
    password = password_entry.get()
    try:
        mega_session = mega.login(email, password)
        messagebox.showinfo("Успех", "Вход в MEGA выполнен успешно!")
        auth_window.destroy()
    except Exception as e:
        messagebox.showerror("Ошибка", f"Ошибка авторизации: {e}")

# 
# @function choose_file
# @brief Открывает диалог выбора файла и сохраняет путь к выбранному файлу.
# 

def choose_file():
    global current_file
    file_path = filedialog.askopenfilename()
    if file_path:
        current_file = file_path
        file_label.config(text=f"Выбран файл: {os.path.basename(file_path)}")

# 
# @function start_backup
# @brief Запускает процесс резервного копирования.
# 

def start_backup():
    global backup_process_active
    if not current_file:
        messagebox.showerror("Ошибка", "Сначала выберите файл для копирования!")
        return
    if not mega_session:
        messagebox.showerror("Ошибка", "Авторизуйтесь в MEGA перед началом!")
        return

    def backup_loop():
        global backup_process_active
        while backup_process_active:
            try:
                encrypted_path = encrypt_file(current_file)
                filename = os.path.basename(encrypted_path)
                mega_session.upload(encrypted_path)
                os.remove(encrypted_path)  
                log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {filename} загружен в MEGA\n")
                
                
                remaining_time = backup_interval_minutes * 60
                update_time_label(remaining_time)
                
                time.sleep(backup_interval_minutes * 60)  
            except Exception as e:
                log_text.insert(tk.END, f"Ошибка резервного копирования: {e}\n")
                break
    
    backup_process_active = True
    log_text.insert(tk.END, "Резервное копирование запущено...\n")
    Thread(target=backup_loop, daemon=True).start()


# 
# @function stop_backup
# @brief Останавливает процесс резервного копирования.
# 

def stop_backup():
    global backup_process_active
    backup_process_active = False
    log_text.insert(tk.END, "Резервное копирование остановлено.\n")

# 
# @function restore_file
# @brief Восстанавливает файл из MEGA.
# 

def restore_file():
    if not mega_session:
        messagebox.showerror("Ошибка", "Авторизуйтесь в MEGA перед началом!")
        return
    
    def list_and_restore():
        files = mega_session.get_files()
        file_list = [(details["a"]["n"], file_id) for file_id, details in files.items() if "a" in details]
        if not file_list:
            messagebox.showinfo("Файлы", "Файлы на MEGA не найдены.")
            return

        # Запрашиваем выбор файла через главный поток
        def ask_for_file_choice():
            file_choices = "\n".join([f"{idx+1}. {name}" for idx, (name, _) in enumerate(file_list)])
            choice = simpledialog.askinteger("Выбор файла", f"Доступные файлы:\n{file_choices}\nВведите номер файла:")
            
            if choice and 0 < choice <= len(file_list):
                file_name = file_list[choice-1][0]
                folder_path = filedialog.askdirectory(title="Выберите папку для сохранения файла")
                if folder_path:
                    file_info = mega_session.find(file_name)
                    mega_session.download(file_info, folder_path)
                    encrypted_path = f"{folder_path}/{file_name}"
                    save_file = file_name[:-4]
                    decrypt_file(encrypted_path, f"{folder_path}/{save_file}")
                    os.remove(encrypted_path)  
                    messagebox.showinfo("Успех", f"Файл '{file_name}' восстановлен в папку '{folder_path}'!")

        root.after(0, ask_for_file_choice)

    Thread(target=list_and_restore, daemon=True).start()

# 
# @function update_time_label
# @brief Обновляет метку оставшегося времени до следующего копирования.
# @param remaining_time Оставшееся время в секундах.
# 

def update_time_label(remaining_time):
    remaining_minutes = remaining_time // 60
    remaining_seconds = remaining_time % 60
    time_label.config(text=f"Оставшееся время до следующего копирования: {remaining_minutes} мин {remaining_seconds} сек")

# 
# @function update_backup_interval
# @brief Обновляет интервал резервного копирования на основе выбранного значения.
# @param event Событие выбора в ComboBox.
# 

def update_backup_interval(event):
    global backup_interval_minutes
    interval_choice = interval_combobox.get()
    if interval_choice == "1 минута":
        backup_interval_minutes = 1
    elif interval_choice == "3 минуты":
        backup_interval_minutes = 3
    elif interval_choice == "5 минут":
        backup_interval_minutes = 5

# Основное окно
root = tk.Tk()
root.title("Программа резервного копирования")

# Вход в MEGA
auth_window = tk.Toplevel(root)
auth_window.title("Авторизация MEGA")
tk.Label(auth_window, text="Email:").pack()
email_entry = tk.Entry(auth_window)
email_entry.pack()
tk.Label(auth_window, text="Пароль:").pack()
password_entry = tk.Entry(auth_window, show="*")
password_entry.pack()
tk.Button(auth_window, text="Войти", command=mega_login).pack()

# Главное меню
file_label = tk.Label(root, text="Выберите файл для резервного копирования.")
file_label.pack()
tk.Button(root, text="Выбрать файл", command=choose_file).pack()

# Выбор интервала
tk.Label(root, text="Выберите периодичность резервного копирования:").pack()
interval_combobox = ttk.Combobox(root, values=["1 минута", "3 минуты", "5 минут"])
interval_combobox.set("1 минута")  # Значение по умолчанию
interval_combobox.bind("<<ComboboxSelected>>", update_backup_interval)
interval_combobox.pack()

# Кнопки управления
tk.Button(root, text="Запустить резервное копирование", command=start_backup).pack()
tk.Button(root, text="Остановить резервное копирование", command=stop_backup).pack()
tk.Button(root, text="Восстановить файл", command=restore_file).pack()

# Метка для отображения времени до следующего копирования
time_label = tk.Label(root, text="Оставшееся время до следующего копирования: 0 мин 0 сек")
time_label.pack()

# Логи
log_text = tk.Text(root, height=10, width=50)
log_text.pack()

# Запуск GUI
root.mainloop()