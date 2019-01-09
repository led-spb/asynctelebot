from asynctelebot.telebot import Bot, BotRequestHandler, PatternMessageHandler, MessageHandler
import pytest


class DummyHandler(BotRequestHandler):
    @PatternMessageHandler("/private( .*)?", authorized=True)
    def private(self, message, text):
        return True

    @PatternMessageHandler("/public( .*)?")
    def public(self, message, text):
        return True

    @PatternMessageHandler("/params")
    def parameters(self, text):
        assert text == "/params"
        return True

    @MessageHandler(message_type='contact')
    def on_contact(self, contact):
        assert contact is not None
        return True


class TestBotHandler:

    @pytest.fixture
    def bot(self):
        bot = Bot(None, admins=[1, 2, 3, 999])
        yield bot

    @pytest.fixture
    def handler(self, bot):
        instance = DummyHandler()
        bot.add_handler(instance)
        yield instance

    def test_count_commands(self, handler):
        assert len(handler.commands) == 4, \
            "Handler instance must has 3 commands"

    def test_private_auth_user(self, handler):
        assert handler.bot.exec_command({"text": "/private", "from": {"id": 2}}), \
            "Authorized user hasn't access to private command"

    def test_private_nonauth_user(self, handler):
        assert not handler.bot.exec_command({"text": "/private", "from": {"id": 15}}), \
            "Unauthorized user has access to private command"

    def test_public_nonauth_user(self, handler):
        assert handler.bot.exec_command({"text": "/public", "from": {"id": 87}}), \
            "Unauthorized user hasn't access to public command"

    def test_public_auth_user(self, handler):
        assert handler.bot.exec_command({"text": "/public", "from": {"id": 999}}), \
            "Authorized user hasn't access to public command"

    def test_params_mapping(self, handler):
        handler.bot.exec_command({"text": "/params", "from": {"id": -1}})

    def test_contact_message(self, handler):
        handler.bot.exec_command({"contact": {"phone_number": "secret"}, "from": {"id": -1}})
