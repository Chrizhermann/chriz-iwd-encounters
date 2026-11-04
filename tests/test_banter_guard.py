"""Tests for component 110, the banter guard: real WeiDU on compiled scripts, no game needed.

Usage: python -I tests/test_banter_guard.py <weidu.exe>

The scripts are written here as readable lines and compiled by a small encoder for the
few triggers and actions they use. A small model of the script engine then reads the
patched script and works out, as exact fractions, what one pass does: one number per
pass, which every RandomNum of the pass reads (measured in the game, 2026-11-05); the
first block whose triggers hold runs; a response is picked by weight.
"""
import itertools
import math
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MOD = REPO / "chriz-iwd-encounters"
HARNESS = REPO / "tests" / "banter_harness.tp2"
WEIDU = ""

TIMERS = ('    RealSetGlobalTimer("IWD_BANTER_TIMER","GLOBAL",1800)\n'
          '    SetGlobalTimer("IWD_BANTER_TIMER_REAL_TIME","GLOBAL",7200)\n')
OTHER_BLOCK = ('IF\n  Global("SOMETHING_ELSE","GLOBAL",0)\nTHEN\n  RESPONSE #100\n'
               '    SetGlobal("SOMETHING_ELSE","GLOBAL",1)\n    Continue()\nEND\n')

# --- a small compiler and decompiler: the raw format the engine reads ---

NEXT_TRIGGER_OBJECT, STATE_CHECK, IN_MY_AREA = 0x40E0, 0x4037, 0x40CB
RANDOM_NUM, RANDOM_NUM_GT, RANDOM_NUM_LT, OR_TRIGGER, OTHER_TRIGGER = 0x4047, 0x4048, 0x4049, 0x4089, 0x4000
NOT_VALID = -2146426897
SLOTS = {"Player%d" % n: 20 + n for n in range(1, 7)}
SLOTS.update({"Player%dFill" % n: 69 + n for n in range(1, 7)})
IDS_SLOTS = {v: k for k, v in SLOTS.items()}


def obj(name=""):
    if name in SLOTS:
        return '0 0 0 0 0 0 0 %d 0 0 0 0 ""' % SLOTS[name]
    return '0 0 0 0 0 0 0 0 0 0 0 0 "%s"' % name.strip('"')


def record(code, a=0, flags=0, b=0, c=0, s1="", s2="", target=""):
    return 'TR\n%d %d %d %d %d "%s" "%s" OB\n%sOB\nTR\n' % (code, a, flags, b, c, s1, s2, obj(target))


def compile_trigger(text):
    m = re.fullmatch(r"TriggerOverride\((\w+),(.*)\)", text)
    if m:
        return record(NEXT_TRIGGER_OBJECT, target=m.group(1)) + compile_trigger(m.group(2))
    negated = int(text.startswith("!"))
    body = text.lstrip("!")
    m = re.fullmatch(r"StateCheck\((\w+),CD_STATE_NOTVALID\)", body)
    if m:
        return record(STATE_CHECK, NOT_VALID, negated, target=m.group(1))
    m = re.fullmatch(r"InMyArea\((\w+)\)", body)
    if m:
        return record(IN_MY_AREA, 0, negated, target=m.group(1))
    m = re.fullmatch(r"RandomNum\((\d+),(\d+)\)", body)
    if m:
        return record(RANDOM_NUM, int(m.group(1)), negated, int(m.group(2)))
    m = re.fullmatch(r"OR\((\d+)\)", body)
    if m:
        return record(OR_TRIGGER, int(m.group(1)))
    return record(OTHER_TRIGGER, 0, negated, s1=body.replace('"', "'"))


def compile_action(text):
    m = re.fullmatch(r"ActionOverride\((\w+),Interact\((.+)\)\)", text)
    if m:
        return 'AC\n168OB\n%sOB\nOB\n%sOB\nOB\n%sOB\n0 0 0 0 0"" "" AC\n' % (obj(m.group(1)), obj(m.group(2)), obj())
    return 'AC\n115OB\n%sOB\nOB\n%sOB\nOB\n%sOB\n0 0 0 0 0"%s" "" AC\n' % (obj(), obj(), obj(), text.replace('"', "'"))


