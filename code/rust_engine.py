# finproj - Rust Monte Carlo engine called from Python
# Copyright (C) 2025-2026 Alex Scherer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Run the finproj projection engine in Rust.

Build once from the repository root:

    cargo build --release --manifest-path rust/Cargo.toml -p finproj_engine

Then:

    from rust_engine import run_simulation_rust
    result = run_simulation_rust(config)

``result`` has the same ``nav_observers`` and ``nav_fan`` objects as
``inv_proj_runner.run_simulation``. Draws use CPython's random generator, so
the same seed produces the same net-asset-value paths. Plain contribution and
withdrawal schedules are passed in as one vector. A custom Viva program is
still drawn in Python, once per projection, and the portfolio math runs in Rust.

This path does not write ``audit.txt`` or ``output.csv``.
"""

from __future__ import annotations

import ctypes
import struct
from pathlib import Path

from inv_proj import (
    STREAM_VIVA,
    NavFanObserver,
    StatisticalObserver,
    cv,
    mix_seed,
)
from inv_proj_runner import (
    RunResult,
    SimulationConfig,
    _build_flow_engine,
    _clamp_period_range,
    _positive_amount,
    nav_observer_years,
    sync_config_with_catalog,
    validate_allocation,
    validate_correlation,
)

_LIB: ctypes.CDLL | None = None


def _library_path() -> Path:
    root = Path(__file__).resolve().parent.parent / "rust" / "target"
    names = (
        "libfinproj_engine.dylib",
        "libfinproj_engine.so",
        "finproj_engine.dll",
    )
    for build in ("release", "debug"):
        for name in names:
            candidate = root / build / name
            if candidate.is_file():
                return candidate
    raise FileNotFoundError(
        "Rust engine is not built. From the finproj folder run: "
        "cargo build --release --manifest-path rust/Cargo.toml -p finproj_engine"
    )


def _library() -> ctypes.CDLL:
    global _LIB
    if _LIB is None:
        lib = ctypes.CDLL(str(_library_path()))
        lib.finproj_run.argtypes = [
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.POINTER(ctypes.c_double)),
            ctypes.POINTER(ctypes.c_size_t),
            ctypes.c_char_p,
            ctypes.c_size_t,
        ]
        lib.finproj_run.restype = ctypes.c_int
        lib.finproj_free.argtypes = [ctypes.POINTER(ctypes.c_double), ctypes.c_size_t]
        lib.finproj_free.restype = None
        _LIB = lib
    return _LIB


class _Packer:
    def __init__(self) -> None:
        self._buf = bytearray()

    def bytes(self, data: bytes) -> None:
        self._buf.extend(data)

    def u32(self, value: int) -> None:
        self._buf.extend(struct.pack("<I", int(value)))

    def u64(self, value: int) -> None:
        self._buf.extend(struct.pack("<Q", int(value) & 0xFFFFFFFFFFFFFFFF))

    def f64(self, value: float) -> None:
        self._buf.extend(struct.pack("<d", float(value)))

    def finish(self) -> bytes:
        return bytes(self._buf)


def _flat_flows(config: SimulationConfig) -> list[float]:
    flows = [0.0] * int(config.max_year)
    if _positive_amount(config.contributions) > 0:
        amount = cv(config.contributions.strip())
        start, end = _clamp_period_range(
            config.contributions_from_period,
            config.contributions_to_period,
            config.max_year,
        )
        for year in range(start, end + 1):
            flows[year - 1] += amount
    if _positive_amount(config.withdrawals) > 0:
        amount = cv(config.withdrawals.strip().lstrip("-"))
        start, end = _clamp_period_range(
            config.withdrawals_from_period,
            config.withdrawals_to_period,
            config.max_year,
        )
        for year in range(start, end + 1):
            flows[year - 1] -= amount
    return flows


def _flow_matrix(config: SimulationConfig) -> list[list[float]] | None:
    """Per-projection flows when a custom Viva program is present."""
    if not (config.viva_source or "").strip():
        return None
    engine = _build_flow_engine(config)
    matrix: list[list[float]] = []
    for projection in range(int(config.nb_projections)):
        seed = mix_seed(config.rng_seed, STREAM_VIVA, projection + 1)
        matrix.append(list(engine.draw_flows(seed=seed).flows))
    return matrix


def _pack_spec(config: SimulationConfig, flows) -> bytes:
    """Pack the simulation configuration into a binary specification. Used by Rust."""
    asset_ids = list(config.risk_param.keys())
    index = {asset_id: i for i, asset_id in enumerate(asset_ids)}

    def require(asset_id: str, label: str) -> int:
        if asset_id not in index:
            raise ValueError(f"{label} asset {asset_id} has no return distribution")
        return index[asset_id]

    pack = _Packer()
    pack.bytes(b"FPR1")
    pack.u32(len(asset_ids))
    pack.u32(config.max_year)
    pack.u32(config.nb_projections)
    pack.u64(config.rng_seed)
    pack.f64(cv(config.initial_capital))
    pack.f64(cv(config.cash_buffer))
    pack.u32(require(config.asset_catalog.liquidity_id(), "liquidity"))
    pack.u32(require(config.asset_catalog.shortfall_id(), "shortfall"))
    pack.u32(require(config.asset_catalog.replenishment_id(), "replenishment"))

    mix_items = [(asset_id, weight) for asset_id, weight in config.risk_mix.items()]
    if not mix_items:
        raise ValueError("risk mix is empty")
    pack.u32(len(mix_items))
    for asset_id, weight in mix_items:
        if asset_id not in index:
            raise ValueError(f"mix asset {asset_id} has no return distribution")
        pack.u32(index[asset_id])
        pack.f64(weight)

    for asset_id in asset_ids:
        segments = config.risk_param[asset_id]
        pack.u32(len(segments))
        for segment in segments:
            kind = segment.get("rv", "norm")
            if kind != "norm":
                raise ValueError(f"Unknown random variable class '{kind}'")
            pack.u32(int(segment["from_year"]))
            pack.f64(segment["mu"])
            pack.f64(segment["sigma"])

    correlations = []
    for (left, right), rho in config.risk_correlation.items():
        if left not in index or right not in index:
            raise ValueError(f"Unknown risk class in correlation: {left}, {right}")
        correlations.append((index[left], index[right], rho))
    pack.u32(len(correlations))
    for left, right, rho in correlations:
        pack.u32(left)
        pack.u32(right)
        pack.f64(rho)

    if flows and isinstance(flows[0], list):
        matrix = flows
        if len(matrix) != int(config.nb_projections):
            raise ValueError("flow matrix does not match the number of projections")
        pack.u32(1)
        for row in matrix:
            if len(row) != int(config.max_year):
                raise ValueError("a flow row does not match the horizon")
            for value in row:
                pack.f64(value)
    else:
        shared = flows
        if len(shared) != int(config.max_year):
            raise ValueError("flow schedule does not match the horizon")
        pack.u32(0)
        for value in shared:
            pack.f64(value)
    return pack.finish()


def _call_engine(spec: bytes) -> list[float]:
    lib = _library()
    buffer = (ctypes.c_uint8 * len(spec)).from_buffer_copy(spec)
    out_ptr = ctypes.POINTER(ctypes.c_double)()
    out_count = ctypes.c_size_t()
    err = ctypes.create_string_buffer(1024)
    code = lib.finproj_run(
        ctypes.cast(buffer, ctypes.c_void_p),
        len(spec),
        ctypes.byref(out_ptr),
        ctypes.byref(out_count),
        err,
        len(err),
    )
    if code != 0:
        message = err.value.decode("utf-8", errors="replace") or "rust engine failed"
        raise ValueError(message)
    count = int(out_count.value)
    values = [out_ptr[i] for i in range(count)]
    lib.finproj_free(out_ptr, count)
    return values


def run_simulation_rust(config: SimulationConfig) -> RunResult:
    """Project ``config`` in the Rust engine and return Python observer objects."""
    if int(config.nb_projections) < 1:
        raise ValueError("nb_projections must be at least 1")
    if int(config.max_year) < 1:
        raise ValueError("max_year must be at least 1")

    sync_config_with_catalog(config)
    config.asset_catalog.validate()
    validate_allocation(config.risk_mix, config.asset_catalog)
    validate_correlation(config.risk_param, config.risk_correlation)

    matrix = _flow_matrix(config)
    flows: list[float] | list[list[float]]
    flows = matrix if matrix is not None else _flat_flows(config)
    spec = _pack_spec(config, flows)
    flat = _call_engine(spec)

    n_proj = int(config.nb_projections)
    n_years = int(config.max_year)
    expected = n_proj * n_years
    if len(flat) != expected:
        raise RuntimeError(f"rust engine returned {len(flat)} values, expected {expected}")

    fan = NavFanObserver(n_years)
    for year in range(1, n_years + 1):
        fan.values_by_year[year] = [flat[p * n_years + (year - 1)] for p in range(n_proj)]

    observers: dict[str, StatisticalObserver] = {}
    for year in nav_observer_years(n_years):
        observer = StatisticalObserver()
        observer.values = list(fan.values_by_year[year])
        observers[f"Net Asset Value @ year {year:>2}"] = observer

    return RunResult(
        nav_observers=observers,
        nav_fan=fan,
        output_csv=config.output_dir / "output.csv",
        audit_path=config.output_dir / "audit.txt",
    )
