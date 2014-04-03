class LQFBIssue(object):
    def __init__(self, id, closed=None, fully_frozen=None, half_frozen=None, accepted=None, created=None,
                 area_name=None):
        self.id = id
        self.closed = closed
        self.fully_frozen = fully_frozen
        self.half_frozen = half_frozen
        self.accepted = accepted
        self.created = created
        self.area_name = area_name

        self.initiatives = dict()

    def add_initiative(self, ini):
        assert isinstance(ini, LQFBInitiative)
        self.initiatives[ini.id] = ini


class LQFBInitiative(object):
    def __init__(self, id, name, eligible=None, rank=None):
        self.id = id
        self.name = name
        self.eligible = eligible
        self.rank = rank