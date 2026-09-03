"""Tests for training, calibration, decision policy and persistence.

The important cases here are the ones that protect against silently-wrong
numbers: feature-order mismatches, leakage across grouped folds, and
calibration fitted on in-sample scores.
"""

from __future__ import annotations

import numpy as np
import pytest

from halluciwatch.calibration import (
    Calibrator,
    DecisionPolicy,
    brier_score,
    expected_calibration_error,
)
from halluciwatch.evaluation.metrics import (
    coverage_at_error,
    evaluate,
    risk_coverage_curve,
)
from halluciwatch.types import Fingerprint


@pytest.fixture
def separable_data():
    """A learnable signal: feature 0 carries the label with noise."""
    rng = np.random.default_rng(0)
    n = 400
    y = rng.integers(0, 2, n)
    X = np.column_stack([y + rng.normal(0, 0.6, n), rng.normal(0, 1, (n, 4))])
    return X, y


class TestFingerprint:
    def test_length_mismatch_is_rejected(self):
        """Silent misalignment between names and values is the failure to prevent."""
        with pytest.raises(ValueError, match="length mismatch"):
            Fingerprint(names=["a", "b"], values=[1.0])

    def test_as_dict_pairs_names_and_values(self):
        fp = Fingerprint(names=["a", "b"], values=[1.0, 2.0])
        assert fp.as_dict() == {"a": 1.0, "b": 2.0}

    def test_subset_filters_by_tier(self):
        fp = Fingerprint(
            names=["a", "b", "c"], values=[1.0, 2.0, 3.0],
            tiers=["token", "sampling", "token"],
        )
        sub = fp.subset(["token"])
        assert sub.names == ["a", "c"]
        assert sub.values == [1.0, 3.0]


class TestCalibrator:
    def test_refuses_to_fit_on_too_little_data(self):
        """Isotonic overfits badly on small samples; identity is the safe fallback."""
        cal = Calibrator(min_samples=100).fit([0.1, 0.9], [0, 1])
        assert not cal.fitted
        assert cal.transform([0.42])[0] == pytest.approx(0.42)

    def test_improves_calibration_of_skewed_scores(self):
        rng = np.random.default_rng(1)
        y = rng.integers(0, 2, 600)
        # Systematically over-confident scores.
        raw = np.clip(y * 0.5 + 0.25 + rng.normal(0, 0.12, 600), 0, 1) ** 0.4
        cal = Calibrator().fit(raw, y)
        assert cal.fitted
        assert expected_calibration_error(cal.transform(raw), y) < expected_calibration_error(raw, y)

    def test_output_stays_in_unit_interval(self):
        rng = np.random.default_rng(2)
        y = rng.integers(0, 2, 300)
        cal = Calibrator().fit(rng.random(300), y)
        out = cal.transform([-5.0, 0.5, 5.0])
        assert np.all((out >= 0) & (out <= 1))


class TestDecisionPolicy:
    def test_accept_threshold_respects_target_error(self):
        rng = np.random.default_rng(3)
        n = 500
        y = rng.integers(0, 2, n)
        risks = np.clip(y * 0.6 + rng.normal(0, 0.15, n), 0, 1)
        policy = DecisionPolicy().fit(risks, y, target_error=0.10)
        assert policy.fitted
        accepted = y[risks <= policy.accept_below]
        if len(accepted):
            assert accepted.mean() <= 0.15  # target plus discretisation slack

    def test_decisions_are_ordered(self):
        policy = DecisionPolicy(accept_below=0.3, reject_above=0.7)
        assert policy.decide(0.1) == "accept"
        assert policy.decide(0.5) == "review"
        assert policy.decide(0.9) == "reject"

    def test_round_trips_through_dict(self):
        original = DecisionPolicy(accept_below=0.22, reject_above=0.81, coverage=0.43)
        restored = DecisionPolicy.from_dict(original.to_dict())
        assert restored.accept_below == pytest.approx(0.22)
        assert restored.reject_above == pytest.approx(0.81)

    def test_impossible_target_accepts_nothing(self):
        """If even the safest answer is wrong, coverage must be zero, not a guess."""
        policy = DecisionPolicy().fit([0.1, 0.2, 0.3], [1, 1, 1], target_error=0.01)
        assert policy.coverage == 0.0


