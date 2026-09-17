from __future__ import annotations

import unittest

from ecoscan.config import load_config
from ecoscan.services.final_readiness import (
    build_final_readiness_items,
    format_final_readiness_markdown,
    summarize_final_readiness,
)


class FinalReadinessTests(unittest.TestCase):
    def test_final_readiness_exposes_final_workstreams(self) -> None:
        items = build_final_readiness_items(load_config())
        titles = {item.title for item in items}
        summary = summarize_final_readiness(items)
        markdown = format_final_readiness_markdown(items)

        self.assertIn("Experiência cidadão e secretaria separada por perfil", titles)
        self.assertIn("Promoção controlada do modelo final", titles)
        self.assertIn("Publicação gratuita HTTPS para testes do grupo", titles)
        self.assertIn("Produção institucional com câmera ao vivo dedicada", titles)
        self.assertIn("Autenticação, papéis reais e proteção de evidências", titles)
        self.assertGreaterEqual(summary.get("ready", 0) + summary.get("prepared", 0), 2)
        self.assertIn("Estrutura final e escalável", markdown)
        self.assertTrue(any(item.prepared_for_later for item in items))


if __name__ == "__main__":
    unittest.main()
