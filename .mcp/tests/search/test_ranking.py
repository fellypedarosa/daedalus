import unittest
from daedalus_search.models import Candidate, Passage
from daedalus_search.ranking import fuse
from scripts.evaluate_search import metrics


class RankingTests(unittest.TestCase):
    def test_rrf_uses_positions_and_merges_channels(self):
        a = Passage("a", "wiki/A.md", "", 1, 1, "a", "a")
        b = Passage("b", "wiki/B.md", "", 1, 1, "b", "b")
        result = fuse([Candidate(a, 10000, {"lexical"}), Candidate(b, 2, {"lexical"})],
                      [Candidate(b, .9, {"semantic"}), Candidate(a, .1, {"semantic"})])
        self.assertAlmostEqual(result[0].score, result[1].score)
        self.assertEqual(result[0].channels, {"lexical", "semantic"})

    def test_metrics_known_relevance(self):
        result = metrics(["irrelevant", "relevant"], {"relevant": 3})
        self.assertEqual(result["mrr_at_5"], .5)
        self.assertEqual(result["recall_at_5"], 1)
        self.assertEqual(result["precision_at_5"], .2)
        self.assertAlmostEqual(result["ndcg_at_5"], 1 / __import__("math").log2(3))
