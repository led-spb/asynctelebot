from asynctelebot.telebot import Bot, BotRequestHandler, TextMessageHandler
import pytest

class DummyHandler(BotRequestHandler):
    @TextMessageHandler("/private( .*)?", authorized=True)
    def private(self, message):
        return True

    @TextMessageHandler("/public( .*)?")
    def public(self, message):
        return True


class TestBotHandler:
    @pytest.fixture
    def handler(self):
        bot = Bot(None, admins=[1, 2, 3, 999])
        instance = DummyHandler()
        instance.assign_to(bot)
        yield instance


    def test_handler_count_commands(self, handler):
        assert len(handler.commands) == 2, \
            "Handler instance must has 2 commands"

    def test_handler_auth_user(self, handler):
        assert handler.private({"text": "/private", "from": {"id": 2}}), \
            "Authorized user hasn't access to private command"

    def test_handler_nonauth_user(self, handler):
        assert not handler.private({"text": "/private", "from": {"id": 15}}), \
            "Unauthorized user has access to private command"

    def test_handler_public_command_nonauth(self, handler):
        assert handler.public({"text": "/public", "from": {"id": 15}}), \
            "Unauthorized user hasn't access to public command"

    def test_handler_public_command_auth(self, handler):
        assert handler.public({"text": "/public", "from": {"id": 999}}), \
            "Authorized user hasn't access to public command"
