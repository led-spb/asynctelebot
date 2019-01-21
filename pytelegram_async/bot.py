import json
import re
import logging
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPError
from tornado.ioloop import IOLoop
from tornado import gen
from uuid import uuid4
from functools import partial
from datetime import timedelta
from entity import Entity, File
import inspect


class MessageHandler(object):
    def __init__(self, message_type='text', authorized=False):
        self.authorized = authorized
        self.message_type = message_type
        self.admins = None

    def pre_process(self, message):
        if self.message_type not in message:
            return False
        if not self.authorized:
            return True
        if self.admins is not None and message['from'].get('id') in self.admins:
            return True

        logging.warn('User "%d/%s" is not authorized', message['from'].get('id'), message['from'].get('first_name'))
        return False

    def __call__(self, func):
        def wrapped(this, message):
            self.admins = this.bot.admins if this.bot is not None else []
            if self.pre_process(message):
                arguments = []
                for arg in inspect.getargspec(func).args:
                    if arg == 'self':
                        arguments.append(this)
                    elif arg == 'message':
                        arguments.append(message)
                    elif arg in message:
                        arguments.append(message[arg])
                    else:
                        arguments.append(None)

                return func(*arguments)
            else:
                return False
        wrapped.is_handler = True
        return wrapped


class PatternMessageHandler(MessageHandler):
    def __init__(self, pattern, authorized=False):
        MessageHandler.__init__(self, 'text', authorized)
        self.pattern = re.compile(pattern)

    def pre_process(self, message):
        if not MessageHandler.pre_process(self, message):
            return False
        if self.pattern.match(message['text']) is not None:
            return True
        return False


class BotRequestHandler:
    def __init__(self):
        self.bot = None
        self._commands = None

    @property
    def commands(self):
        if self._commands is not None:
            return self._commands
        self._commands = []
        for func_name in dir(self):
            func = getattr(self, func_name)
            if callable(func) and hasattr(func, 'is_handler'):
                self._commands.append(func)
        return self._commands

    @PatternMessageHandler('/version', authorized=True)
    def get_version(self, chat):
        if hasattr(self, 'version'):
            self.bot.send_message(to=chat['id'], message=str(getattr(self, 'version')))
            return True
        else:
            return False

    def assign_to(self, bot):
        self.bot = bot