class TestMetrics:
    def test_perfect_ranking_scores_one(self):
        m = evaluate([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1], bootstrap=0)
        assert m.auroc == pytest.approx(1.0)

    def test_random_ranking_scores_half(self):
        rng = np.random.default_rng(4)
        y = rng.integers(0, 2, 400)
        assert evaluate(rng.random(400), y, bootstrap=0).auroc == pytest.approx(0.5, abs=0.12)

    def test_single_class_does_not_crash(self):
        m = evaluate([0.1, 0.2, 0.3], [0, 0, 0], bootstrap=0)
        assert m.auroc == 0.5

    def test_empty_input_does_not_crash(self):
        assert evaluate([], []).n == 0

    def test_risk_coverage_is_monotone_in_coverage(self):
        coverage, _ = risk_coverage_curve([0.1, 0.5, 0.9], [0, 0, 1])
        assert list(coverage) == pytest.approx([1 / 3, 2 / 3, 1.0])

    def test_coverage_at_error_finds_safe_prefix(self):
        """Three safe answers then two wrong ones: full coverage at 40% error."""
        risks = [0.1, 0.2, 0.3, 0.8, 0.9]
        labels = [0, 0, 0, 1, 1]
        assert coverage_at_error(risks, labels, 0.0) == pytest.approx(0.6)
        assert coverage_at_error(risks, labels, 0.5) == pytest.approx(1.0)

    def test_bootstrap_ci_brackets_point_estimate(self):
        rng = np.random.default_rng(5)
        y = rng.integers(0, 2, 300)
        risks = np.clip(y * 0.5 + rng.normal(0, 0.25, 300), 0, 1)
        m = evaluate(risks, y, bootstrap=200)
        assert m.auroc_ci[0] <= m.auroc <= m.auroc_ci[1]

    def test_brier_is_zero_for_perfect_probabilities(self):
        assert brier_score([0.0, 1.0], [0, 1]) == pytest.approx(0.0)


class TestTraining:
    def test_learns_a_real_signal(self, separable_data):
        from halluciwatch.model import train_classifier

        X, y = separable_data
        names = [f"f{i}" for i in range(X.shape[1])]
        detector = train_classifier(X, y, names, kind="sklearn", n_splits=3)
        assert detector.metrics["auroc"] > 0.75
        assert detector.metrics["n_samples"] == len(y)

    def test_rejects_feature_name_mismatch(self, separable_data):
        from halluciwatch.model import train_classifier

        X, y = separable_data
        with pytest.raises(ValueError, match="feature names"):
            train_classifier(X, y, ["only", "two"], kind="sklearn")

    def test_rejects_single_class_target(self):
        from halluciwatch.model import train_classifier

        X = np.random.default_rng(6).random((50, 3))
        with pytest.raises(ValueError, match="single class"):
            train_classifier(X, np.zeros(50, dtype=int), ["a", "b", "c"], kind="sklearn")

    def test_grouped_folds_keep_a_question_on_one_side(self):
        """Leakage across folds is the easiest way to publish an inflated AUROC."""
        from halluciwatch.model import _grouped_folds

        groups = [f"q{i // 4}" for i in range(40)]
        for train_idx, test_idx in _grouped_folds(groups, 4, seed=0):
            train_groups = {groups[i] for i in train_idx}
            test_groups = {groups[i] for i in test_idx}
            assert not (train_groups & test_groups)

    def test_save_and_load_round_trip(self, separable_data, tmp_path):
        from halluciwatch.model import save_detector, train_classifier

        X, y = separable_data
        names = [f"f{i}" for i in range(X.shape[1])]
        detector = train_classifier(X, y, names, kind="sklearn", n_splits=3)
        out = save_detector(detector, tmp_path / "det")

        assert (out / "model.pkl").exists()
        assert (out / "detector.json").exists()

        import json

        meta = json.loads((out / "detector.json").read_text())
        assert meta["feature_names"] == names
        assert "auroc" in meta["metrics"]

    def test_predict_proba_is_calibrated_and_bounded(self, separable_data):
        from halluciwatch.model import train_classifier

        X, y = separable_data
        names = [f"f{i}" for i in range(X.shape[1])]
        detector = train_classifier(X, y, names, kind="sklearn", n_splits=3)
        probs = detector.predict_proba(X)
        assert probs.shape == (len(y), 2)
        assert np.allclose(probs.sum(axis=1), 1.0)
        assert np.all((probs >= 0) & (probs <= 1))


class TestImportanceAlignment:
    """`feature_importances_` must line up with `feature_names`.

    `importances` is stored sorted by gain so it can be printed directly, but
    `feature_names` stays in registry order. Returning the sorted values from
    `feature_importances_` pairs every name with another feature's number
    wherever the two are zipped - which the detector's explanation code does, so
    it silently reported the wrong "signals that drove the score".
    """

    def test_importances_follow_feature_name_order(self, separable_data):
        from halluciwatch.model import train_classifier

        X, y = separable_data
        names = [f"f{i}" for i in range(X.shape[1])]
        detector = train_classifier(X, y, names, kind="sklearn")

        aligned = detector.feature_importances_
        assert len(aligned) == len(detector.feature_names)

        by_name = dict(detector.importances)
        for name, value in zip(detector.feature_names, aligned, strict=True):
            assert value == pytest.approx(by_name[name])

    def test_top_feature_agrees_between_both_views(self, separable_data):
        from halluciwatch.model import train_classifier

        X, y = separable_data
        names = [f"f{i}" for i in range(X.shape[1])]
        detector = train_classifier(X, y, names, kind="sklearn")

        recomputed = max(
            zip(detector.feature_names, detector.feature_importances_, strict=True),
            key=lambda kv: kv[1],
        )[0]
        assert recomputed == detector.importances[0][0]
