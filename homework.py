import requests
import time
import telegram
import os
from dotenv import load_dotenv
import logging
from requests.exceptions import RequestException
import sys

load_dotenv()

LOG_FORMAT = "%(levelname)s %(asctime)s - %(message)s"

logger = logging.getLogger()
fileHandler = logging.FileHandler("main.log")
streamHandler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(LOG_FORMAT)
streamHandler.setFormatter(formatter)
fileHandler.setFormatter(formatter)
logger.addHandler(streamHandler)
logger.addHandler(fileHandler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в чат."""
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)


def get_api_answer(current_timestamp):
    """Получает ответ от API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        message = 'Код ответа API не соответствует ожидаемому.'
        logging.error(message)
        raise RequestException(message)


def check_response(response):
    """Проверяет, что ответ API соответствует ожидаемому."""
    response = response['homeworks']
    if response and response[0] is not None:
        return response
    else:
        logging.error('Ответ API не содержит необходимой информации.')


def parse_status(homework):
    """Извлекает статус домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if homework_status not in HOMEWORK_STATUSES:
        logging.error('Неизвестный статус проверки работы.')
    elif homework_status is None:
        logging.debug('Статус отсутствует.')

    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет наличие токенов в env."""
    if (PRACTICUM_TOKEN is None or TELEGRAM_TOKEN is None
       or TELEGRAM_CHAT_ID is None):
        logging.critical('Отсутствуют переменные окружения.')
        return False
    return True


def main():
    """Основная логика работы бота."""

    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            response_checked = check_response(response)
            if response_checked:
                message = parse_status(response_checked[0])
                send_message(bot, message)
                logging.info('Статус проверки отправлен в чат.')
            current_timestamp = response.get('current_date')
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
            logging.info(f'Сообщение об ошибке {error} направлено в чат.')
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