def lines_to_blocks(text):
    """Readable script text to (triggers, [(weight, actions)])."""
    text = text.replace("\r\n", "\n")
    blocks = []
    for found in re.finditer(r"^IF\n(.*?)^THEN\n(.*?)^END$", text, re.M | re.S):
        triggers = [line.strip() for line in found.group(1).splitlines() if line.strip()]
        responses = []
        for part in re.split(r"^\s*RESPONSE #", found.group(2), flags=re.M)[1:]:
            weight, _, actions = part.partition("\n")
            responses.append((int(weight), [line.strip() for line in actions.splitlines() if line.strip()]))
        blocks.append((triggers, responses))
    return blocks


def compile_script(text):
    out = "SC\n"
    for triggers, responses in lines_to_blocks(text):
        out += "CR\nCO\n" + "".join(compile_trigger(t) for t in triggers) + "CO\nRS\n"
        for weight, actions in responses:
            out += "RE\n%d" % weight + "".join(compile_action(a) for a in actions) + "RE\n"
        out += "RS\nCR\n"
    return out + "SC\n"


def name_of(fields):
    parts = fields.split()
    if int(parts[7]) in IDS_SLOTS:
        return IDS_SLOTS[int(parts[7])]
    return re.search(r'"(.*)"', fields).group(1)


def decompile_script(raw):
    """Compiled script to (triggers, [(weight, actions)]), the model's input."""
    raw = raw.replace("\r\n", "\n")
    assert raw.startswith("SC\n") and raw.endswith("SC\n"), raw[:20]
    blocks = []
    for block in re.findall(r"^CR\nCO\n(.*?)^RS\nCR\n", raw, re.M | re.S):
        condition, _, body = block.partition("CO\nRS\n")
        triggers, override = [], None
        for code, a, flags, b, s1, target in re.findall(
                r'TR\n(\d+) (-?\d+) (\d+) (-?\d+) 0 "([^"]*)" "" OB\n([^\n]*)OB\nTR\n', condition):
            code, a, flags, b = int(code), int(a), int(flags), int(b)
            sign = "!" if flags else ""
            if code == NEXT_TRIGGER_OBJECT:
                override = name_of(target)
                continue
            if code == STATE_CHECK:
                text = "%sStateCheck(%s,CD_STATE_NOTVALID)" % (sign, name_of(target))
            elif code == IN_MY_AREA:
                text = "%sInMyArea(%s)" % (sign, name_of(target))
            elif code == RANDOM_NUM:
                text = "%sRandomNum(%d,%d)" % (sign, a, b)
            elif code == RANDOM_NUM_GT:
                text = "%sRandomNumGT(%d,%d)" % (sign, a, b)
            elif code == RANDOM_NUM_LT:
                text = "%sRandomNumLT(%d,%d)" % (sign, a, b)
            elif code == OR_TRIGGER:
                text = "OR(%d)" % a
            else:
                text = sign + s1.replace("'", '"')
            if override:
                text = "TriggerOverride(%s,%s)" % (override, text)
                override = None
            triggers.append(text)
        responses = []
        for weight, actions in re.findall(r"RE\n(\d+)(.*?)RE\n", body, re.S):
            texts = []
            for code, first, second, tail in re.findall(
                    r'AC\n(\d+)OB\n([^\n]*)OB\nOB\n([^\n]*)OB\nOB\n[^\n]*OB\n0 0 0 0 0"([^"]*)" "" AC\n', actions):
                if code == "168":
                    texts.append("ActionOverride(%s,Interact(%s))" % (name_of(first), name_of(second)))
                else:
                    texts.append(tail.replace("'", '"'))
            responses.append((int(weight), texts))
        blocks.append((triggers, responses))
    return blocks


# --- the scripts under test ---

def pair_actions(a, b):
    return "    ActionOverride(%s,Interact(%s))\n    ActionOverride(%s,Interact(%s))\n" % (a, b, b, a)


