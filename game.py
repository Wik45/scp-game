import json

ADJ = {"A": ["C", "D"], "C": ["A", "B"], "D": ["A", "B"], "B": ["C", "D"]}


class Game:
    def __init__(self, data):
        self.d = data
        self.s = {k: {**v, "effect": 0, "sealed": False, "cams": True, "lost": 0}
                  for k, v in data["sectors"].items()}
        self.s["A"]["effect"] = 1
        self.turn = 1
        self.mtf_arrival = None
        self.integrity = 100
        self.saved = 0
        self.over = None
        self.log = []
        self.say("Records loss reported in Sector A. Site command is yours.")

    def clock(self):
        m = 480 + (self.turn - 1) * 10
        return "%02d:%02d" % (m // 60, m % 60)

    def say(self, t):
        self.log.append("T%02d %s | %s" % (self.turn, self.clock(), t))

    def mtf_ready(self):
        return self.mtf_arrival is not None and self.turn >= self.mtf_arrival

    def do(self, aid):
        if self.over:
            return self.view()
        op, _, k = aid.partition(":")
        if op == "seal" and not self.s[k]["sealed"]:
            v = self.s[k]
            if self.integrity < 50 and v["effect"] >= 2:
                self.say("Seal on %s FAILED: door authorisations tied to erased personnel." % k)
            else:
                v["sealed"] = True
                self.say("Sector %s sealed." % k)
        elif op == "cams":
            v = self.s[k]
            v["cams"] = not v["cams"]
            self.say("Sector %s cameras %s." % (k, "ONLINE" if v["cams"] else "OFFLINE"))
        elif op == "evac" and not self.s[k]["sealed"]:
            n = self.s[k]["pop"]
            self.saved += n
            self.s[k]["pop"] = 0
            self.say("Sector %s evacuated: %d staff to surface hold." % (k, n))
        elif op == "mtf" and self.mtf_arrival is None:
            self.mtf_arrival = self.turn + 3
            self.say("MTF requested. Estimated arrival T%02d." % self.mtf_arrival)
        elif op == "deploy" and self.mtf_ready():
            a = self.s["A"]
            if a["effect"] <= 2:
                a["effect"] = 0
                self.say("MTF reached the source in A. Anomaly secured.")
            else:
                self.say("MTF cannot reach the source: Sector A effect too advanced.")
        self.step()
        return self.view()

    def step(self):
        new = {}
        for k, v in self.s.items():
            e = v["effect"]
            if e > 0:
                e = min(3, e + 1) if v["cams"] else e - 1
            new[k] = e
        for k, v in self.s.items():
            if v["effect"] >= 3 and not v["sealed"]:
                for n in ADJ[k]:
                    t = self.s[n]
                    if t["cams"] and not t["sealed"] and new[n] == 0:
                        new[n] = 1
                        self.say("Effect spreading into Sector %s." % n)
        for k, v in self.s.items():
            v["effect"] = new[k]
            if new[k] >= 2 and v["pop"] > 0:
                n = min(v["pop"], 2 * (new[k] - 1))
                v["pop"] -= n
                v["lost"] += n
                self.integrity -= n * 3
                self.say("Sector %s: %d personnel erased from all records." % (k, n))
        self.turn += 1
        total = sum(v["pop"] for v in self.s.values())
        if all(v["effect"] == 0 for v in self.s.values()):
            self.over = "CONTAINED. %d staff evacuated, %d lost." % (
                self.saved + total, sum(v["lost"] for v in self.s.values()))
        elif self.integrity <= 0 or total == 0 or self.turn > 24:
            self.over = "SITE LOST. Record integrity or staff exhausted."

    def actions(self):
        out = []
        for k, v in self.s.items():
            if not v["sealed"]:
                out.append({"id": "seal:" + k, "label": "Seal", "group": k})
                out.append({"id": "evac:" + k, "label": "Evacuate", "group": k})
            out.append({"id": "cams:" + k, "label": "Cameras " + ("OFF" if v["cams"] else "ON"), "group": k})
        if self.mtf_arrival is None:
            out.append({"id": "mtf:", "label": "Request MTF", "group": "Command"})
        if self.mtf_ready():
            out.append({"id": "deploy:", "label": "Deploy MTF to source", "group": "Command"})
        out.append({"id": "wait:", "label": "Hold position", "group": "Command"})
        return out

    def view(self):
        secs = []
        for k, v in self.s.items():
            secs.append({"id": k, "name": v["name"], "effect": v["effect"] if v["cams"] else None,
                         "pop": v["pop"] if v["cams"] else None, "sealed": v["sealed"], "cams": v["cams"]})
        return json.dumps({"turn": self.turn, "clock": self.clock(), "integrity": max(0, self.integrity),
                           "saved": self.saved, "mtf": self.mtf_arrival, "sectors": secs,
                           "log": self.log[-14:], "over": self.over,
                           "actions": [] if self.over else self.actions()})
