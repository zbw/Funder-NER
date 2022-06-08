
class Expression:
    def __init__(self, text, intent):
        self.set_text(text)
        self.set_intent(intent)

    def normalize(self, text):
        return text.lower().strip()

    def set_text(self, text):
        assert isinstance(text, str), (
            'Expression: set_text: {} is not a string'.format(text))
        self.text = self.normalize(text)

    def set_intent(self, intent):
        assert isinstance(intent, str), (
            'Expression: set_intent: {} is not a string'.format(intent))
        self.intent = intent