def speaker_block(speaker, partners, gate=(5, 1), weights=None, tail_weight=0, extra_trigger=""):
    """A block in the shape of the Crossmod Banter Pack v5."""
    triggers = "  TriggerOverride(%s,ActionListEmpty())\n  !StateCheck(%s,CD_STATE_NOTVALID)\n" % (speaker, speaker)
    if gate:
        triggers += "  RandomNum(%d,%d)\n" % gate
    triggers += extra_trigger
    triggers += ('  CombatCounter(0)\n  RealGlobalTimerExpired("IWD_BANTER_TIMER","GLOBAL")\n'
                 '  GlobalTimerExpired("IWD_BANTER_TIMER_REAL_TIME","GLOBAL")\n')
    weights = weights or [25] * len(partners)
    responses = "".join("  RESPONSE #%d\n%s%s" % (w, TIMERS, pair_actions(speaker, p)) for w, p in zip(weights, partners))
    responses += "  RESPONSE #%d\n%s" % (tail_weight, TIMERS)
    return "IF\n%sTHEN\n%sEND\n" % (triggers, responses)


def banter_script(players=("Player2", "Player3", "Player4", "Player5", "Player6")):
    blocks = [speaker_block(s, [p for p in players if p != s], gate=(5, i + 1)) for i, s in enumerate(players)]
    return OTHER_BLOCK + "\n" + "\n".join(blocks) + "\n" + OTHER_BLOCK.replace("SOMETHING_ELSE", "LAST_BLOCK")


def run_weidu(raw, work):
    source = work / "in.bcs"
    target = work / "out.bcs"
    source.write_bytes(raw.encode("latin-1"))
    target.unlink(missing_ok=True)
    shutil.copy(HARNESS, work / "banter_harness.tp2")
    done = subprocess.run(
        [WEIDU, "banter_harness.tp2", "--nogame", "--no-exit-pause", "--noautoupdate", "--quick-log",
         "--skip-at-view", "--force-install-list", "1",
         "--args", str(MOD).replace("\\", "/"), "--args", "in.bcs", "--args", "out.bcs"],
        cwd=work, capture_output=True, text=True, errors="replace")
    log = done.stdout + done.stderr
    found = re.search(r"harness result: blocks=(\d+) foreign=(\d+)", log)
    if not found or "SUCCESSFULLY INSTALLED" not in log:
        raise AssertionError("WeiDU failed:\n" + log[-2500:])
    (work / "WeiDU.log").unlink(missing_ok=True)
    shutil.rmtree(work / "backup", ignore_errors=True)
    return target.read_bytes().decode("latin-1"), int(found.group(1)), int(found.group(2))


class World:
    """Who can talk."""

    def __init__(self, dead=(), empty=(), elsewhere=(), busy=(), combat=False, timers=True):
        self.dead, self.empty, self.elsewhere, self.busy = set(dead), set(empty), set(elsewhere), set(busy)
        self.combat, self.timers = combat, timers

    def holds(self, trigger, number):
        m = re.fullmatch(r"RandomNum(GT|LT)?\((\d+),(\d+)\)", trigger)
        if m:
            roll = number % int(m.group(2)) + 1
            value = int(m.group(3))
            return {None: roll == value, "GT": roll > value, "LT": roll < value}[m.group(1)]
        m = re.fullmatch(r"!StateCheck\((\w+),CD_STATE_NOTVALID\)", trigger)
        if m:  # the engine: StateCheck is false for an empty slot, so its negation holds
            return m.group(1) not in self.dead
        m = re.fullmatch(r"TriggerOverride\((\w+),ActionListEmpty\(\)\)", trigger)
        if m:
            return m.group(1) not in self.empty and m.group(1) not in self.busy
        m = re.fullmatch(r"TriggerOverride\((\w+),InMyArea\((\w+)\)\)", trigger)
        if m:
            a, b = m.group(1), m.group(2)
            return (a not in self.empty and b not in self.empty
                    and (a in self.elsewhere) == (b in self.elsewhere))
        if trigger == "CombatCounter(0)":
            return not self.combat
        if "TimerExpired" in trigger:
            return self.timers
        if trigger.startswith("Global("):
            return False
        raise AssertionError("the model does not know " + trigger)


