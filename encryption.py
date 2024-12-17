from cryptography.fernet import Fernet
import os
import json
from datetime import datetime


# Функция для загрузки данных из конфигурационного файла
def load_config(file_path='config.json'):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        if default_data is None:
            default_data = {}
        with open(file_path, 'w') as file:
            json.dump(default_data, file, indent=4)
        print(f"Файл '{file_path}' не найден, создан с начальными данными.")
        return default_data

# Функция для сохранения данных в конфигурационный файл
def save_config(data, file_path='config.json'):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

# Функция для добавления новой записи (дата и ключ шифрования)
def add_encryption_key(date, encryption_key, file_path='config.json'):
    config = load_config(file_path)
    config[date] = {"encryption_key": encryption_key}
    save_config(config, file_path)

# Функция для получения ключа шифрования по дате
def get_encryption_key(date, file_path='config.json'):
    config = load_config(file_path)
    return config.get(date, {}).get("encryption_key", None)


def encrypt_file(file_path):
    KEY = Fernet.generate_key()
    cipher = Fernet(KEY)
    with open(file_path, 'rb') as f:
        encrypted_data = cipher.encrypt(f.read())
    encrypted_path = file_path + ".enc"
    with open(encrypted_path, 'wb') as f:
        f.write(encrypted_data)
    add_encryption_key(datetime.now().strftime('%d-%m-%Y %H:%M:%S'), repr(KEY))
    return encrypted_path

def decrypt_file(encrypted_path, output_path, date):
    KEY = eval(get_encryption_key(date))
    cipher = Fernet(KEY)
    with open(encrypted_path, 'rb') as f:
        decrypted_data = cipher.decrypt(f.read())
    with open(output_path, 'wb') as f:
        f.write(decrypted_data)
        return output_path

date = datetime.now().strftime('%d-%m-%Y')
print(encrypt_file("Python File.py"))
print(decrypt_file("Python File.py.enc", "C:\\Users\\numma\\Python File.py", date))