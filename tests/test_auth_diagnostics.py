from unittest.mock import MagicMock, patch

import pytest
from streamlit.testing.v1 import AppTest

from ecoscan.services.password_identity import register, sign_in


class ProviderError(Exception):
    def __init__(self, code, status=400):
        super().__init__('PRIVATE_PASSWORD private@example.com ACCESS_TOKEN')
        self.code = code
        self.status = status


@pytest.mark.parametrize('code, fragment', [
    ('email_not_confirmed', 'Confirme seu e-mail'),
    ('invalid_credentials', 'Confira e-mail e senha'),
    ('over_email_send_rate_limit', 'limite temporário'),
    ('weak_password', 'critérios de segurança'),
    ('signup_disabled', 'temporariamente desabilitado'),
    ('captcha_failed', 'verificação de segurança'),
    ('email_address_not_authorized', 'não permite este envio'),
    ('unknown PRIVATE_PASSWORD', 'não concluiu'),
])
def test_errors_are_actionable_and_redacted(code, fragment, caplog):
    with patch('ecoscan.services.password_identity._client', side_effect=ProviderError(code)):
        with pytest.raises(ValueError) as error:
            sign_in('private@example.com', 'PRIVATE_PASSWORD')
    assert fragment in str(error.value)
    assert 'Código de atendimento:' in str(error.value)
    assert 'auth_failure operation=login' in caplog.text
    for secret in ('PRIVATE_PASSWORD', 'private@example.com', 'ACCESS_TOKEN'):
        assert secret not in str(error.value) + caplog.text


def test_http_rate_limit_without_code_is_handled():
    with patch('ecoscan.services.password_identity._client', side_effect=ProviderError(None, 429)):
        with pytest.raises(ValueError, match='Muitas tentativas'):
            sign_in('a@example.com', 'password')


def test_duplicate_account_error_does_not_disclose_existence():
    client = MagicMock()
    client.auth.sign_up.side_effect = ProviderError('user_already_exists')
    with patch('ecoscan.services.password_identity._client', return_value=client):
        with pytest.raises(ValueError) as error:
            register('a@example.com', 'long-password', 'long-password', enabled=True)
    assert 'user_already_exists' not in str(error.value)


def test_invalid_signup_does_not_consume_remote_cooldown():
    app = AppTest.from_string('''
import streamlit as st
from ecoscan.ui.identity import _render_registration
_render_registration(st, {'public_signup_enabled': True})
''').run()
    with patch('ecoscan.services.password_identity.register') as signup:
        app.text_input[0].set_value('person@example.com')
        app.text_input[1].set_value('short')
        app.text_input[2].set_value('short')
        app.checkbox[0].check()
        app.button[0].click().run()
        assert app.error
        assert 'signup_last_attempt' not in app.session_state
        signup.assert_not_called()
        app.text_input[0].set_value('person@example.com')
        app.text_input[1].set_value('long-password')
        app.text_input[2].set_value('long-password')
        app.checkbox[0].check()
        app.button[0].click().run()
        assert not app.exception
        assert app.success
        signup.assert_called_once()


@pytest.mark.parametrize('function, key', [
    ('_render_resend_confirmation', 'signup_last_attempt'),
    ('_render_reset_request', 'reset_last_attempt'),
])
def test_invalid_email_does_not_consume_send_cooldown(function, key):
    app = AppTest.from_string(f'''
import streamlit as st
from ecoscan.ui.identity import {function}
{function}(st)
''').run()
    app.text_input[0].set_value('invalid')
    app.button[0].click().run()
    assert app.error
    assert key not in app.session_state