def block_holds(triggers, world, number):
    lines = iter(triggers)
    for trigger in lines:
        m = re.fullmatch(r"OR\((\d+)\)", trigger)
        if m:
            if not any([world.holds(t, number) for t in itertools.islice(lines, int(m.group(1)))]):
                return False
        elif not world.holds(trigger, number):
            return False
    return True


def one_pass(blocks, world):
    """The outcomes of one pass of the script: {actions: chance}. Key () is a pass where
    nothing ran. Every number the pass can roll counts once: the ranges repeat after their
    least common multiple."""
    ranges = [int(m) for triggers, _ in blocks for t in triggers for m in re.findall(r"RandomNum(?:GT|LT)?\((\d+),", t)]
    numbers = math.lcm(*ranges) if ranges else 1
    outcomes = {}
    for number in range(numbers):
        for triggers, responses in blocks:
            if block_holds(triggers, world, number):
                total = sum(w for w, _ in responses)
                for weight, actions in responses:
                    if weight:
                        key = tuple(actions)
                        outcomes[key] = outcomes.get(key, 0) + Fraction(weight, total * numbers)
                break
        else:
            outcomes[()] = outcomes.get((), 0) + Fraction(1, numbers)
    return outcomes

def talkers(outcomes):
    """Every Interact pair in the outcomes, with the chance of its response."""
    pairs = {}
    for actions, chance in outcomes.items():
        for action in actions:
            m = re.fullmatch(r"ActionOverride\((\w+),Interact\((\w+)\)\)", action)
            if m:
                pairs[(m.group(1), m.group(2))] = pairs.get((m.group(1), m.group(2)), 0) + chance
    return pairs


