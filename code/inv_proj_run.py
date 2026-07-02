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


from inv_proj_runner import default_config, run_simulation


def run():
    '''Main procedure to run investment projection simulation'''
    config = default_config()
    result = run_simulation(config)

    for period in result.nav_observers:
        print(f"{period:<20}: {result.nav_observers[period]}")


if __name__ == '__main__':
    run()
