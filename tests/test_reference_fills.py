from types import SimpleNamespace
import pandas as pd
import pytest
from lab.adapters.reference import audit_oos_fills
from lab.engine import Costs


@pytest.mark.parametrize("side", [-1, 1])
def test_replay_detects_wrong_fill(side):
    dates = pd.date_range("2020-01-01", periods=7)
    prices = pd.DataFrame({"X": [100, 101, 102, 100, 101, 97, 95]}, index=dates)
    trades = pd.DataFrame([dict(_variant="v", asset="X", side=side, entry=dates[2], exit=dates[5],
                                entry_px=102., exit_px=97., ret=side*(97/102-1), reason="signal")])
    panel = SimpleNamespace(o=prices, h=prices, l=prices, c=prices)
    inputs = ({"v": SimpleNamespace(params={"_exit": 0})}, [SimpleNamespace(partial_r=None)], Costs())
    assert audit_oos_fills(panel, trades, *inputs)["status"] == "matched"
    trades.loc[0, "entry_px"] = 103
    with pytest.raises(ValueError, match="fill mismatch"):
        audit_oos_fills(panel, trades, *inputs)
