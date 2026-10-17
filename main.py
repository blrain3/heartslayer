import os
import time
import traceback

from rs.ai.claw_is_law.claw_is_law import CLAW_IS_LAW
from rs.ai.peaceful_pummeling.peaceful_pummeling import PEACEFUL_PUMMELING
from rs.ai.observant_heartslayer.observant_heartslayer import OBSERVANT_HEARTSLAYER  # 碎心模式（三钥匙 + act4）
from rs.ai.pwnder_my_orbs.pwnder_my_orbs import PWNDER_MY_ORBS
from rs.ai.requested_strike.requested_strike import REQUESTED_STRIKE
from rs.ai.shivs_and_giggles.shivs_and_giggles import SHIVS_AND_GIGGLES
from rs.helper.seed import make_random_seed
from rs.api.client import Client
from rs.machine.game import Game
from rs.helper.logger import log, init_log, log_new_run_sequence

# If there are run seeds, it will run them. Otherwise, it will use the run amount.
run_seeds = [
    #'LGZ12EEMFGUK',
]
# EXPERIMENT: back-to-back runs. CommunicationMod keeps the game process alive across runs,
# so Game Over -> proceed -> start <char> is enough to line the next run up in theory. This is
# NOT verified yet; enable with RUN_AMOUNT=N in the environment so the default (1) stays intact.
# A bad value must not abort the batch before the first run: fall back to a single run.
try:
    run_amount = max(1, int(os.environ.get("RUN_AMOUNT", "1")))
except (TypeError, ValueError):
    run_amount = 1
# run_amount = 3
# 碎心模式：把下一行换成 OBSERVANT_HEARTSLAYER（slay_heart=True，自动收集三钥匙并进入 act4）
strategy = OBSERVANT_HEARTSLAYER  # 2026-10-05 碎心验证批次；回默认改回 PEACEFUL_PUMMELING

if __name__ == "__main__":
    init_log()
    log("Starting up")
    log_new_run_sequence()
    try:
        client = Client()
        game = Game(client, strategy)
        if run_seeds:
            for seed in run_seeds:
                game.start(seed)
                game.run()
                time.sleep(1)
        else:
            for i in range(run_amount):
                # A single run failing (bot stuck, unexpected screen) must not abort the
                # batch: log it and move on to the next run, otherwise "auto next run"
                # silently means "auto stop at the first problem".
                try:
                    game.start(make_random_seed())
                    game.run()
                except Exception:
                    log("Exception in run " + str(i + 1) + " of " + str(run_amount))
                    log(traceback.format_exc())
                    # Re-create the game so the next run starts from a clean client.
                    client = Client()
                    game = Game(client, strategy)
                time.sleep(1)

    except Exception as e:
        log("Exception! " + str(e))
        log(traceback.format_exc())
