from asynctelebot.telebot import Bot, BotRequestHandler, TextMessageHandler


class Object(object):
    pass


class TestBotHandler:

    def test_handler(self):
        bot = Bot(None, admins=[1234])

        class TestHandler(BotRequestHandler):
            @TextMessageHandler("/start.*", authorized=True)
            def start(self, message):
                return True

        handler = TestHandler()
        handler.assign_to(bot)

        assert len(handler.commands) == 1

        assert handler.start({"text": "/start", "from": {"id": 13}})
