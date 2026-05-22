# finproj - tests for correlated return sampling
# Copyright (C) 2025-2026 Alex Scherer
#
# Run from project root with: python3 -m unittest discover -s tests -v

import math
import unittest

from inv_proj import (
    CorrelatedReturns,
    Risk,
    build_correlation_matrix,
    cholesky_decomposition,
    rc,
)


# Assumed return parameters used throughout these tests (percent units).
TEST_RISK_PARAM = {
    rc.MONEY_MARKET: [{"from_year": 1, "rv": "norm", "mu": 0.5, "sigma": 4.0}],
    rc.BOND: [{"from_year": 1, "rv": "norm", "mu": 2.0, "sigma": 10.0}],
    rc.EQUITY: [{"from_year": 1, "rv": "norm", "mu": 6.5, "sigma": 20.0}],
    rc.REAL_ESTATE: [{"from_year": 1, "rv": "norm", "mu": 3.0, "sigma": 15.0}],
}

TEST_CORRELATIONS = {
    (rc.MONEY_MARKET, rc.BOND): 0.50,
    (rc.EQUITY, rc.BOND): -0.20,
    (rc.EQUITY, rc.REAL_ESTATE): 0.30,
    (rc.BOND, rc.REAL_ESTATE): 0.10,
}

# Large enough for stable Monte Carlo checks; 4-sigma tolerances below keep false failures rare.
N_DRAWS = 15_000
PERIOD = 1
MAX_YEAR = 1
SIGMA_LEVEL = 4.0


def sample_mean(values):
    return sum(values) / len(values)


def sample_std(values):
    n = len(values)
    mean = sample_mean(values)
    variance = sum((value - mean) ** 2 for value in values) / (n - 1)
    return math.sqrt(variance)


def sample_correlation(x_values, y_values):
    n = len(x_values)
    mean_x = sample_mean(x_values)
    mean_y = sample_mean(y_values)
    covariance = sum((x_values[i] - mean_x) * (y_values[i] - mean_y) for i in range(n)) / (n - 1)
    std_x = sample_std(x_values)
    std_y = sample_std(y_values)
    return covariance / (std_x * std_y)


def matrix_multiply_lower(lower, transpose_lower=True):
    n = len(lower)
    result = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            result[i][j] = sum(
                lower[i][k] * (lower[j][k] if transpose_lower else lower[k][j])
                for k in range(n)
            )
    return result


def expected_mu(risk_distrib, risk_class, period):
    return risk_distrib[risk_class].distribution[period].mu


def expected_sigma(risk_distrib, risk_class, period):
    return risk_distrib[risk_class].distribution[period].sigma


def mean_tolerance(sigma, n_draws):
    return SIGMA_LEVEL * sigma / math.sqrt(n_draws)


def std_tolerance(sigma, n_draws):
    # Approximate sampling variability of the sample standard deviation.
    return SIGMA_LEVEL * sigma / math.sqrt(2 * (n_draws - 1))


def correlation_tolerance(target_rho, n_draws):
    return SIGMA_LEVEL * (1 - target_rho**2) / math.sqrt(n_draws - 1)


class CorrelatedReturnsStatisticsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.risk_distrib = Risk.buildRisks(TEST_RISK_PARAM, max_year=MAX_YEAR)
        cls.correlated_returns = CorrelatedReturns(
            cls.risk_distrib,
            correlations=TEST_CORRELATIONS,
        )
        cls.samples = {
            risk_class: [] for risk_class in TEST_RISK_PARAM
        }
        for _ in range(N_DRAWS):
            draw = cls.correlated_returns.draw(PERIOD)
            for risk_class, value in draw.items():
                cls.samples[risk_class].append(value)

    def test_sample_means_match_assumed_mu(self):
        for risk_class, values in self.samples.items():
            mu = expected_mu(self.risk_distrib, risk_class, PERIOD)
            observed_mean = sample_mean(values)
            tolerance = mean_tolerance(expected_sigma(self.risk_distrib, risk_class, PERIOD), N_DRAWS)
            self.assertAlmostEqual(
                observed_mean,
                mu,
                delta=tolerance,
                msg=(
                    f"{risk_class.name}: mean {observed_mean:.4f} vs assumed mu {mu:.4f} "
                    f"(tolerance +/- {tolerance:.4f})"
                ),
            )

    def test_sample_sigmas_match_assumed_sigma(self):
        for risk_class, values in self.samples.items():
            sigma = expected_sigma(self.risk_distrib, risk_class, PERIOD)
            observed_std = sample_std(values)
            tolerance = std_tolerance(sigma, N_DRAWS)
            self.assertAlmostEqual(
                observed_std,
                sigma,
                delta=tolerance,
                msg=(
                    f"{risk_class.name}: std {observed_std:.4f} vs assumed sigma {sigma:.4f} "
                    f"(tolerance +/- {tolerance:.4f})"
                ),
            )

    def test_sample_correlations_match_assumed_correlations(self):
        for (risk_a, risk_b), target_rho in TEST_CORRELATIONS.items():
            observed_rho = sample_correlation(self.samples[risk_a], self.samples[risk_b])
            tolerance = correlation_tolerance(target_rho, N_DRAWS)
            self.assertAlmostEqual(
                observed_rho,
                target_rho,
                delta=tolerance,
                msg=(
                    f"{risk_a.name}/{risk_b.name}: correlation {observed_rho:.4f} "
                    f"vs assumed {target_rho:.4f} (tolerance +/- {tolerance:.4f})"
                ),
            )

    def test_unspecified_pairs_are_approximately_uncorrelated(self):
        uncorrelated_pairs = [
            (rc.MONEY_MARKET, rc.EQUITY),
            (rc.MONEY_MARKET, rc.REAL_ESTATE),
        ]
        for risk_a, risk_b in uncorrelated_pairs:
            observed_rho = sample_correlation(self.samples[risk_a], self.samples[risk_b])
            tolerance = correlation_tolerance(0.0, N_DRAWS)
            self.assertAlmostEqual(
                observed_rho,
                0.0,
                delta=tolerance,
                msg=(
                    f"{risk_a.name}/{risk_b.name}: correlation {observed_rho:.4f} "
                    f"vs assumed 0.0 (tolerance +/- {tolerance:.4f})"
                ),
            )


class CorrelatedReturnsStructureTest(unittest.TestCase):
    def test_build_correlation_matrix_is_symmetric_with_unit_diagonal(self):
        risk_classes = list(TEST_RISK_PARAM.keys())
        matrix = build_correlation_matrix(risk_classes, TEST_CORRELATIONS)

        for i, risk_a in enumerate(risk_classes):
            self.assertAlmostEqual(matrix[i][i], 1.0)
            for j, risk_b in enumerate(risk_classes):
                self.assertAlmostEqual(matrix[i][j], matrix[j][i])

        index = {risk_class: i for i, risk_class in enumerate(risk_classes)}
        for (risk_a, risk_b), rho in TEST_CORRELATIONS.items():
            self.assertAlmostEqual(matrix[index[risk_a]][index[risk_b]], rho)

    def test_cholesky_reconstructs_correlation_matrix(self):
        risk_classes = list(TEST_RISK_PARAM.keys())
        matrix = build_correlation_matrix(risk_classes, TEST_CORRELATIONS)
        lower = cholesky_decomposition(matrix)
        reconstructed = matrix_multiply_lower(lower, transpose_lower=True)

        for i in range(len(matrix)):
            for j in range(len(matrix)):
                self.assertAlmostEqual(reconstructed[i][j], matrix[i][j], places=10)

    def test_cholesky_rejects_non_positive_definite_matrix(self):
        bad_matrix = [
            [1.0, 0.9, 0.9],
            [0.9, 1.0, -0.9],
            [0.9, -0.9, 1.0],
        ]
        with self.assertRaises(ValueError):
            cholesky_decomposition(bad_matrix)


if __name__ == "__main__":
    unittest.main()
