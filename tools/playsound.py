class MockPlaySound:
    def __call__(self, *args, **kwargs):
        return None


playsound = MockPlaySound()
