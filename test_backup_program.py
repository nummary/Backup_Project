import os
import unittest
from cryptography.fernet import Fernet
from backup_program import load_or_generate_key

class TestLoadOrGenerateKey(unittest.TestCase):
    key_file = "encryption_key.key"

    def setUp(self):
        # Удаляем файл ключа перед каждым тестом, чтобы обеспечить чистую среду
        if os.path.exists(self.key_file):
            os.remove(self.key_file)

    def tearDown(self):
        # Удаляем файл ключа после каждого теста
        if os.path.exists(self.key_file):
            os.remove(self.key_file)

    def test_key_generation(self):
        """Проверяет генерацию нового ключа, если файл отсутствует."""
        cipher = load_or_generate_key()
        self.assertTrue(os.path.exists(self.key_file), "Файл ключа не создан!")
        self.assertIsInstance(cipher, Fernet, "Возвращённый объект не является экземпляром Fernet.")

    def test_key_loading(self):
        """Проверяет загрузку существующего ключа."""
        # Создаём файл ключа вручную
        generated_key = Fernet.generate_key()
        with open(self.key_file, "wb") as f:
            f.write(generated_key)

        # Проверяем загрузку ключа
        cipher = load_or_generate_key()
        with open(self.key_file, "rb") as f:
            saved_key = f.read()

        self.assertEqual(cipher._signing_key, Fernet(saved_key)._signing_key, "Загруженный ключ отличается от сохранённого!")

if __name__ == "__main__":
    unittest.main()
