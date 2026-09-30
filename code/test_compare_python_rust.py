import time

import viva
from inv_proj_runner import default_config
from inv_proj_runner import run_simulation as run_simulation_python
from lark.exceptions import UnexpectedCharacters
from rust_engine import run_simulation_rust


def time_func(func, config):
    start_time = time.time()
    result = func(config)
    end_time = time.time()
    return result, end_time - start_time

def test_compare_python_rust():
    config = default_config()
    config.max_year = 50
    config.nb_projections = 20000
    config.rng_seed = 42
    config.viva_source = r"life: Paul, male, born 1949 flow: inheritance, 1M, upon Paul's death"

    # test viva syntax compatibility
    if config.viva_source is not None:
        try:
            viva.generateFlowEngine(config.viva_source)
        except UnexpectedCharacters as e:
            print(f"Viva syntax error: {e}")
            return 

    # run the simulation
    python_result, time_python=time_func(run_simulation_python, config)
    rust_result, time_rust=time_func(run_simulation_rust, config)


    for nav in python_result.nav_observers:
        mean_p, mean_r = [o.nav_observers[nav].mean() for o in [python_result, rust_result]]
        print(f"Nav: {nav}, Python mean: {mean_p:,.0f}, Rust mean: {mean_r:,.0f}")

    print(f"Python time: {time_python:.2f}, Rust time: {time_rust:.2f}, Ratio: {time_python/time_rust:.2f}")



if __name__ == "__main__":
    test_compare_python_rust()