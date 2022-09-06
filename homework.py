import logging
import sys
import time
import telegram
import requests
import os
from exceptions import ErrorException
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('pract_token')
TELEGRAM_TOKEN = os.getenv('telegram_token')
TELEGRAM_CHAT_ID = os.getenv('chat')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
handler_1 = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler_1)

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def logging_message(message):
    """Делает запись в логе и вызывает ошибку."""
    logging.error(message)
    raise ErrorException(message)


def send_message(bot, message):
    """Отправить сообщение."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(f'Бот отправил сообщение {message}')
    except Exception as error:
        logging.error(f'Не удалось отправить сообщение {error}')


def get_api_answer(current_timestamp):
    """Запросить к api."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_status = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if str(homework_status.status_code)[0] == '5':
        logging_message('Эндпоинт недоступен')
    if homework_status.status_code != 200:
        logging_message('Сбой при запросе к эндпоинту')
    return homework_status.json()


def check_response(response):
    """Проверить ответ api на корректность."""
    if type(response['homeworks']) is not list:
        logging_message('Отсутствие ожидаемого типа в ответе API')
    if len(response['homeworks']) == 0:
        logging.debug('Нет новых статусов')
        raise Exception
    else:
        return response['homeworks']


def parse_status(homework):
    """Извлечь статус работы."""
    if 'homework_name' not in homework:
        raise KeyError
    homework_name = homework.get('homework_name')
    if 'status' not in homework:
        raise KeyError
    homework_status = homework.get('status')
    try:
        verdict = HOMEWORK_STATUSES.get(homework_status)
        print(verdict)
        if verdict is None:
            logging_message('Недокументированный статус домашней работы')
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except TypeError:
        logging_message('Отсутствие ключа домашней работы')
    except KeyError:
        raise logging_message('ключ отсутсвует в списке')


def check_tokens():
    """Проверить доступность переменной окружения."""
    if PRACTICUM_TOKEN is None:
        return False
    elif TELEGRAM_TOKEN is None:
        return False
    elif TELEGRAM_CHAT_ID is None:
        return False
    return True


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        logging.critical('Переменная окружения недоступна.')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks_dict = check_response(response)
            for homework in homeworks_dict:
                message = parse_status(homework)
                send_message(bot, message)
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except ErrorException as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception:
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
