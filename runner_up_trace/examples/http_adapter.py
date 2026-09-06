"""A ModelAdapter over an HTTP completion server that returns per-token
logprobs and accepts a token-id prompt. Written against the llama.cpp server
surface (`/tokenize`, `/completion` with `n_probs`, `temperature: 0`,
`n_predict`); other servers need the two request/response mappings changed
and nothing else.

stdlib only: urllib. No key handling, no retries; the runner adds what their
server needs.

With no `--url` this runs DRY: it prints the exact requests it would send for
a toy prefix, so the mapping can be checked against a server's docs before
any compute is spent. That is also what the smoke test exercises.

Run:  python -m runner_up_trace.examples.http_adapter [--url http://127.0.0.1:8080]
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from typing import Dict, List, Optional, Sequence

from ..model import Distribution, ModelAdapter


class LlamaCppAdapter(ModelAdapter):
    def __init__(self, url: Optional[str], model_id: str, top_k: int = 20,
                 eos_token: Optional[int] = None, timeout: float = 120.0):
        self.url = url.rstrip("/") if url else None
        self.model_id = model_id
        self.top_k = top_k
        self.eos_token = eos_token
        self.timeout = timeout
        self.dry_log: List[Dict] = []

    # -- transport -------------------------------------------------------
    def _post(self, path: str, body: Dict) -> Dict:
        if self.url is None:
            self.dry_log.append({"POST": path, "body": body})
            return {}
        req = urllib.request.Request(
            self.url + path, data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # -- contract --------------------------------------------------------
    def tokenize(self, text: str) -> List[int]:
        out = self._post("/tokenize", {"content": text})
        return list(out.get("tokens", []))

    def next_token_distribution(self, prefix: Sequence[int]) -> Distribution:
        out = self._post("/completion", {
            "prompt": list(prefix), "n_predict": 1, "temperature": 0,
            "n_probs": self.top_k, "cache_prompt": True,
        })
        probs = (out.get("completion_probabilities") or [{}])[0].get("probs", [])
        # llama.cpp reports `prob`; convert to logprob. Newer builds also
        # expose `logprob`; prefer it when present.
        top = []
        texts = []
        for p in probs:
            tok = p.get("id", p.get("tok_id"))
            lp = p.get("logprob")
            if lp is None:
                import math
                lp = math.log(max(float(p.get("prob", 0.0)), 1e-300))
            top.append((int(tok), float(lp)))
            texts.append(str(p.get("tok_str", "")))
        top.sort(key=lambda t: -t[1])
        return Distribution(top_k=top, full_entropy=None, texts=texts)

    def continue_greedy(self, prefix: Sequence[int], n: int) -> List[int]:
        out = self._post("/completion", {
            "prompt": list(prefix), "n_predict": n, "temperature": 0,
            "n_probs": 0, "cache_prompt": True,
        })
        toks = out.get("tokens")
        if toks is None:
            # server did not return ids; fall back to one step at a time
            return super().continue_greedy(prefix, n)
        return [int(t) for t in toks][:n]


def main(argv=None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--url", default=None, help="server base URL; omit for a dry run")
    p.add_argument("--model-id", default="llama.cpp:unnamed")
    a, _ = p.parse_known_args(argv)  # tolerate a test runner's argv
    adapter = LlamaCppAdapter(a.url, a.model_id)
    prefix = [1, 415, 4123]  # toy ids; a dry run only shows request shape
    if a.url is None:
        adapter.next_token_distribution(prefix)
        adapter.continue_greedy(prefix + [7], 8)
        print("DRY RUN -- requests that would be sent:")
        for entry in adapter.dry_log:
            print(json.dumps(entry, sort_keys=True))
        print("Map these two calls onto your server, then pass --url.")
    else:
        dist = adapter.next_token_distribution(prefix)
        print(f"k={dist.k} top={dist.top_k[:3]}")


if __name__ == "__main__":
    main()
