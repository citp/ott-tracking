class PiHoleListParser:

    def __init__(self):
        self.domains = set()

        with open('blocklists/pi-hole.txt', 'r') as f:
            for line in f.readlines():
                self.domains.add(line.strip())

    def is_blocked_by_pihole(self, domain):
        return True if domain.strip() in self.domains else False

#if __name__ == "__main__":
#    plparser = PiHoleListParser()
#    print(plparser.is_blocked_by_pihole('scorecardresearch.com'))
#    print(plparser.is_blocked_by_pihole('e.scorecardresearch.com'))
#    print(plparser.is_blocked_by_pihole('a.scorecardresearch.com'))
