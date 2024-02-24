from lib.rep_sys.email_auth import EmailAuthenticator
from lib.rep_sys.rep_id import RepSysUserId


class ApplicationBase:
    def get_email_authenticator(self, user_id: RepSysUserId) -> EmailAuthenticator:
        raise NotImplementedError()