class Guard(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix="banter-guard-"))
        self.addCleanup(shutil.rmtree, self.work, True)

    def patch(self, text):
        """Patches readable script text. Returns the compiled source, the compiled result,
        the decoded result, blocks and foreign."""
        source = compile_script(text)
        patched, blocks, foreign = run_weidu(source, self.work)
        return source, patched, decompile_script(patched), blocks, foreign

    def test_the_encoder_and_decoder_agree(self):
        text = banter_script()
        self.assertEqual(decompile_script(compile_script(text)), lines_to_blocks(text))

    def test_v5_shape_keeps_every_chance_when_everyone_can_talk(self):
        text = banter_script()
        _, _, parts, blocks, foreign = self.patch(text)
        self.assertEqual((blocks, foreign), (5, 0))
        self.assertEqual(one_pass(lines_to_blocks(text), World()), one_pass(parts, World()))

    def test_every_part_runs_its_response_word_for_word(self):
        text = banter_script()
        _, _, parts, _, _ = self.patch(text)
        self.assertEqual(len(parts), 2 + 20)
        old = [tuple(a) for _, rs in lines_to_blocks(text) for w, a in rs if w]
        new = [tuple(a) for _, rs in parts for w, a in rs if w]
        self.assertEqual(old, new)
        self.assertEqual(sum(1 for t, _ in parts for line in t if "InMyArea" in line), 20)

    def test_other_blocks_stay_byte_for_byte(self):
        source, patched, _, _, _ = self.patch(banter_script())
        first = source[:source.index("CR\nCO\n", source.index("CR\nCO\n") + 1)]
        last = source[source.rindex("CR\nCO\n"):]
        self.assertTrue(patched.startswith(first))
        self.assertTrue(patched.endswith(last))

    def test_each_response_keeps_its_bytes(self):
        source, patched, _, _, _ = self.patch(banter_script())
        for response in re.findall(r"RE\n25(AC\n.*?)RE\n", source, re.S):
            self.assertIn("RE\n100" + response + "RE\n", patched)

    def test_a_dead_partner_is_never_picked_and_the_others_stay(self):
        _, _, parts, _, _ = self.patch(banter_script())
        pairs = talkers(one_pass(parts, World(dead=["Player4"])))
        self.assertFalse([p for p in pairs if "Player4" in p])
        living = ("Player2", "Player3", "Player5", "Player6")
        self.assertEqual(set(pairs), {(a, b) for a in living for b in living if a != b})

    def test_a_dead_partner_leaves_every_other_pair_its_exact_chance(self):
        text = banter_script()
        _, _, parts, _, _ = self.patch(text)
        for dead in ("Player3", "Player4", "Player6"):
            before = one_pass(lines_to_blocks(text), World())
            after = one_pass(parts, World(dead=[dead]))
            for actions, chance in after.items():
                if actions:
                    self.assertEqual(chance, before[actions])
            self.assertEqual(len([a for a in after if a]), 12)

    def test_the_speaker_and_the_partner_come_from_different_rolls(self):
        _, _, parts, _, _ = self.patch(banter_script())
        pairs = talkers(one_pass(parts, World()))
        self.assertEqual(len(pairs), 20)
        self.assertEqual(len(set(pairs.values())), 1)
    def test_an_empty_slot_is_never_picked(self):
        _, _, parts, _, _ = self.patch(banter_script())
        pairs = talkers(one_pass(parts, World(empty=["Player6"])))
        self.assertFalse([p for p in pairs if "Player6" in p])
        self.assertTrue(pairs)

    def test_a_partner_in_another_area_is_never_picked(self):
        _, _, parts, _, _ = self.patch(banter_script())
        pairs = talkers(one_pass(parts, World(elsewhere=["Player3"])))
        self.assertFalse([p for p in pairs if "Player3" in p])
        pairs = talkers(one_pass(parts, World(elsewhere=["Player3", "Player4"])))
        self.assertIn(("Player3", "Player4"), pairs)
        self.assertNotIn(("Player3", "Player5"), pairs)

    def test_no_pair_that_can_talk_means_nothing_runs_at_all(self):
        _, _, parts, _, _ = self.patch(banter_script())
        for world in (World(dead=["Player3", "Player4", "Player5", "Player6"]),
                      World(empty=["Player3", "Player4", "Player5", "Player6"]),
                      World(dead=["Player2", "Player3"], empty=["Player4", "Player5", "Player6"]),
                      World(elsewhere=["Player2"], dead=["Player3", "Player4", "Player5", "Player6"])):
            self.assertEqual(one_pass(parts, world), {(): Fraction(1)})

    def test_other_weights_keep_their_chances(self):
        players = ("Player2", "Player3", "Player4", "Player5")
        text = "\n".join(speaker_block(s, [p for p in players if p != s], gate=(7, 3), weights=[10, 20, 30], tail_weight=40)
                         for s in players)
        _, _, parts, blocks, _ = self.patch(text)
        self.assertEqual(blocks, 4)
        self.assertEqual(one_pass(lines_to_blocks(text), World()), one_pass(parts, World()))
        # the response that only sets the timers has no pair, so nothing can stop it
        self.assertTrue(any(not [line for line in t if "InMyArea" in line] for t, _ in parts))

    def test_a_block_without_a_random_gate_keeps_its_chances(self):
        text = speaker_block("Player2", ["Player3", "Player4"], gate=None, weights=[30, 70])
        _, _, parts, blocks, _ = self.patch(text)
        self.assertEqual(blocks, 1)
        self.assertEqual(one_pass(lines_to_blocks(text), World()), one_pass(parts, World()))

    def test_a_random_trigger_inside_an_or_stays_and_the_pairs_stay_reachable(self):
        text = speaker_block("Player2", ["Player3", "Player4"], gate=None,
                             extra_trigger='  OR(2)\n    RandomNum(5,1)\n    Global("X","GLOBAL",1)\n')
        _, _, parts, blocks, _ = self.patch(text)
        self.assertEqual(blocks, 1)
        self.assertEqual(sum(1 for t, _ in parts if "RandomNum(5,1)" in t), 2)
        self.assertEqual(one_pass(lines_to_blocks(text), World()), one_pass(parts, World()))

    def test_weights_that_share_a_factor_with_the_blocks_roll_stay_close(self):
        players = ("Player2", "Player3", "Player4", "Player5", "Player6", "Player1")
        text = "\n".join(speaker_block(s, [p for p in players if p != s], gate=(5, i + 1))
                         for i, s in enumerate(players[:5]))
        _, _, parts, _, _ = self.patch(text)
        before = one_pass(lines_to_blocks(text), World())
        after = one_pass(parts, World())
        self.assertEqual(set(before), set(after))
        for actions, chance in before.items():
            self.assertLess(abs(chance - after[actions]), Fraction(1, 1000))
        self.assertTrue(all(any("1009" in line for line in t) for t, _ in parts))
    def test_extra_actions_and_reordered_responses_stay_with_their_pair(self):
        text = ('IF\n  RandomNum(4,2)\n  !StateCheck(Player6,CD_STATE_NOTVALID)\nTHEN\n'
                '  RESPONSE #1\n    DisplayStringHead(Player6,1)\n    ActionOverride(Player3,Interact(Player6))\n'
                '    SetGlobal("A","GLOBAL",1)\n'
                '  RESPONSE #3\n    ActionOverride(Player6Fill,Interact(Player2Fill))\nEND\n')
        _, _, parts, blocks, _ = self.patch(text)
        self.assertEqual(blocks, 1)
        first, second = parts
        self.assertEqual(first[1][0][1], ["DisplayStringHead(Player6,1)", "ActionOverride(Player3,Interact(Player6))",
                                          'SetGlobal("A","GLOBAL",1)'])
        self.assertIn("!StateCheck(Player3,CD_STATE_NOTVALID)", first[0])
        self.assertIn("TriggerOverride(Player3,InMyArea(Player6))", first[0])
        self.assertIn("TriggerOverride(Player6Fill,InMyArea(Player2Fill))", second[0])
        self.assertIn("!StateCheck(Player2Fill,CD_STATE_NOTVALID)", second[0])

    def test_a_second_run_changes_nothing(self):
        _, patched, _, _, _ = self.patch(banter_script())
        again, blocks, _ = run_weidu(patched, self.work)
        self.assertEqual(blocks, 0)
        self.assertEqual(patched, again)

    def test_a_block_that_already_checks_its_pair_stays(self):
        text = ('IF\n  !StateCheck(Player2,CD_STATE_NOTVALID)\n  !StateCheck(Player3,CD_STATE_NOTVALID)\n'
                '  TriggerOverride(Player3,InMyArea(Player2))\n  RandomNum(5,1)\nTHEN\n'
                '  RESPONSE #100\n' + pair_actions("Player2", "Player3") + 'END\n')
        source, patched, _, blocks, foreign = self.patch(text)
        self.assertEqual((blocks, foreign), (0, 0))
        self.assertEqual(patched, source)

    def test_a_script_without_banter_stays(self):
        source, patched, _, blocks, foreign = self.patch(OTHER_BLOCK + "\n" + OTHER_BLOCK.replace("SOMETHING_ELSE", "LAST_BLOCK"))
        self.assertEqual((blocks, foreign), (0, 0))
        self.assertEqual(patched, source)

    def test_interact_at_anything_but_a_party_slot_stays_and_is_counted(self):
        source, patched, _, blocks, foreign = self.patch(
            'IF\n  RandomNum(2,1)\nTHEN\n  RESPONSE #100\n    ActionOverride(Player2,Interact("C0KARIHI"))\nEND\n')
        self.assertEqual((blocks, foreign), (0, 1))
        self.assertEqual(patched, source)

    def test_windows_line_ends(self):
        text = banter_script()
        patched, blocks, _ = run_weidu(compile_script(text).replace("\n", "\r\n"), self.work)
        self.assertEqual(blocks, 5)
        self.assertEqual(one_pass(lines_to_blocks(text), World()), one_pass(decompile_script(patched), World()))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: test_banter_guard.py <weidu.exe>")
    WEIDU = sys.argv.pop(1)
    unittest.main()