class Bot(object):

    def __init__(self, token, admins=None, handler=None, logger=None, proxy=None, ioloop=None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        self.token = token
        self.admins = admins or []
        self.proxy = proxy

        self.baseUrl = 'https://api.telegram.org/bot%s' % self.token
        self.handlers = []
        if handler is not None:
            self.add_handler(handler)

        self.ioloop = ioloop or IOLoop.current()
        self._client = AsyncHTTPClient()
        self.params = {'timeout': 60, 'offset': 0, 'limit': 5}

    def add_handler(self, handler):
        if handler is not None:
            handler.assign_to(self)
            self.handlers.append(handler)
        pass

    def request_loop(self):
        request = HTTPRequest(
            url=self.baseUrl+'/getUpdates',
            method='POST',
            headers={"Content-Type": "application/json"},
            body=json.dumps(self.params),
            request_timeout=self.params['timeout']+5
        )
        self._client.fetch(request, callback=self._on_updates_ready, raise_error=False)
        return

    def process_updates(self, updates):
        for update in updates:
            if 'callback_query' in update:
                callback = update['callback_query']
                self.exec_callback(callback)

                message = callback['message']
                message['from'] = callback['from']
                message['text'] = callback['data']
                message['is_callback'] = True
                update.update({'message': message})

            if 'message' in update:
                message = update['message']
                if 'from' in message:
                    user = message['from']

                    message_type = list(
                        set(message.keys())
                        & {"text", "audio", "document", "photo", "sticker", "video", "voice", "contact", "location",
                           "venue", "game"})
                    message_type = message_type[0] if len(message_type) > 0 else "unknown"
                    if message_type == "text":
                        message_type = message["text"]

                    self.logger.info("message \"%s\" from %d/%s", message_type, user.get('id'), user.get('first_name'))
                    try:
                        self.exec_command(message)
                    except Exception:
                        logging.exception('Error while processing request')
            self.params['offset'] = update['update_id']+1
        return

    def exec_command(self, message):
        self.logger.debug(json.dumps(message, indent=2))
        for handler in self.handlers:
            for cmd_handler in handler.commands:
                if cmd_handler.__call__(message):
                    return True
        return False

    def exec_callback(self, callback):
        url = self.baseUrl + '/answerCallbackQuery?callback_query_id=%s' % callback['id']
        return self._client.fetch(url, raise_error=False)

    def _on_updates_ready(self, response):
        try:
            response.rethrow()
            result = json.loads(response.body)

            self.logger.debug('updates:')
            self.logger.debug(json.dumps(result, indent=2))
            if result['ok']:
                updates = result['result']
                self.process_updates(updates)
            else:
                self.logger.error('Error while receive updates from server')
                self.logger.error(result)

            self.loop_start()
        except (HTTPError, ValueError):
            self.logger.exception('Error while receive updates from server')
            self.loop_start(10)
            pass

    def _on_message_cb(self, response):
        try:
            response.rethrow()
        except HTTPError:
            self.logger.exception("Error while sending message")
        pass

    def loop_start(self, delay=0):
        if delay > 0:
            self.ioloop.add_timeout(timedelta(seconds=15), self.request_loop)
        else:
            self.ioloop.add_callback(self.request_loop)

    @gen.coroutine
    def multipart_producer(self, boundary, body, files, write):
        boundary_bytes = boundary.encode()

        for key, value in body.iteritems():
            buf = ( 
                   (b'--%s\r\n' % (boundary_bytes,))
                   + (b'Content-Disposition: form-data; name="%s"\r\n' % key.encode())
                   + (b'\r\n%s\r\n' % str(value).encode())
              )
            yield write(buf)

        for key, value in files.iteritems():
            filename = value[0]
            f = value[1]
            mime_type = value[2]
            self.logger.debug("FILE: %s: %s %s", key, filename, mime_type)

            buf = (
                    (b"--%s\r\n" % boundary_bytes) +
                    (b'Content-Disposition: form-data; name="%s"; filename="%s"\r\n'
                     % (key.encode(), filename.encode())) +
                    (b"Content-Type: %s\r\n" % mime_type.encode()) +
                    b"\r\n"
            )
            yield write(buf)

            while True:
                chunk = f.read(16 * 1024)
                if not chunk:
                    break
                yield write(chunk)
            yield write(b"\r\n")

        yield write(b"--%s--\r\n" % (boundary_bytes,))
        pass

    def send_request(self, url, body=None, files=None, timeout=None, callback=None):
        if files is None or len(files) == 0:
            request = HTTPRequest(
                url, headers={"Content-Type": "application/json"},
                method='POST', body=json.dumps(body)
            )
        else:
            boundary = uuid4().hex
            request = HTTPRequest(
                url, headers={"Content-Type": "multipart/form-data; boundary=%s" % boundary},
                method='POST',
                body_producer=partial(
                    self.multipart_producer,
                    boundary, body, files
                )
            )
        return self._client.fetch(request, callback=callback or self._on_message_cb, raise_error=False)

    def edit_message_text(self, to, message_id, text, callback=None, reply_markup=None, **extra):
        if len(text) > 4096:
            raise ValueError('Text message can\'t longer than 4096')

        params = {'chat_id': to, 'message_id': message_id, 'text': text}
        if reply_markup is not None:
            params['reply_markup'] = json.dumps(reply_markup)
        if extra is not None:
            params.update(extra)

        return self.send_request(self.baseUrl + '/editMessageText', body=params, callback=callback)

    def send_message(self, to, message, callback=None, reply_markup=None, **extra):
        params = {'chat_id': to}
        files = {}

        if isinstance(message, Entity):
            method = message.__class__.__name__
            for key, value in message.to_dict().iteritems():
                if isinstance(value, File):
                    files[key] = list(value)
                else:
                    params[key] = value
        elif isinstance(message, str) or isinstance(message, unicode):
            if len(message) > 4096:
                raise ValueError('Text message can\'t longer than 4096')
            method = 'Message'
            params['text'] = message
        else:
            raise ValueError('message parameter must be str or Entity type, got "%s"', type(message))

        if reply_markup is not None:
            params['reply_markup'] = json.dumps(reply_markup)
        if extra is not None:
            params.update(extra)

        return self.send_request(self.baseUrl + '/send%s' % method, body=params, files=files, callback=callback)
