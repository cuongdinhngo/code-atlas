# Task 302 census fixture: same-file explicit return used as a member-call receiver.


class Client:
    def send(self) -> None:
        return None


def make_client() -> Client:
    return Client()


def run() -> None:
    make_client().send()
    c = make_client()
    c.send()
