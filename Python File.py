import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
from tkinter import ttk
from threading import Thread
from mega import Mega
from cryptography.fernet import Fernet
import os
import time

# Глобальные переменные
backup_process_active = False
current_file = ""
mega = Mega()
mega_session = None
key_file = "encryption_key.key"
backup_interval_minutes = 1  # Значение по умолчанию

# Генерация и загрузка ключа шифрования
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

# Шифрование файла
def encrypt_file(file_path):
    encrypted_path = file_path + ".enc"
    with open(file_path, "rb") as original_file:
        data = original_file.read()
    encrypted_data = cipher.encrypt(data)
    with open(encrypted_path, "wb") as encrypted_file:
        encrypted_file.write(encrypted_data)
    return encrypted_path

# Дешифрование файла
def decrypt_file(encrypted_path, save_path):
    with open(encrypted_path, "rb") as enc_file:
        encrypted_data = enc_file.read()
    decrypted_data = cipher.decrypt(encrypted_data)
    with open(save_path, "wb") as decrypted_file:
        decrypted_file.write(decrypted_data)

# Авторизация MEGA
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

# Функция для выбора файла
def choose_file():
    global current_file
    file_path = filedialog.askopenfilename()
    if file_path:
        current_file = file_path
        file_label.config(text=f"Выбран файл: {os.path.basename(file_path)}")

# Резервное копирование
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
                os.remove(encrypted_path)  # Удаляем локальный зашифрованный файл
                os.remove(current_file)  # Удаляем оригинальный файл после загрузки
                log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {filename} загружен в MEGA\n")
                
                # Обновление времени до следующего резервного копирования
                remaining_time = backup_interval_minutes * 60
                update_time_label(remaining_time)
                
                time.sleep(backup_interval_minutes * 60)  # Интервал в секундах для следующего резервного копирования
            except Exception as e:
                log_text.insert(tk.END, f"Ошибка резервного копирования: {e}\n")
                break
    
    backup_process_active = True
    log_text.insert(tk.END, "Резервное копирование запущено...\n")
    
    # Запуск резервного копирования в отдельном потоке
    Thread(target=backup_loop, daemon=True).start()

def stop_backup():
    global backup_process_active
    backup_process_active = False
    log_text.insert(tk.END, "Резервное копирование остановлено.\n")

# Восстановление файла
# Восстановление файла
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
                file_name, file_id = file_list[choice-1]
                # Запрашиваем папку для сохранения
                folder_path = filedialog.askdirectory(title="Выберите папку для сохранения файла")
                if folder_path:
                    save_path = os.path.join(folder_path, file_name)
                    encrypted_path = "temp_enc_file"
                    mega_session.download(file_id, encrypted_path)
                    decrypt_file(encrypted_path, save_path)
                    os.remove(encrypted_path)  # Удаляем зашифрованный временный файл
                    messagebox.showinfo("Успех", f"Файл '{file_name}' восстановлен в папку '{folder_path}'!")

        # Используем root.after() для вызова диалога выбора файла в главном потоке
        root.after(0, ask_for_file_choice)

    Thread(target=list_and_restore, daemon=True).start()



# Обновление метки с оставшимся временем
def update_time_label(remaining_time):
    remaining_minutes = remaining_time // 60
    remaining_seconds = remaining_time % 60
    time_label.config(text=f"Оставшееся время до следующего копирования: {remaining_minutes} мин {remaining_seconds} сек")

# Изменение интервала резервного копирования
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
