# finproj - Stochastic Financial Projections to optimize asset management
# Copyright (C) 2025-2026 Alex Scherer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Alternative licensing under a commercial license is available; see LICENSE
# and COMMERCIAL-LICENSE.md in the project root.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

import argparse
import secrets

from inv_proj_runner import default_config, run_simulation


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a finproj Monte Carlo projection (reproducible by default)."
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Master RNG seed (default: 1, from default_config).",
    )
    parser.add_argument(
        "--reseed",
        action="store_true",
        help="Draw a new master seed and print it (overrides --seed).",
    )
    return parser.parse_args(argv)


def run(argv: list[str] | None = None):
    """Main procedure to run investment projection simulation."""
    args = _parse_args(argv)
    config = default_config()
    if args.reseed:
        config.rng_seed = secrets.randbelow(2**31 - 2) + 1
    elif args.seed is not None:
        config.rng_seed = int(args.seed)
    print(f"rng_seed={config.rng_seed}")
    result = run_simulation(config)

    for period in result.nav_observers:
        print(f"{period:<20}: {result.nav_observers[period]}")


if __name__ == '__main__':
    run()
