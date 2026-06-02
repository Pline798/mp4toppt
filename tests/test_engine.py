"""视频帧提取引擎测试"""
import pytest
from core.engine import VideoEngine


def test_engine_init_defaults():
    engine = VideoEngine()
    assert engine.screenshot_mode == "interval"
    assert engine.interval == 1.0
    assert engine.stable_duration == 2.0
    assert engine.similarity_threshold == 95.0


def test_engine_init_custom():
    engine = VideoEngine(mode="stable", interval=0.5, stable_duration=3.0, similarity_threshold=90.0)
    assert engine.screenshot_mode == "stable"
    assert engine.interval == 0.5
    assert engine.stable_duration == 3.0
    assert engine.similarity_threshold == 90.0


def test_hamming_similarity_identical():
    h1 = "10101010" * 8
    assert VideoEngine._hamming_similarity(h1, h1) == 100.0


def test_hamming_similarity_completely_different():
    h1 = "10101010" * 8
    h2 = "01010101" * 8
    assert VideoEngine._hamming_similarity(h1, h2) == 0.0
