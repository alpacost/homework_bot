from http import HTTPStatus
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
logger.setLevel(logging.INFO)
handler_1 = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler_1)

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def logging_message(message):
    """Делает запись в логе и вызывает ошибку."""
    logger.error(message)
    raise ErrorException(message)


def send_message(bot, message):
    """Отправить сообщение."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Бот отправил сообщение {message}')
    except Exception as error:
        logger.exception(f'Не удалось отправить сообщение {error}')


def get_api_answer(current_timestamp):
    """Запросить к api."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_status = requests.get(ENDPOINT,
                                       headers=HEADERS,
                                       params=params)
        if str(homework_status.status_code)[0] == '5':
            raise Exception('Эндпоинт недоступен')
        if homework_status.status_code != HTTPStatus.OK:
            raise Exception('Сбой при запросе к эндпоинту')
        return homework_status.json()
    except Exception as error:
        logging_message(str(error))


def check_response(response):
    """Проверить ответ api на корректность."""
    if not isinstance(response['homeworks'],
                      list):
        logging_message('Отсутствие ожидаемого типа в ответе API')
    if not isinstance(response, dict):
        # Не проходит тесты если сначала проверять на словарь
        logging_message(
            'Отсутствие ожидаемого типа в ответе API (response не словарь)'
        )
    return response['homeworks']


def parse_status(homework):
    """Извлечь статус работы."""
    if not homework:
        logger.debug('Нет новых статусов')
    if 'homework_name' not in homework:
        raise KeyError('homework_name')
    homework_name = homework.get('homework_name')
    if 'status' not in homework:
        raise KeyError('status')
    homework_status = homework.get('status')
    try:
        verdict = HOMEWORK_STATUSES.get(homework_status)
        if verdict is None:
            logging_message('Недокументированный статус домашней работы')
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except TypeError:
        logging_message('Отсутствие ключа домашней работы')
    except KeyError as error:
        logging_message(f'{error}отсутсвует в списке')


def check_tokens():
    """Проверить доступность переменной окружения."""
    tokens = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    return all(tokens)


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Переменная окружения недоступна.')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks and homeworks is not None:
                for homework in homeworks:
                    message = parse_status(homework)
                    send_message(bot, message)
            else:
                logger.debug('Нет новых статусов')
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
